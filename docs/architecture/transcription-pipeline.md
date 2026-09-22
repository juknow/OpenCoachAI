# 음성 녹음부터 전사 완료까지

## 1. 한 문장 설명

브라우저가 만든 음성 파일을 백엔드가 검사하고, OpenAI STT가 받아쓴 글을 다시
브라우저에 돌려주면 사용자가 잘못 들은 부분을 확인한다.

## 2. 다섯 단계 비유

```text
① 녹음기      ② 소리 검사       ③ 문지기       ④ 받아쓰기 AI    ⑤ 확인 책상
브라우저  ───▶ 브라우저 분석 ───▶ FastAPI ───▶ OpenAI STT ───▶ 사용자 검토
```

- **녹음기**는 목소리를 오디오 Blob으로 만든다.
- **소리 검사**는 너무 조용한 녹음인지 대략 확인한다.
- **문지기**는 파일 크기와 형식이 올바른지 확인한다.
- **받아쓰기 AI**는 들린 말을 영어 글자로 옮긴다.
- **확인 책상**에서 사용자가 STT의 실수만 바로잡는다.

## 3. 현재 실제 요청 순서

```text
사용자
  │ 녹음 시작
  ▼
useRecorder
  │ MediaRecorder로 Blob 생성
  ├──────────────▶ audioAnalysisService
  │                  음량 기반 지표 계산
  │
  ▼
App.submitRecording
  │
  ▼
httpCoachService.transcribe
  │ POST /api/transcriptions (multipart/form-data)
  ▼
FastAPI transcription route
  │
  ▼
TranscriptionService
  │ 시간·크기·MIME·signature 검증
  ▼
OpenAIProvider.transcribe
  │ OpenAI Audio Transcriptions API
  ▼
전사문 + requestId
  │
  ▼
createTranscriptResult
  │ 단어·WPM·필러·반복 계산
  ▼
TranscriptReviewPage
```

## 4. 브라우저 녹음

현재 `frontend/src/hooks/useRecorder.ts`가 다음 순서로 녹음한다.

1. `navigator.mediaDevices.getUserMedia()`로 마이크 권한을 요청한다.
2. 사용자가 선택한 마이크가 있으면 해당 `deviceId`를 사용한다.
3. 지원되는 첫 MIME 형식을 선택한다.
   - `audio/webm;codecs=opus`
   - `audio/webm`
   - `audio/mp4`
4. MediaRecorder를 `48,000 bits/second`로 만든다.
5. 250ms마다 생성되는 오디오 조각을 메모리에 모은다.
6. 사용자가 종료하거나 120초가 되면 녹음을 멈춘다.
7. 조각을 하나의 Blob으로 합치고 재생 URL을 만든다.

녹음 파일은 현재 서버나 localStorage에 장기 저장하지 않는다.

## 5. 브라우저 음성 지표

`frontend/src/services/audioAnalysisService.ts`는 Web Audio API로 파일을 해독하고
첫 번째 채널을 0.05초 단위로 나눈다. 각 구간의 RMS 음량을 사용해 다음을 추정한다.

| 값 | 계산 의미 | 주의점 |
|---|---|---|
| `initialDelaySeconds` | 처음 소리가 나타날 때까지 시간 | 주변 소음도 소리로 잡힐 수 있음 |
| `shortPauses` | 0.28~0.9초 조용한 구간 수 | 실제 망설임인지 알 수 없음 |
| `longPauses` | 0.9초보다 긴 조용한 구간 수 | 문장 사이 자연스러운 쉼도 포함 |
| `silenceRatio` | 전체 중 조용한 frame 비율 | 마이크 감도에 영향을 받음 |
| `energyVariation` | RMS 변화량 | 억양을 직접 측정하지 않음 |
| `peakRms` | 가장 큰 RMS | 음질이나 발음을 뜻하지 않음 |
| `voicedFrameRatio` | 기준 음량 이상 frame 비율 | 사람 목소리 여부를 확정하지 못함 |

이 계산은 UX 보조용 휴리스틱이다. 발음 정확도, 강세, 개별 음가, 실제 억양을
측정하지 않는다.

## 6. 프론트엔드 업로드 계약

