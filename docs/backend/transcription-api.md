# 백엔드 전사 API

## 아주 쉽게 설명하면

백엔드는 세 사람이 줄을 서서 일하는 구조다.

```text
Route 접수원 → Service 검사원 → Provider 외부 연락 담당
```

- **Route**는 브라우저 요청을 받는다.
- **Service**는 오디오가 규칙에 맞는지 검사한다.
- **Provider**는 OpenAI STT를 호출하고 공통 결과로 바꾼다.

이 역할을 나눈 이유는 외부 AI를 바꾸거나 테스트할 때 HTTP 코드와 도메인 규칙을
모두 다시 작성하지 않기 위해서다.

## 관련 파일

| 파일 | 책임 |
|---|---|
| `app/api/routes/transcriptions.py` | multipart 입력과 HTTP 응답 |
| `app/services/transcription_service.py` | 시간, 크기, 형식, signature 검증 |
| `app/providers/base.py` | provider가 지켜야 할 Protocol과 공통 결과 |
| `app/providers/openai_provider.py` | OpenAI SDK 호출, retry, usage 기록 |
| `app/schemas/transcription.py` | 공개 응답 Pydantic 모델 |
| `app/prompts/transcription.txt` | 축약·교정을 금지하는 STT prompt |
| `app/errors.py` | 내부 및 OpenAI 오류를 안전한 HTTP 오류로 변환 |
| `app/config.py` | 모델명, timeout, retry, 파일 크기 설정 |
| `tests/test_transcriptions.py` | route와 service 계약 테스트 |
| `tests/test_openai_provider.py` | OpenAI 호출 인자와 usage 테스트 |

경로는 모두 `backend/`를 기준으로 한다.

## Endpoint

```http
POST /api/transcriptions
Content-Type: multipart/form-data
```

### 입력

| Form 필드 | 서버 타입 | 제약 |
|---|---|---|
| `audio` | `UploadFile` | 필수 |
| `durationSeconds` | `float` | service에서 `0 < value <= 120.5` |
| `attemptNumber` | `int` | FastAPI에서 1~2 |

`attemptNumber`는 현재 route에서 즉시 버린다. API 계약에는 있지만 도메인 동작에는
사용하지 않는 값이다.

### 성공 응답

```json
{
  "transcript": "Um, I I went there yesterday.",
  "metadata": {
    "requestId": "c827d4c1-...",
    "model": "gpt-4o-mini-transcribe",
    "usage": {
      "inputTokens": 120,
      "outputTokens": 24,
      "cachedInputTokens": 0,
      "cacheWriteTokens": 0,
      "reasoningTokens": 0,
      "totalTokens": 144
    },
    "audioSeconds": null
  }
}
```

Python 모델은 snake_case를 사용하고 공통 `ApiModel`의 alias 규칙에 따라 JSON에서는
camelCase가 된다. OpenAI가 token usage를 반환하면 `usage`가 채워지고 duration usage를
반환하면 `audioSeconds`가 채워진다. 제공되지 않은 측정값은 `null`이다.

## Route 처리

Route는 설정한 최대 크기보다 한 바이트 더 읽는다.

```text
audio.read(max_audio_bytes + 1)
```

이렇게 해야 업로드 전체를 무제한으로 읽지 않으면서 제한을 넘겼는지 확인할 수 있다.
읽은 bytes와 metadata를 `TranscriptionService`에 전달한다.

Route가 직접 하지 않는 일:

- MIME과 signature 검증
- OpenAI SDK 호출
- 전사문 수정
- 음성 파일 저장
- 평가 LLM 호출

## Service 검증 순서

### 1. 녹음 시간

- 0초 이하는 `INVALID_AUDIO_DURATION`, HTTP 422
- 120.5초 초과도 같은 오류

0.5초 여유는 브라우저 timer와 stop event 사이의 작은 차이를 허용한다.

### 2. 파일 크기

- 512바이트 미만은 `AUDIO_TOO_SMALL`, HTTP 422
- `MAX_AUDIO_BYTES` 초과는 `AUDIO_TOO_LARGE`, HTTP 413
- 설정 기본값은 900,000바이트

