# OPIc AI Coach OpenAI API 기술 인수인계

작성 기준일: 2026-08-03 (Asia/Seoul)  
대상: 현재 배포된 `opic-ai-coach` Sites 프로젝트의 저장 버전 12 / 소스 커밋 `98fea0ee4540ee945757dbf7d4a271a0d5b9d244`  
목적: 현재 동작을 변경하지 않고 React + FastAPI의 일반 HTTP API 구조로 옮기기 위한 소스 기반 명세

이 문서는 배포 프로젝트의 현재 소스와 배포 환경변수 목록을 직접 확인해 작성했다. API 키, 인증 토큰, 사용자 식별자 등 비밀값은 포함하지 않는다. 배포 환경변수는 현재 0개이므로, 서버에 저장된 `OPENAI_API_KEY`도 없다.

## 가장 중요한 확인 결과

1. 전사는 `gpt-4o-mini-transcribe`, 평가는 `gpt-5.6-luna`를 사용한다.
2. 평가는 Responses API가 아니라 **Chat Completions API**의 Structured Outputs를 사용한다.
3. 현재 배포 환경에는 모델·토큰·API 키 환경변수가 하나도 없다. 따라서 코드 기본값이 실제 적용된다.
4. 현재 배포 평가의 최대 completion token은 `.env.example`의 1,800이 아니라 코드 기본값인 **2,700**이다.
5. README에는 API 키가 없으면 Demo Mode로 전체 흐름이 동작한다고 적혀 있지만, 실제 Route와 테스트는 mock 전사·평가로 전환하지 않는다. 키가 없으면 연결 UI를 열거나 `503 OPENAI_CONNECTION_REQUIRED`를 반환한다.
6. README의 오디오 25MB 제한도 현재 코드와 다르다. 실제 애플리케이션 제한은 **900,000 bytes**다.
7. 재답변 비교는 OpenAI를 호출하지 않지만 브라우저 안에서만 계산하는 것도 아니다. 브라우저가 `/api/compare`를 호출하고, 서버 Route가 결정론적으로 계산한다.

## 확인한 소스

- `app/api/transcribe/route.ts`
- `app/api/evaluate/route.ts`
- `app/api/compare/route.ts`
- `app/api/status/route.ts`
- `lib/prompts/evaluator.ts`
- `lib/schemas.ts`
- `lib/metrics.ts`
- `lib/acoustics.ts`
- `lib/recording-limits.ts`
- `lib/openai-auth.ts`
- `lib/openai-errors.ts`
- `lib/openai-key.ts`
- `lib/storage.ts`
- `components/AudioRecorder.tsx`
- `components/CoachApp.tsx`
- `types/index.ts`
- 관련 Vitest 테스트와 설치된 OpenAI JavaScript SDK 7.3.0 소스

## 1. 실제 사용 모델과 OpenAI 호출 파라미터

### 전사

| 항목 | 현재 값 |
|---|---|
| 모델 | `gpt-4o-mini-transcribe` |
| 앱 endpoint | `POST /api/transcribe` |
| OpenAI endpoint | `POST https://api.openai.com/v1/audio/transcriptions` |
| SDK 호출 | `client.audio.transcriptions.create(...)` |
| `language` | `en` |
| `response_format` | 소스에서 미지정 |
| `temperature` | 소스에서 미지정 |
| `prompt` | `transcription-prompt.txt`의 원문 |
| `stream` | 소스에서 미지정 |
| reasoning effort | 해당 호출에 설정 없음 |
| 출력 토큰 제한 | 해당 호출에 설정 없음 |
| `store` | 해당 호출에 설정 없음 |
| prompt caching | 설정 없음 |

`response_format`은 요청에 명시하지 않는다. 설치된 SDK 타입상 `gpt-4o-mini-transcribe`가 지원하는 형식은 JSON이지만, 이 프로젝트 소스만으로 서버 기본값을 별도로 고정했다고 말할 수는 없다. 코드가 실제 사용하는 값은 `result.text`뿐이다.

실제 호출 코드:

```ts
const client = new OpenAI({ apiKey });
const result = await client.audio.transcriptions.create({
  file: audio,
  model: process.env.OPENAI_TRANSCRIPTION_MODEL || "gpt-4o-mini-transcribe",
  language: "en",
  prompt: "This is an OPIc English speaking practice response. Transcribe it verbatim, word for word. Preserve every audible filler such as um, uh, er, and hmm; repeated words; stutters; false starts; unfinished sentences; broken grammar; incorrect tense; and awkward or incorrect vocabulary. Do not infer intended wording, replace words with natural synonyms, complete sentences, rewrite, correct, summarize, polish, or improve anything the speaker said.",
});
```

### 평가