`frontend/src/services/httpCoachService.ts`는 전송 전에 다음을 확인한다.

- Blob MIME이 지원 형식인지
- 파일 크기가 900,000바이트 이하인지

요청:

```http
POST /api/transcriptions
Content-Type: multipart/form-data
```

| 필드 | 형식 | 현재 의미 |
|---|---|---|
| `audio` | 파일 | 브라우저가 녹음한 오디오 Blob |
| `durationSeconds` | 숫자 문자열 | 브라우저가 측정한 전체 녹음 시간 |
| `attemptNumber` | `1` 또는 `2` | 첫 답변인지 재도전인지 표시 |

현재 `attemptNumber`는 백엔드 입력 검증만 통과한 뒤 버려진다. 전사 prompt나 모델
동작에는 영향을 주지 않는다.

프론트엔드 HTTP timeout은 75초다. timeout이 발생하면 브라우저 요청은 취소하지만,
이미 시작된 외부 STT 호출이 서버에서 실제로 중단되는지는 보장하지 않는다.

## 7. 백엔드 파일 검증

`backend/app/services/transcription_service.py`는 외부 API 호출 전에 다음 순서로
검사한다.

| 검사 | 현재 기준 | 실패 코드 |
|---|---:|---|
| 녹음 시간 | `0 < durationSeconds <= 120.5` | `INVALID_AUDIO_DURATION` |
| 최소 파일 크기 | 512바이트 이상 | `AUDIO_TOO_SMALL` |
| 최대 파일 크기 | 설정 기본값 900,000바이트 | `AUDIO_TOO_LARGE` |
| MIME 허용 목록 | webm, mp4, mpeg/mp3, m4a, wav | `UNSUPPORTED_AUDIO_TYPE` |
| 파일 signature | MIME에 맞는 header | `INVALID_AUDIO_FILE` |

파일명에서는 최대 60자의 stem만 사용하고, 검증한 MIME에 맞는 확장자를 새로 붙인다.
그러나 현재 백엔드는 전체 오디오를 실제로 decode하지 않는다. 따라서 header 뒤의
데이터가 손상되었는지, 음성이 들어 있는지, duration이 실제 파일과 같은지는 외부
STT 호출 전까지 확정하지 못한다.

## 8. OpenAI STT 호출

`backend/app/providers/openai_provider.py`는 현재 다음 인자를 보낸다.

```text
model    = OPENAI_TRANSCRIPTION_MODEL
기본값   = gpt-4o-mini-transcribe
language = en
file     = 검증된 파일명, bytes, MIME
prompt   = backend/app/prompts/transcription.txt
```

prompt는 다음을 보존하도록 요구한다.

- `um`, `uh`, `er`, `hmm` 같은 필러
- 반복한 단어
- 말 더듬기
- 다시 시작한 문장
- 끝내지 못한 문장
- 틀린 문법과 시제
- 어색하거나 잘못 사용한 어휘

동시에 문장 완성, 교정, 요약, 자연스럽게 바꾸기, 말하지 않은 내용 추가를 금지한다.

OpenAI rate limit 오류는 설정에 따라 기본 한 번 재시도한다. SDK 자체 재시도는 0으로
두어 재시도 횟수를 provider가 통제한다. 기본 외부 요청 timeout은 60초다.

## 9. 현재 전사 응답

성공 응답:

```json
{
  "transcript": "Um, I I went there yesterday.",
  "requestId": "서버에서 생성한 UUID"
}
```

provider 내부에서는 모델명과 usage를 얻지만 현재 전사 API 응답에는 포함하지 않는다.
개발 환경에서 명시적으로 usage 로그를 켠 경우에만 요청 종류, 모델, token, latency,
성공 여부, 재시도 횟수를 안전하게 기록한다. 음성과 전사문은 기록하지 않는다.

provider는 `response.text`가 문자열인지 검사한다. service는 결과가 빈 문자열 또는
공백 문자뿐인지 추가로 검사하고, 비어 있으면 HTTP 422 `EMPTY_TRANSCRIPT`를 반환한다.
내용이 있는 전사문의 앞뒤 공백은 원문 보존을 위해 제거하지 않는다.