512바이트 기준은 실제 음성 존재를 증명하지 않는다. 명백히 작은 파일을 빠르게 막는
최소 방어선이다.

### 3. MIME 정규화

`;` 뒤 codec parameter를 제거하고 소문자로 바꾼다.

```text
audio/webm;codecs=opus → audio/webm
```

허용 MIME과 저장 확장자:

| MIME | 확장자 |
|---|---|
| `audio/webm` | `.webm` |
| `audio/mp4` | `.mp4` |
| `audio/mpeg`, `audio/mp3` | `.mp3` |
| `audio/x-m4a` | `.m4a` |
| `audio/wav`, `audio/x-wav` | `.wav` |

목록에 없으면 `UNSUPPORTED_AUDIO_TYPE`, HTTP 415다.

### 4. 파일 signature

클라이언트가 보낸 MIME 문자열만 믿지 않고 bytes 시작 부분을 확인한다.

- WebM: EBML header
- MP4/M4A: `ftyp`
- WAV: `RIFF`와 `WAVE`
- MP3: ID3 또는 MPEG frame sync

일치하지 않으면 `INVALID_AUDIO_FILE`, HTTP 415다.

이 검사는 container의 첫 부분만 확인한다. codec, 전체 손상 여부, 실제 duration,
사람 음성 존재 여부는 검사하지 않는다.

## Provider 경계

`TranscriptionProvider` Protocol은 전사 서비스가 특정 AI 회사의 SDK에 직접
의존하지 않게 한다. 평가 서비스는 별도의 `EvaluationProvider` Protocol을 사용한다.
현재 `get_transcription_provider`는 `OpenAITranscriptionProvider`를,
`get_evaluation_provider`는 `OpenAIEvaluationProvider`를 반환한다. 두 클래스는
각자 필요한 메서드만 공개하고 내부 OpenAI SDK 처리 코드를 재사용한다.
전사와 평가에 다른 회사나 로컬 모델을 선택하는 설정은 아직 구현되지 않았다.

```python
async def transcribe(
    *,
    audio: bytes,
    filename: str,
    mime_type: str,
    prompt: str,
) -> ProviderTranscription
```

`ProviderTranscription`은 현재 다음 정보를 가질 수 있다.

- `text`
- `model`
- `usage`
- `audio_seconds`

공개 `TranscriptionResponse`는 이 값과 서버 request ID를 `metadata`로 전달한다.
프론트엔드는 metadata를 전사 결과에 함께 보관하므로 나중에 모델별 품질과 비용을
연결할 수 있다.

## OpenAI 호출 설정

| 설정 | 기본값 | 역할 |
|---|---|---|
| `OPENAI_TRANSCRIPTION_MODEL` | `gpt-4o-mini-transcribe` | STT 모델 |
| `OPENAI_TIMEOUT_SECONDS` | `60` | 외부 요청 timeout |
| `OPENAI_RATE_LIMIT_MAX_RETRIES` | `1` | rate limit 재시도 횟수 |
| `OPENAI_RATE_LIMIT_RETRY_DELAY_SECONDS` | `0.5` | 재시도 전 대기 |
| `MAX_AUDIO_BYTES` | `900000` | 읽을 수 있는 최대 오디오 bytes |

OpenAI SDK의 자동 retry는 0이다. provider의 `_with_rate_limit_retry`가 정책을 한 곳에서
통제한다.

호출 시 언어를 `en`으로 고정한다. 현재 OPIc 답변이 영어라는 제품 전제 때문이다.

## Prompt의 책임

`app/prompts/transcription.txt`는 STT가 코치처럼 행동하지 못하게 한다. 전사 단계는
말을 글로 옮기는 단계이지, 잘 말하도록 고쳐주는 단계가 아니다.

따라서 prompt는 다음 동작을 금지한다.

- 문법 교정
- 자연스러운 동의어로 교체
- 미완성 문장 완성
- 요약
- 문장 다듬기
- 말하지 않은 내용 추가

이 prompt 자체도 완벽함을 보장하지 않는다. 모델이 실제로 필러와 오류를 얼마나
보존하는지는 고정된 평가 자료로 측정해야 한다.