| 항목 | 현재 배포의 실제 값 |
|---|---|
| 모델 | `gpt-5.6-luna` |
| 앱 endpoint | `POST /api/evaluate` |
| OpenAI endpoint | `POST https://api.openai.com/v1/chat/completions` |
| SDK 호출 | `client.chat.completions.parse(...)` |
| API 종류 | Chat Completions API + Structured Outputs |
| `reasoning_effort` | `none` |
| `verbosity` | `low` |
| `max_completion_tokens` | **2,700** |
| 토큰 설정 함수 범위 | 환경값이 있으면 1,800~3,200으로 clamp |
| `temperature` | 미지정 |
| `top_p` | 미지정 |
| `frequency_penalty` | 미지정 |
| `presence_penalty` | 미지정 |
| `seed` | 미지정 |
| `stream` | 미지정 |
| `n` | 미지정 |
| `store` | 미지정 |
| `response_format` | `zodResponseFormat(..., "opic_practice_evaluation")`, `strict: true` |
| `prompt_cache_key` | `opic-evaluator-v3` |
| `prompt_cache_options` | `{ mode: "explicit", ttl: "30m" }` |
| cache breakpoint | system text content block에 `{ mode: "explicit" }` |

배포 환경변수가 비어 있으므로 `OPENAI_EVALUATION_MAX_TOKENS`는 존재하지 않으며 `DEFAULT_MAX_COMPLETION_TOKENS = 2700`이 적용된다. `.env.example`의 1,800은 로컬에서 그 파일을 복사해 환경변수를 실제 설정했을 때만 적용된다.

`store`는 `false`로 명시한 것이 아니라 요청에서 **생략**한다. 따라서 “현재 소스가 `store: false`를 보낸다”라고 옮기면 현재 동작과 달라진다. 실제 저장 여부에 관한 OpenAI 서버 기본 정책은 이 저장소에서 확인할 수 없다.

평가 호출의 핵심 부분:

```ts
const completion = await client.chat.completions.parse({
  model: process.env.OPENAI_EVALUATION_MODEL || "gpt-5.6-luna",
  reasoning_effort: "none",
  verbosity: "low",
  max_completion_tokens: evaluationTokenLimit(),
  prompt_cache_key: "opic-evaluator-v3",
  prompt_cache_options: { mode: "explicit", ttl: "30m" },
  messages: [systemMessage, userMessage],
  response_format: zodResponseFormat(
    EvaluationModelOutputSchema,
    "opic_practice_evaluation",
  ),
});
```

### 공통 SDK 기본값

앱은 `new OpenAI({ apiKey })` 외에 client 옵션을 설정하지 않는다. 설치된 OpenAI JavaScript SDK 7.3.0 소스 기준으로 다음 기본값이 적용된다.

- base URL: `https://api.openai.com/v1`
- 요청 timeout: 10분(600,000ms)
- 최대 retry: 2회, 즉 최초 요청을 포함하면 최대 3번 시도 가능
- 재시도 대상: 연결 실패·timeout, HTTP 408, 409, 429, 5xx 또는 `x-should-retry: true`
- `Retry-After`/`retry-after-ms`가 있으면 이를 사용하고, 없으면 0.5초부터 지수 backoff와 최대 25% jitter를 적용한다.

프론트 `fetch`에는 별도 `AbortController`, timeout, retry 코드가 없다.

## 2. 전사 기능

### HTTP 요청

```text
POST /api/transcribe
Content-Type: multipart/form-data

audio=<File>
durationSeconds=<decimal string>
attemptNumber=1|2
```

`attemptNumber`는 브라우저가 보내지만 현재 전사 Route에서는 읽거나 사용하지 않는다.

### transcription prompt 전체 원문

원문은 `transcription-prompt.txt`에도 별도 제공한다.

> This is an OPIc English speaking practice response. Transcribe it verbatim, word for word. Preserve every audible filler such as um, uh, er, and hmm; repeated words; stutters; false starts; unfinished sentences; broken grammar; incorrect tense; and awkward or incorrect vocabulary. Do not infer intended wording, replace words with natural synonyms, complete sentences, rewrite, correct, summarize, polish, or improve anything the speaker said.

보존 대상으로 명시된 것은 다음과 같다.

- `um`, `uh`, `er`, `hmm` 같은 들리는 filler
- 반복 단어
- 말더듬
- false start
- 미완성 문장
- 깨진 문법
- 잘못된 시제
- 어색하거나 잘못된 어휘

금지된 처리는 의도 추론, 자연스러운 동의어 치환, 문장 완성, 재작성, 교정, 요약, 다듬기, 개선이다.

### MIME type

서버 허용 목록:

- `audio/webm`
- `audio/mp4`
- `audio/mpeg`
- `audio/mp3`
- `audio/wav`
- `audio/x-wav`
- `audio/ogg`

브라우저 MediaRecorder의 선택 우선순위는 `audio/webm;codecs=opus` → `audio/webm` → `audio/mp4`다. 업로드 직전 `;codecs=...`를 제거한 base MIME type을 사용한다. 브라우저 선택 목록에는 OGG·MP3·WAV가 없지만 서버는 외부 클라이언트가 보내는 해당 형식을 허용한다.

### 파일·시간 제한