## 10. 전사 결과의 브라우저 후처리

`frontend/src/services/transcriptMetricsService.ts`가 STT 텍스트와 녹음 지표를 합쳐
`TranscriptResult`를 만든다.

```ts
interface TranscriptResult {
  rawText: string
  editedText: string
  wordCount: number
  wpm: number
  fillerCount: number
  repeatedWordCount: number
  metrics: SpeechMetrics
  provider: 'mock' | 'openai'
  requestId?: string
}
```

- `rawText`: STT가 돌려준 원문
- `editedText`: 사용자가 확인하는 문장, 처음에는 원문과 같음
- `wordCount`: 공백 기준 단어 수
- `wpm`: 단어 수 ÷ 전체 녹음 시간
- `fillerCount`: 정규식으로 찾은 영어 필러 수
- `repeatedWordCount`: 바로 이어서 같은 단어가 나온 횟수

사용자가 `editedText`를 바꾸면 단어 수, WPM, 필러, 반복 수를 다시 계산한다.
`rawText`는 유지한다.

## 11. 현재 잘된 점

- API 키를 브라우저에 전달하지 않는다.
- route, service, provider가 나뉘어 테스트하기 쉽다.
- 파일 MIME뿐 아니라 signature도 확인한다.
- STT가 문법을 교정하지 않도록 목적이 분명한 prompt를 사용한다.
- STT 원문과 사용자 수정문을 분리한다.
- 원본 오디오를 장기 저장하지 않는다.
- 외부 AI를 가짜 provider로 바꿔 비용 없이 API 테스트를 실행할 수 있다.

## 12. 현재 부족한 점

| 우선순위 | 부족한 점 | 영향 |
|---|---|---|
| P0 | 동의받은 실제 비원어민 평가 음성 없음 | 실제 사용자 발화에서 개선인지 아직 증명할 수 없음 |
| P0 | 서버 측 실제 음성·decode 검사 없음 | 직접 API 호출 시 무음·손상 파일이 외부 호출까지 감 |
| P1 | 신뢰도와 낮은 확신 구간 미사용 | 사용자가 어디를 집중 확인할지 알 수 없음 |
| P1 | 모델 별칭을 바로 사용 | 모델 업데이트 시 결과가 조용히 달라질 수 있음 |
| P1 | 질문 맥락 사용 여부에 대한 실험 없음 | 고유명사 개선과 편향 위험을 비교하지 못함 |
| P1 | 전사 요청의 서버 멱등성 없음 | 네트워크 재시도 시 중복 비용 가능 |
| P2 | 프론트와 백엔드의 크기 상수가 중복됨 | 한쪽만 바꾸면 계약이 어긋날 수 있음 |
| P2 | 파일의 실제 duration을 서버가 검증하지 않음 | 클라이언트 값을 신뢰함 |

## 13. 목표 파이프라인

```text
녹음
  ↓
형식·크기·실제 decode·음성 존재 검사
  ↓
버전이 고정된 STT 설정으로 전사
  ↓
전사문 + 모델 + usage + 신뢰도 메타데이터
  ↓
낮은 신뢰 구간을 중심으로 사용자 검토
  ↓
rawText와 editedText를 모두 유지
  ↓
확인된 editedText만 평가 LLM으로 전달
```

목표 파이프라인의 각 변경은 고정된 STT 평가 자료로 기존 버전보다 좋아졌음을
확인한 뒤 반영한다.

## 14. 전사 단계 완료 조건

- 지원 브라우저와 오디오 형식이 문서와 테스트에서 일치한다.
- 무음, 손상, 빈 전사 결과가 안전한 오류로 처리된다.
- 전사 원문은 필러와 오류를 임의로 교정하지 않는다.
- 사용자가 낮은 신뢰 구간을 쉽게 확인할 수 있다.
- 동일한 평가 자료로 모델과 prompt의 전후 품질을 비교할 수 있다.
- latency, 실패율, usage를 민감 정보 없이 관측할 수 있다.
- 오디오와 전사 데이터의 보관·삭제 정책이 문서화되어 있다.
- 모든 변경이 자동 테스트와 상세 커밋 기록으로 추적된다.