## 오류 응답

모든 공개 오류는 공통 형식을 사용한다.

```json
{
  "error": {
    "code": "AUDIO_TOO_LARGE",
    "message": "녹음 파일 크기가 허용 범위를 초과했습니다.",
    "requestId": "c827d4c1-..."
  }
}
```

주요 외부 오류 변환:

| 상황 | HTTP | 공개 코드 |
|---|---:|---|
| OpenAI rate limit | 429 | `OPENAI_RATE_LIMITED` |
| OpenAI quota 부족 | 429 | `OPENAI_QUOTA_EXCEEDED` |
| OpenAI timeout | 504 | `OPENAI_TIMEOUT` |
| OpenAI 연결 실패 | 502 | `OPENAI_UNAVAILABLE` |
| 인증 실패 | 502 | `OPENAI_AUTHENTICATION_FAILED` |
| 모델 권한 또는 모델 없음 | 502 | `OPENAI_MODEL_UNAVAILABLE` |
| 응답 형식 검증 실패 | 502 | `INVALID_AI_RESPONSE` |
| API 키 미설정 | 503 | `OPENAI_NOT_CONFIGURED` |

전사문이 빈 문자열이거나 공백 문자만 포함하면 service가 HTTP 422
`EMPTY_TRANSCRIPT`로 변환한다. 사용자는 마이크를 확인하고 다시 녹음할 수 있다.
내용이 존재한다면 전사문 앞뒤 공백은 임의로 제거하지 않는다.

외부 오류의 원문 message는 API 키나 provider 내부 정보가 섞일 수 있어 사용자에게
그대로 전달하거나 로그에 남기지 않는다.

## 관측 정보와 개인정보

개발 환경에서 `OPENAI_USAGE_LOG_ENABLED=true`일 때만 상세 usage 로그를 남긴다.

기록 가능:

- 요청 종류
- 모델명
- token 수와 오디오 초
- latency
- 성공 여부
- retry 횟수
- 안전하게 제한한 오류 타입

기록 금지:

- 오디오 bytes
- 파일 내용
- 전사문
- prompt
- 평가 결과
- API 키

운영 환경에서는 상세 usage 로깅이 강제로 꺼진다.

## 현재 테스트가 증명하는 것

`tests/test_transcriptions.py`:

- provider가 반환한 앞뒤 공백과 반복을 그대로 보존
- codec parameter가 있는 WebM MIME 정규화
- 지원하지 않는 MIME 거부
- MIME과 signature 불일치 거부
- 3초의 짧은 유효 녹음 허용
- 0초 녹음 거부
- 최대 크기 초과 거부
- 빈 문자열, 공백, 개행만 포함한 전사 결과 거부
- request ID, 모델명, token usage, provider 오디오 길이 응답

`tests/test_openai_provider.py`:

- 기본 STT 모델명 전달
- 전사 usage 파싱
- token usage와 duration usage를 provider 결과에 구분해 보존
- SDK에 민감하거나 불필요한 저장 인자를 보내지 않음
- 평가 provider의 retry와 prompt cache 동작
- usage 로그에 민감 데이터가 들어가지 않음

아직 증명하지 않는 것:

- OpenAI 전사 rate limit 재시도
- STT timeout과 연결 오류의 route 응답
- 실제 브라우저가 만든 MP4/M4A/WAV fixture
- 손상된 container의 실제 decode 실패
- 사람 음성이 없는 잡음 파일 차단
- 동일 요청의 중복 비용 방지
- STT 품질과 필러 보존율

## 변경할 때 지켜야 할 계약

- 공개 필드 변경은 프론트엔드 타입과 매핑을 함께 수정한다.
- 새 오류는 HTTP 상태, code, 사용자 메시지, 테스트를 함께 추가한다.
- 모델이나 prompt 변경은 API 동작 변경이므로 평가 결과를 기록한다.
- 파일 제한을 바꾸면 프론트엔드와 백엔드 값을 동시에 맞춘다.
- 관측 필드를 추가해도 음성 또는 전사 내용을 로그에 넣지 않는다.
- provider 교체 시에도 service의 도메인 오류 계약을 유지한다.