| 제한 | 실제 값 | 적용 위치 |
|---|---:|---|
| 최소 녹음 시간 | 5초 | 브라우저와 서버 Route |
| 최대 녹음 시간 | 120초 | 브라우저 MediaRecorder |
| 서버의 최대 시간 검증 | 없음 | 확인 불가가 아니라 코드상 미구현 |
| 최소 파일 크기 | 512 bytes | 브라우저 완료 검사와 서버 Route |
| 최대 파일 크기 | 900,000 bytes | 브라우저 제출 전과 서버 Route |
| 녹음 bitrate | 48,000 bps | MediaRecorder option |
| 120초 예상 payload | 약 720,000 bytes | 코드의 산식 |

서버가 120초 상한을 다시 검증하지 않으므로 일반 HTTP 이식에서도 현재 동작을 그대로 재현하려면 이 차이를 유지해야 한다.

### 전사 오류 처리

- 파일 누락: 400, `녹음 파일을 찾을 수 없습니다.`
- 5초 미만: 400, `5초 이상 녹음한 답변만 전사할 수 있습니다.`
- 512 bytes 미만: 422, 유효한 음성 데이터가 없다는 안내
- 900,000 bytes 초과: 413 + `RECORDING_TOO_LARGE`
- 지원하지 않는 MIME: 415
- 키 없음: 503 + `OPENAI_CONNECTION_REQUIRED`
- 빈 전사 결과: 422, 재녹음 또는 직접 입력 안내
- OpenAI 오류: 공통 오류 매핑 적용
- 그 밖의 예외: 500, `전사 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.`

브라우저는 전사 실패 시 오류 배너를 표시하고 연습 녹음 화면으로 돌아간다. 자동 재녹음이나 mock 전사 대체는 없다.

## 3. 음성 분석

### 전체 녹음 시간

MediaRecorder의 `onstart`에서 `performance.now()`를 저장한다. 250ms 간격 timer가 다음을 계산한다.

```ts
elapsed = Math.floor((performance.now() - startedAt) / 1000)
```

종료 시 최종 시간은 다음 둘 중 큰 값이다.

```ts
Math.max(secondsRef.current, Math.floor((performance.now() - startedAt) / 1000))
```

따라서 `durationSeconds`는 정수 초이며 녹음 시작부터 종료까지의 전체 시간이다. 침묵도 포함한다.

### 발화 시간

별도의 `speakingDurationSeconds` 또는 발화 시간 필드는 계산하거나 저장하지 않는다. PCM 분석은 voiced frame 비율을 내부적으로 계산해 `silenceRatio`를 반환하지만, voiced duration 자체는 응답에 포함하지 않는다. WPM도 발화 시간 대신 전체 녹음 시간을 분모로 사용한다.

### PCM 분석과 pause 판정

1. Web Audio API로 Blob을 decode한다.
2. 다채널이면 모든 채널을 평균한다.
3. 원본 sample rate가 16kHz보다 높으면 16kHz로 단순 downsample한다.
4. 40ms frame으로 분할한다.
5. 음성 threshold는 다음 최댓값이다.

```text
max(0.0035, RMS 15 percentile × 2.6, RMS 90 percentile × 0.1)
```

6. threshold 이상인 frame을 voiced로 본다.
7. 첫 voiced frame과 마지막 voiced frame 사이의 연속 silent run만 pause로 센다. 앞·뒤 silence는 내부 pause count에 포함하지 않는다.

정확한 구간:

- `pause < 0.28초`: 무시
- `0.28초 <= pause < 0.9초`: `hesitationPauseCount`
- `pause >= 0.9초`: `longPauseCount`

frame이 40ms이므로 실제 측정값은 0.04초 단위다. 코드의 기준은 0.28/0.9초지만, 0.9초는 frame 배수에 맞춰 다음 0.04초 단위에서 판정될 수 있다.

추가 브라우저 계산값:

- `initialResponseDelaySeconds`: 첫 voiced frame index × 0.04
- `silenceRatio`: `(1 - voicedFrames / allFrames) × 100`, 반올림한 정수
- `pitchRangeSemitones`: 유효 pitch의 10~90 percentile 범위를 semitone으로 변환
- `energyVariationDb`: voiced RMS 10~90 percentile의 dB 차이
- acoustic confidence: 녹음 길이, speech ratio, pitch sample 수로 `low|medium|high`

분석할 신호가 부족하거나 decode가 실패하면 acoustic metrics 전체가 `null`이 되고, 텍스트 지표만 사용한다.

### WPM

단어는 다음 정규식으로 센다.

```regex
[A-Za-z]+(?:'[A-Za-z]+)?
```

WPM:

```text
round(wordCount / durationSeconds × 60)
```

`durationSeconds <= 0` 또는 유한수가 아니면 0이다.

### filler count

대소문자를 낮춘 뒤 단어 경계 정규식으로 다음 표현을 센다.

- functional discourse markers: `well`, `you know`, `i mean`, `actually`, `honestly`, `to be honest`, `let me think`, `the thing is`, `basically`
- hesitation fillers: `um`, `uh`, `er`, `hmm`
- 전체 `fillerWords` 목록에만 추가되는 표현: `like`

`fillerRatePer100Words`는 hesitation fillers 네 종류만 합산한다.

```text
roundTo1Decimal(hesitationFillerCount / wordCount × 100)
```

