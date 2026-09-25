# 백엔드 전사 API

## 아주 쉽게 설명하면

백엔드는 세 사람이 줄을 서서 일하는 구조다.

```text
Route 접수원 → Processor 공통 처리 담당 → Provider STT 연결 담당
```

- **Route**는 브라우저 요청을 받는다.
- **Processor**는 입력을 검사하고 파일명을 정리한 뒤 provider에 전사를 맡기고 결과를 확인한다.
- **Provider**는 선택한 STT 모델을 호출하고 공통 결과로 바꾼다.

이 역할을 나눈 이유는 외부 AI를 바꾸거나 테스트할 때 HTTP 코드와 도메인 규칙을
모두 다시 작성하지 않기 위해서다.

## 관련 파일

| 파일 | 책임 |
|---|---|
| `app/api/routes/transcriptions.py` | multipart 입력과 HTTP 응답 |
| `app/services/transcription_processor.py` | 시간·크기·형식·signature 검증, 안전한 파일명 구성, provider 호출, 빈 결과 검사 |
| `app/providers/base.py` | provider가 지켜야 할 Protocol과 공통 결과 |
| `app/providers/openai_provider.py` | OpenAI SDK 호출, retry, usage 기록 |
| `app/providers/local_whisper_provider.py` | 로컬 Whisper 모델을 공통 전사 결과에 연결하는 비교용 adapter |
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
읽은 bytes와 metadata를 `TranscriptionProcessor`에 전달한다.

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
기본 `get_transcription_provider`는 `OpenAITranscriptionProvider`를 반환한다.
`TRANSCRIPTION_PROVIDER=local_whisper`를 명시하면 로컬 Whisper adapter를
반환한다. `get_evaluation_provider`는 계속 `OpenAIEvaluationProvider`를
반환한다. 따라서 전사 모델만 바꾸고 평가 모델은 그대로 둘 수 있다.

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

### 로컬 Whisper 비교 후보

**현재 구현:** `LocalWhisperTranscriptionProvider`는 `faster-whisper` 모델을
공통 전사 계약에 연결한다. `TRANSCRIPTION_PROVIDER=local_whisper`를 설정하면
`/api/transcriptions`에서 사용할 수 있다. 모델은 파일 크기·형식 검사를 통과한 뒤
별도 thread에서 처음 로드되고, 같은 서버 프로세스의 다음 요청에 재사용된다.
오디오 bytes는 메모리에서 전달한다. 모델의 전사 구간을 순서대로 합치며 필러나
반복을 코드에서 제거하지 않는다. 결과 모델명은 `local-whisper/<모델명>`이다.
모델 준비 실패는 내부 경로나 예외 내용을 공개하지 않고
`503 LOCAL_STT_UNAVAILABLE`로 응답한다.

기본값은 여전히 OpenAI이며, 로컬 선택값의 기본 모델 후보는 영어 전용
`small.en`과 CPU `int8`이다. 모델 파일은 이미지에 포함하지 않는다. 명시적으로
모델을 미리 다운로드하고 Docker 볼륨에 캐시하는 실행 절차는
[백엔드 README](../../backend/README.md#docker에서-로컬-whisper-전사-선택)에 있다.
캐시가 없다면 첫 전사 요청에서 다운로드가 발생할 수 있다. 큰 모델이나 특정 GPU를
기본으로 가정하지 않는 선택이며, 품질이 더 좋다는 뜻은 아니다.
같은 평가 음성으로 환각·필러·반복·속도를 확인하기 전에는 기본 모델을 교체하지
않는다.

Whisper의 `initial_prompt`는 명령문 전달 기능과 같지 않으므로 기존 OPIc 전사
prompt를 그대로 넘기지 않는다. 조용하게 말한 구간을 잘라낼 위험을 줄이기 위해
이 후보에서는 VAD를 끈다. 대신 무음에서 없는 말을 만들어낼 가능성은 고정 평가
자료로 반드시 확인해야 한다. 로컬 실행에도 CPU·GPU·메모리 비용이 있다.
클라우드 provider를 위한 빈 클래스는 추가하지 않는다. 공통
`TranscriptionProvider` 계약이 향후 실제 클라우드 모델을 연결할 자리다.

**아직 구현되지 않음:** GPU 실행, 모델의 사전 품질 평가, OpenAI 키가 없는
브라우저에서 로컬 전사와 평가를 함께 사용하는 무료 모드. 현재 브라우저는
OpenAI 평가 설정이 없으면 Demo Mode로 전환된다.

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

### 모델별 전사 요청 형식

**현재 구현:** `OPENAI_TRANSCRIPTION_MODEL`은 전사 모델만 선택한다. 평가 LLM은
`OPENAI_EVALUATION_MODEL`로 따로 선택한다. 전사 모델을 바꿀 때 필요한 요청 인자도
provider가 구분한다.

| 전사 모델 | 영어 힌트 | `logprobs` 요청 |
|---|---|---|
| `gpt-transcribe` | `extra_body={"languages": ["en"]}` | 보내지 않음 |
| `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-mini-transcribe-2025-12-15` | `language="en"` | 설정이 켜졌을 때만 보냄 |
| `whisper-1` | `language="en"` | 보내지 않음 |

`prompt`와 오디오 파일은 위 모델에 공통으로 전달한다. `logprobs` 설정이 켜져 있어도
지원하지 않는 모델에는 이 필드를 보내지 않는다. `gpt-4o-transcribe-diarize`는
`prompt`를 지원하지 않아 이 단일 화자·원문 보존 흐름의 모델 교체 대상으로 삼지 않는다.
새 전사 모델을 사용할 때는 지원하는 요청 인자를 공식 문서로 확인하고 가짜 provider
테스트를 먼저 추가해야 한다.

**기본 모델 선택 대기:** 공식 예상 비용은 녹음 1분당 `gpt-4o-mini-transcribe`가
$0.003, `gpt-transcribe`가 $0.0045다. 현재 비용 우선 기준에서는 전자가 더 저렴하지만
2027년 2월 26일 종료 예정이다. 녹음 완료 후 전사의 공식 권장 모델은
`gpt-transcribe`다. 지금은 고정 평가 음성의 품질 비교 자료가 없어 어느 모델이
OPIc 답변의 필러·반복을 더 잘 보존하는지 판단할 수 없다. 따라서 기본값은 아직
바꾸지 않았으며, 같은 음성으로 두 모델을 평가한 결과와 실제 비용을 검토한 뒤
사용자 승인으로 결정한다. 자세한 지원 형식과 비용은
[전사 가이드](https://developers.openai.com/api/docs/guides/speech-to-text),
[전사 API](https://developers.openai.com/api/reference/cli/resources/audio/subresources/transcriptions/methods/create),
[가격표](https://developers.openai.com/api/docs/pricing),
[종료 일정](https://developers.openai.com/api/docs/deprecations)을 참고한다.

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
| 로컬 Whisper 모델 준비 실패 | 503 | `LOCAL_STT_UNAVAILABLE` |
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

`tests/test_provider_dependencies.py`, `tests/test_local_whisper_provider.py`:

- 기본 OpenAI 전사 경로 유지와 로컬 provider의 명시적 선택
- 잘못된 파일에는 로컬 모델을 로드하지 않음
- 로컬 전사의 모델명·원문·오디오 길이 응답과 모델 재사용
- 모델 준비 오류의 안전한 `503 LOCAL_STT_UNAVAILABLE` 응답

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