`like`, `well`, `you know` 등은 이 비율에 포함되지 않는다.

### 브라우저 값과 AI 판단의 구분

| 값 | 계산 주체 | AI에 전달 여부 |
|---|---|---|
| 전체 녹음 시간 | 브라우저 | 전달 |
| 단어 수, WPM | 브라우저 | 전달 |
| 반복 phrase | 브라우저 | 전달, 최대 5개 |
| functional marker | 브라우저 | 전달 |
| hesitation filler와 비율 | 브라우저 | 전달 |
| 전체 `fillerWords` | 브라우저/서버에서 계산하지만 평가 모델에는 제외 |
| 첫 20초 추정 텍스트 | 브라우저 | 전달 |
| pause, silence, pitch, energy | 브라우저 PCM heuristic | 분석 성공 시 전달 |
| 발음·개별 음가·강세·실제 억양 품질 | 계산하지 않음 | AI가 추측하지 못하도록 금지 |
| 7개 차원과 OPIc 연습 등급 | 평가 모델 | Structured Output으로 반환 |

## 4. 평가 기능

### 메시지 구성

- system prompt: `evaluation-prompt.txt`의 `[SYSTEM PROMPT — exact source text]`
- developer prompt: **없음**
- user prompt: JSON 문자열 1개

사용자 메시지의 실제 형식:

```json
{
  "learnerProfile": {
    "targetLevel": "IH",
    "currentLevel": "IM2",
    "difficulty": "medium"
  },
  "question": {
    "type": "description",
    "text": "<question text>",
    "requiredElements": ["<required element>"]
  },
  "attemptNumber": 1,
  "transcript": "<user-confirmed transcript>",
  "deterministicSpeechMetrics": {
    "durationSeconds": 45,
    "wordCount": 67,
    "wordsPerMinute": 89,
    "repeatedPhrases": [],
    "functionalDiscourseMarkers": [],
    "hesitationFillers": [{ "word": "um", "count": 2 }],
    "fillerRatePer100Words": 3,
    "opening20SecondEstimate": "<estimated opening text>",
    "acoustic": null
  },
  "previousAttempt": null
}
```

실제 payload에는 `undefined` 필드가 JSON 직렬화 중 제거된다. acoustic 분석에 성공한 경우만 `acoustic` object가 들어가며, 실패 시 `modelMetrics()` 결과에는 `acoustic` 키가 `undefined`이므로 JSON에서 사라진다. 위 예시의 `null`은 설명용이며 첫 번째 시도에서 반드시 전송되는 실제 값이 아니다. 정확한 템플릿은 `evaluation-prompt.txt`를 참조한다.

### OPIc 연습 등급 규칙

- 공식·보장 점수라고 표현하지 않는다.
- functions/task completion, relevant content/context, connected text type/organization, accuracy/comprehensibility를 종합 평가한다.
- 답변 길이만으로 등급을 변경하지 않는다.
- role-play는 필수 질문 수행, problem-solving은 문제와 해결책, past experience는 특정 사건을 확인한다.
- 근거가 약하면 confidence를 낮춘다.
- 모델이 `mostLikelyLevel`을 `NL|NM|NH|IL|IM1|IM2|IM3|IH|AL` 중 하나로 반환한다.
- API Route는 모델 등급의 바로 아래·바로 위 한 단계로 `estimatedRange`를 결정론적으로 만든다. 최저·최고에서는 경계를 clamp한다.

### 평가 차원

공식 lens의 7개 차원은 모두 0~4 정수 점수와 한 문장 이유를 가진다.

1. `taskCompletion`
2. `contentSpecificity`
3. `discourseOrganization`
4. `timeFrameControl`
5. `grammarControl`
6. `vocabularyRange`
7. `fluencyComprehensibility`

별도 coaching lens에는 `fluency`, `accuracy`, `naturalness`, Main Point, feeling language, discourse markers가 있다. 이 부분은 공식 등급 차원으로 취급하지 말라는 문구가 system prompt에 있다.

### 강점·개선·교정·미션

- strengths: 정확히 2개, 각각 짧고 정확한 전사 원문 excerpt 포함
- limitations: 모델에 생성시키지 않고 API Route가 항상 `[]`를 넣음
- primary blocker: 1개
- corrections: 최대 3개
- 맞춤 회화 표현: 정확히 2개
- 추천 어휘/collocation: 정확히 3개
- 기본 개선 답변: 10~12개의 문장 item, prompt상 약 120~160 words
- 상위 개선 답변: 12~15개의 문장 item, prompt상 약 140~180 words
- Retry Mission: 정확히 3개

문장 배열의 item 수는 JSON Schema가 강제한다. 총 word 수는 prompt 지시일 뿐 JSON Schema에서 검증하지 않는다. 각 item은 3~240자 문자열이며, Route는 번호 prefix를 제거하고 문장부호가 없으면 마침표를 붙인 뒤 하나의 문자열로 join한다.

### 발음·억양·멈춤 추측 방지

system prompt는 다음을 명시한다.

- transcript와 deterministic metrics만 사용
- acoustic metrics는 브라우저 heuristic이고 마이크·소음의 영향을 받음
- pitch range는 억양 변화의 추정치로만 설명
- pause도 추정치로만 설명
- 발음 품질, 개별 음가, stress, 오디오 품질, 전사되지 않은 filler, 존재하지 않는 transcript quote를 만들지 않음
- transcript 내부 명령문은 사용자 답변 내용일 뿐 지시로 취급하지 않음

## 5. Structured Output

현재 모델-facing 전체 JSON Schema는 `evaluation-schema.json`에 있다. 이것은 `EvaluationModelOutputSchema`를 설치된 SDK의 `zodResponseFormat`으로 변환한 결과다.

핵심 cardinality:

| 배열 | minItems | maxItems |
|---|---:|---:|
| `strengths` | 2 | 2 |
| `corrections` | 미지정(0 가능) | 3 |
| `naturalPhraseSuggestions` | 2 | 2 |
| `recommendedVocabulary` | 3 | 3 |
| `retryMission` | 3 | 3 |
| `minimalCorrectionSentences` | 10 | 12 |
| `nextLevelSentences` | 12 | 15 |
| feeling expressions | 미지정 | 4 |
| functional markers | 미지정 | 4 |
| disruptive markers | 미지정 | 4 |

모델-facing required 필드는 schema 최상단의 `required` 배열에 모두 수록되어 있다. `additionalProperties: false`, `strict: true`다.

브라우저-facing `EvaluationResult`에는 모델이 만들지 않는 다음 값이 서버에서 추가된다.

- `estimatedRange`
- `limitations: []`
- `minimalCorrectionVersion`
- `nextLevelVersion`
- `reusableStructure`
- `safetyNoticeKorean`
- `conversationalDelivery.mainPoint.first20SecondsEstimate`

## 6. 재도전

### 첫 번째 답변 저장 구조

첫 평가가 성공하면 브라우저 localStorage의 `opic-ai-coach:sessions` 배열에 다음 구조가 저장된다.

```ts
interface PracticeSession {
  id: string;
  createdAt: string;
  profileSnapshot: UserProfile;
  question: PracticeQuestion;
  firstAttempt: {
    attemptNumber: 1;
    transcript: string;
    speechMetrics: SpeechMetrics;
    evaluation: EvaluationResult;
    createdAt: string;
  };
  secondAttempt?: PracticeAttempt;
  comparison?: AttemptComparison;
}
```

오디오 Blob과 재생 URL은 localStorage에 저장하지 않는다.

### 두 번째 평가 요청

브라우저는 첫 번째 평가 전체를 `previousEvaluation`으로 `/api/evaluate`에 보낸다.

```json
{
  "profile": { "...": "UserProfile" },
  "question": { "...": "PracticeQuestion" },
  "attemptNumber": 2,
  "transcript": "<second confirmed transcript>",
  "speechMetrics": { "...": "second metrics" },
  "previousEvaluation": { "...": "first EvaluationResult" }
}
```

서버는 모델 user message에 첫 평가 전체를 넣지 않고 아래만 축약해 전달한다.

- previous level
- 7개 dimension score
- primary blocker의 title
- Retry Mission 3개

### 두 답변 비교 알고리즘

브라우저가 `/api/compare`에 질문, 첫 시도, 둘째 시도를 보낸다. 비교 Route는 OpenAI SDK를 import하지 않는다.

1. 7개 차원별 `delta = second.score - first.score`를 계산한다.
2. `scoreDelta`는 7개 delta의 합이다.
3. `levelDelta`는 `NL → NM → NH → IL → IM1 → IM2 → IM3 → IH → AL` 순서 index 차이다.
4. `overallImproved = scoreDelta > 0 || levelDelta > 0`이다.
5. 좋아진 차원을 delta 내림차순으로 최대 3개 뽑는다.
6. 좋아진 차원이 없으면 두 번째 평가의 첫 strength를 `유지된 강점`으로 사용한다.
7. remaining issue는 두 번째 평가의 primary blocker다.
8. 다음 문제 유형은 두 번째 평가의 `recommendedNextQuestionType`이다.

### API 비교와 브라우저 로컬 비교의 구분

- 등급 변화, 7개 차원 변화, 개선 여부, 개선 영역, 남은 문제, 다음 추천: **`/api/compare` 서버 Route**
- 답변 시간·단어 수·WPM의 전후 숫자 표시: 브라우저가 두 저장 객체를 직접 렌더링
- OpenAI 비교 호출: 없음

## 7. API 연결 상태

### React 상태

```ts
serverApiConfigured: boolean
sessionApiKey: string
showApiKeyDialog: boolean
pendingAiAction: "transcribe" | "evaluate" | null
storageAvailable: boolean
```

초기화 때 `GET /api/status`의 `apiConfigured`를 `serverApiConfigured`에 넣고, localStorage에 기억된 키가 있으면 `sessionApiKey`에 복원한다.

```text
apiReady = serverApiConfigured || Boolean(sessionApiKey)
```

서버 키가 있으면 브라우저는 키 header를 보내지 않는다. 서버 키가 없으면 현재 세션 키를 `X-OpenAI-API-Key` header로 `/api/transcribe`와 `/api/evaluate`에 보낸다.

### 연결·해제

- 연결: 키 문자열 정규화·검증 → 필요 시 localStorage 저장 → React state 저장 → 대기 중이던 전사 또는 평가 재개
- 자동 연결 유지 미선택: localStorage 키 제거, React memory에만 유지
- 연결 해제: localStorage 키 제거 + `sessionApiKey = ""` + dialog/pending action 초기화
- 서버 환경변수 키가 있는 경우 상태 버튼은 disabled이며 브라우저 연결 해제로 서버 키를 끌 수 없다.

### localStorage 항목

| key | 내용 |
|---|---|
| `opic-ai-coach:profile` | 사용자 프로필 JSON |
| `opic-ai-coach:sessions` | 연습 세션 배열 JSON |
| `opic-ai-coach:openai-api-key` | 사용자가 자동 연결 유지를 선택한 API 키 원문 |

현재 UI 자체가 “암호화 없이 저장”이라고 경고한다.

### 실제 API 키 위치

현재 배포 환경에는 서버 환경변수가 없으므로, 실제 이용 시 키는 다음 둘 중 하나다.

1. 자동 연결 유지 ON: 브라우저 localStorage + React memory
2. 자동 연결 유지 OFF: React memory만

요청할 때 키는 같은 origin의 서버 Route에 custom header로 전송된다. 현재 배포 소스나 이 인수인계 ZIP에는 키가 없다.

### Demo Mode 전환 조건

현재 실행 코드에는 실제 전사·평가 provider를 mock provider로 바꾸는 Demo Mode 전환이 없다. 키가 없으면 UI가 `AI 연결 필요`를 표시하고, 사용자가 전사·평가를 누르면 연결 dialog를 연다. Route를 직접 호출하면 503을 반환한다.

`lib/demo.ts`와 Demo fixture는 테스트·개발용으로 남아 있으나 `CoachApp` 또는 API Route에서 import하지 않는다. README의 “키가 없으면 Demo Mode 전체 흐름” 설명은 현재 코드와 불일치한다.

## 8. 오류, timeout, retry, usage, 비용

### 오류 코드와 사용자 메시지

| HTTP | code | 사용자 메시지 요약 |
|---:|---|---|
| 400 | 없음 | 파일 누락, 5초 미만, 평가/비교 request schema 오류 |
| 401 | `OPENAI_INVALID_KEY` | 키가 올바르지 않거나 비활성화됨 |
| 403 | `OPENAI_PERMISSION_DENIED` | 모델 권한 또는 프로젝트 한도 확인 |
| 404 upstream → 502 | `OPENAI_MODEL_UNAVAILABLE` | 필요한 모델 접근 권한 확인 |
| 413 | `RECORDING_TOO_LARGE` | 페이지 새로고침 후 압축 설정으로 재녹음 |
| 415 | 없음 | 지원하지 않는 오디오 형식 |
| 422 | 없음 | 유효 음성 데이터 없음 또는 빈 전사 |
| 429 | `OPENAI_QUOTA_EXCEEDED` | API 결제 크레딧 충전, ChatGPT 구독과 별도 |
| 429 | `OPENAI_RATE_LIMITED` | 잠시 후 재시도 |
| 503 | `OPENAI_CONNECTION_REQUIRED` | OpenAI API 키 연결 필요 |
| 500 | 없음 | 전사/평가/비교별 fallback 메시지 |

서버 로그에는 OpenAI 오류의 `status`, `code`, `type`만 남기고 message, 키, 오디오, 전사문은 기록하지 않는다.

### timeout과 retry

- 애플리케이션 사용자 정의 timeout: 없음
- OpenAI SDK 기본 timeout: 요청당 10분
- OpenAI SDK 기본 retry: 최대 2회
- 프론트 fetch timeout/retry: 없음
- Structured Output parse 실패·빈 `message.parsed`: 502, 애플리케이션 재호출 없음

### usage token 처리

`completion.usage`를 읽거나 응답 metadata로 반환하거나 localStorage/UI에 저장하는 코드가 없다. 입력·출력·cache token 사용량과 비용은 현재 앱에서 확인할 수 없다. 전사 응답에서도 usage를 처리하지 않는다.

### 비용 최적화를 위해 실제로 축소한 항목

- `reasoning_effort: none`
- `verbosity: low`
- completion token 상한 적용
- 평가 output은 model-facing schema와 browser-facing schema를 분리
- `estimatedRange`, `limitations`, reusable structure, safety notice, opening text를 모델이 생성하지 않음
- 강점 2개, 교정 최대 3개, 회화 표현 2개, 어휘 3개로 제한
- 전체 `fillerWords` 목록은 모델 payload에서 제외
- 두 번째 평가에 첫 평가 전체가 아닌 요약만 전달
- 재답변 비교는 OpenAI 호출 없이 결정론적 Route로 처리
- 질문 음성은 브라우저 SpeechSynthesis 사용
- 명시적 prompt cache key와 system prompt breakpoint 사용

### 평가 응답 예시

운영 OpenAI 응답 원문과 request ID는 저장하지 않으므로 **실제 운영 호출에서 캡처한 응답은 확인 불가**다. 아래는 현재 저장소의 demo/test 문구와 현재 API Route의 후처리 규칙을 조합한, 브라우저-facing contract 예시다. 실제 사용자 데이터나 운영 모델 출력이라고 해석하면 안 된다.

```json
{
  "mostLikelyLevel": "IM3",
  "estimatedRange": { "lower": "IM2", "upper": "IH" },
  "confidence": "medium",
  "confidenceReason": "한 문항의 전사문과 제한된 음성 지표만으로 평가했으므로 전체 시험 수행을 확정할 수 없습니다.",
  "summaryKorean": "질문에 맞는 개인 경험과 이유를 제시했지만, 사건의 흐름을 더 구체적으로 연결하면 IH에 가까워질 수 있습니다.",
  "dimensions": {
    "taskCompletion": { "score": 3, "reason": "주제에는 답했지만 사건의 전개와 마무리를 조금 더 분명하게 만들 수 있습니다." },
    "contentSpecificity": { "score": 3, "reason": "장소의 특징과 개인적인 이유가 포함되었습니다." },
    "discourseOrganization": { "score": 2, "reason": "내용은 연결되지만 사건의 전환과 결론이 약합니다." },
    "timeFrameControl": { "score": 2, "reason": "현재와 과거를 사용했지만 과거 사건 전개가 짧습니다." },
    "grammarControl": { "score": 3, "reason": "일부 단순한 표현이 있지만 의미 전달을 방해하지 않습니다." },
    "vocabularyRange": { "score": 2, "reason": "익숙한 어휘로 명확하게 전달했으나 반복이 있습니다." },
    "fluencyComprehensibility": { "score": 2, "reason": "전사문과 제공된 WPM·반복 지표 범위에서 전반적인 이해가 가능합니다." }
  },
  "conversationalDelivery": {
    "fluency": { "score": 3, "reason": "전반적인 흐름은 이해되지만 사건의 전환이 조금 짧습니다." },
    "accuracy": { "score": 3, "reason": "상황에 맞는 현재와 과거 시제를 대체로 정확하게 사용했습니다." },
    "naturalness": { "score": 2, "reason": "내용은 명확하지만 감정 반응과 대화형 연결 표현을 더할 수 있습니다." },
    "mainPoint": {
      "status": "clear_early",
      "first20SecondsEstimate": "My favorite park is Doldam Park near my home",
      "feedbackKorean": "답변 초반에 좋아하는 공원과 그 이유가 바로 드러납니다."
    },
    "feelingLanguage": {
      "expressions": ["good memories", "special"],
      "feedbackKorean": "감정 단어는 있으나 왜 그렇게 느꼈는지 한 문장 더 확장하면 좋습니다."
    },
    "discourseMarkers": {
      "functional": ["That is why"],
      "disruptive": [],
      "feedbackKorean": "연결 표현을 과하게 넣지 않고 결론을 자연스럽게 이어갑니다."
    }
  },
  "naturalPhraseSuggestions": [
    {
      "contextKorean": "낯선 질문에 반응할 때",
      "phraseEnglish": "Wow, I've never really thought about that before.",
      "usageKorean": "생각할 시간을 벌면서도 질문에 자연스럽게 반응할 수 있어요."
    },
    {
      "contextKorean": "생각을 정리할 때",
      "phraseEnglish": "Well, let me think for a second.",
      "usageKorean": "한 번만 짧게 사용한 뒤 Main Point로 바로 이어가세요."
    }
  ],
  "recommendedVocabulary": [
    {
      "category": "topic",
      "wordOrPhraseEnglish": "a peaceful getaway",
      "meaningKorean": "평화로운 휴식처",
      "whyRecommendedKorean": "공원이 나에게 어떤 장소인지 한 번에 설명할 수 있어요.",
      "exampleSentenceEnglish": "For me, Doldam Park is a peaceful getaway from my busy routine."
    },
    {
      "category": "feeling",
      "wordOrPhraseEnglish": "bring back warm memories",
      "meaningKorean": "따뜻한 추억을 떠올리게 하다",
      "whyRecommendedKorean": "개인적인 감정을 더 자연스럽게 전달해요.",
      "exampleSentenceEnglish": "Walking by the stream always brings back warm memories of my childhood."
    },
    {
      "category": "action",
      "wordOrPhraseEnglish": "unwind",
      "meaningKorean": "긴장을 풀다",
      "whyRecommendedKorean": "공원에서 무엇을 하는지 짧고 회화적으로 표현할 수 있어요.",
      "exampleSentenceEnglish": "I usually go there on weekends to unwind with my friends."
    }
  ],
  "strengths": [
    {
      "title": "개인적인 이유",
      "explanationKorean": "단순 묘사에 그치지 않고 장소가 특별한 이유를 말했습니다.",
      "evidenceFromTranscript": "My favorite park is Doldam Park near my home"
    },
    {
      "title": "질문 관련성",
      "explanationKorean": "답변 전체가 질문의 주제를 벗어나지 않습니다.",
      "evidenceFromTranscript": "I usually go there with my friends on weekends"
    }
  ],
  "limitations": [],
  "primaryLevelBlocker": {
    "title": "과거 사건의 흐름과 결과 부족",
    "explanationKorean": "구체적인 사건의 시작, 예상 밖의 변화, 결과를 더 선명하게 말해야 합니다.",
    "evidenceFromTranscript": "Last spring, I had a picnic there"
  },
  "corrections": [
    {
      "original": "The park is have many flowers.",
      "corrected": "The park has many flowers.",
      "explanationKorean": "현재시제에서 주어 the park에는 has를 사용합니다."
    }
  ],
  "minimalCorrectionVersion": "I would like to talk about my favorite park. It is close to my home. I usually visit it with my friends on weekends. The park has many flowers and a small stream. It also has several exercise machines. I started going there when I was young. Because of that, it brings back good memories. Last spring, I had a picnic there with my friends. We talked together for a long time. That is why the park is special to me.",
  "nextLevelVersion": "I would like to talk about Doldam Park near my home. It is a peaceful place that I often visit on weekends. The park has colorful flowers, a small stream, and exercise machines. I especially like the walking path beside the water. I started going there when I was young. As a result, the place brings back warm childhood memories. Last spring, my friends and I had a picnic there. We brought some food and sat near the stream. The weather was pleasant, so we stayed for several hours. We talked about school and laughed a lot. I felt completely relaxed during that afternoon. In the end, that personal memory is what makes the park special to me.",
  "reusableStructure": [
    { "step": 1, "titleKorean": "한 문장 Main Point", "explanationKorean": "무엇을 묘사할지와 전체 인상을 먼저 말하세요." },
    { "step": 2, "titleKorean": "구체적인 특징", "explanationKorean": "보이는 모습과 대표 특징을 두세 가지 덧붙이세요." },
    { "step": 3, "titleKorean": "개인적인 이유", "explanationKorean": "왜 좋아하는지 감정과 경험으로 마무리하세요." }
  ],
  "retryMission": [
    "경험이 언제 있었는지 첫 두 문장 안에 말하기",
    "예상하지 못한 사건 한 가지와 대응을 추가하기",
    "그 경험이 특별한 이유를 결론으로 말하기"
  ],
  "recommendedNextQuestionType": "past_experience",
  "safetyNoticeKorean": "이 결과는 AI 기반 연습용 추정치이며 공식 OPIc 성적이 아닙니다."
}
```

## 9. 일반 React + FastAPI로 옮길 때의 1:1 매핑

새 설계가 아니라 현재 Sites 전용 Route를 일반 HTTP 서버로 바꾸는 대응표다.

| 현재 Sites/Next 코드 | FastAPI에서 유지할 의미 |
|---|---|
| `GET app/api/status/route.ts` | `GET /api/status` JSON 응답 |
| `POST app/api/transcribe/route.ts` | 같은 multipart field와 status/error body를 받는 Route |
| `POST app/api/evaluate/route.ts` | 같은 JSON request/response 계약의 Route |
| `POST app/api/compare/route.ts` | 같은 결정론적 비교 Route |
| `process.env.*` | FastAPI process environment |
| `X-OpenAI-API-Key` | 현재 browser-key mode를 그대로 재현할 때 같은 request header |
| Zod request validation | 동일 constraint의 Pydantic validation |
| Zod Structured Output | `evaluation-schema.json`과 동일한 strict model output 검증 |
| `Response.json` | 동일 HTTP status와 JSON body |

프론트 계약은 `api-contract.ts`에 정리했다. FastAPI 구현에서 endpoint 이름이나 body shape를 바꾸면 현재 배포 동작의 그대로 이식이 아니므로, 별도 변경으로 관리해야 한다.

## 10. 확인 불가 또는 소스에 없는 항목

- 실제 운영 OpenAI 평가 응답·request ID·usage token: 저장 코드와 로그 fixture가 없어 확인 불가
- prompt cache hit rate와 절감 token 수: usage 미처리로 확인 불가
- OpenAI 서버가 생략된 `store`, `temperature`, `response_format`에 적용한 런타임 기본값: 프로젝트 소스만으로 확인 불가
- Sites gateway 자체의 timeout/retry/body limit 상세: 프로젝트 소스 밖이므로 확인 불가. 앱 자체는 900,000-byte 제한을 먼저 적용함
- 별도 발화 시간: 계산 필드 자체가 없음
- 발음, 개별 음가, 강세의 실제 측정: 구현 없음
- 서버 DB의 사용자 기록: 구현 없음

## 부록: 현재 파일별 역할

- `transcription-prompt.txt`: 전사 prompt 원문
- `evaluation-prompt.txt`: system prompt 원문, developer prompt 부재, user payload 직렬화 형식
- `evaluation-schema.json`: 현재 모델-facing strict Structured Output 전체
- `api-contract.ts`: 프론트↔HTTP 서버 request/response 타입과 저장 구조

