# 시스템 전체 구조

## 1. 아주 쉽게 보는 구조

OpenCoachAI에는 네 명의 일꾼이 있다.

1. **브라우저 녹음기**가 사용자의 목소리를 받는다.
2. **백엔드 문지기**가 파일이 안전하고 올바른지 검사한다.
3. **받아쓰기 AI**가 목소리를 영어 문장으로 옮긴다.
4. **OPIc 코치 AI**가 확인된 문장을 읽고 피드백을 만든다.

중요한 점은 받아쓰기 AI의 결과를 곧바로 코치 AI에 주지 않는다는 것이다.
사용자가 전사문을 먼저 확인하고 잘못 들은 부분을 수정할 수 있다.

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ React 브라우저 │ ──▶ │ FastAPI 서버  │ ──▶ │ OpenAI API   │
│ 녹음과 화면    │ ◀── │ 검증과 조립    │ ◀── │ STT와 평가    │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        └── 프로필과 연습 기록은 브라우저 localStorage에 저장
```

## 2. 현재 사용 기술

| 영역 | 기술 | 하는 일 |
|---|---|---|
| 프론트엔드 | React 19, TypeScript, Vite | 화면과 연습 흐름 |
| 녹음 | MediaRecorder API | 마이크 음성을 Blob으로 생성 |
| 로컬 음성 분석 | Web Audio API | 음량, 침묵, 멈춤을 휴리스틱으로 추정 |
| 백엔드 | FastAPI, Pydantic | HTTP API, 입력 검증, 오류 변환 |
| 외부 AI SDK | OpenAI Python SDK | STT와 평가 모델 호출 |
| 저장 | 브라우저 localStorage | 프로필과 완료된 연습 기록 보관 |

현재 별도 데이터베이스와 사용자 로그인은 없다. 오디오 Blob은 재생을 위해 브라우저
메모리에 잠시 존재하지만 연습 기록으로 저장하지 않는다.

## 3. 처음부터 끝까지의 현재 흐름

### 3.1 연습 시작

1. 사용자가 목표 등급, 현재 등급, 관심사, 난이도를 설정한다.
2. 프론트엔드가 조건에 맞는 OPIc 연습 질문을 선택한다.
3. 브라우저 음성 합성으로 질문을 읽어줄 수 있다.

관련 코드:

- `frontend/src/pages/ProfileSetupPage.tsx`
- `frontend/src/pages/PracticeHomePage.tsx`
- `frontend/src/data/questions.ts`
- `frontend/src/hooks/useSpeechSynthesis.ts`

### 3.2 녹음과 로컬 분석

1. 브라우저가 마이크 권한을 요청한다.
2. MediaRecorder가 최대 120초 동안 오디오 조각을 만든다.
3. 녹음 중에는 주파수 데이터의 평균으로 입력 크기를 화면에 표시한다.
4. 녹음이 끝나면 오디오 Blob과 재생 URL을 만든다.
5. Web Audio API가 첫 채널을 해독해 음량 기반 지표를 계산한다.

관련 코드:

- `frontend/src/hooks/useRecorder.ts`
- `frontend/src/components/RecorderPanel.tsx`
- `frontend/src/services/audioAnalysisService.ts`

### 3.3 음성 전사

1. 프론트엔드가 오디오, 녹음 시간, 시도 번호를 multipart 요청으로 전송한다.
2. 백엔드가 크기, 녹음 시간, MIME, 파일 signature를 검사한다.
3. OpenAI provider가 영어 STT 모델을 호출한다.
4. 백엔드는 전사문과 요청 ID를 반환한다.
5. 프론트엔드는 전사문에서 단어 수, WPM, 필러, 연속 반복 단어를 계산한다.

관련 코드:

- `frontend/src/services/httpCoachService.ts`
- `frontend/src/services/transcriptMetricsService.ts`
- `backend/app/api/routes/transcriptions.py`
- `backend/app/services/transcription_processor.py`
- `backend/app/providers/openai_provider.py`
- `backend/app/prompts/transcription.txt`

### 3.4 사용자 전사문 확인

1. 화면에 STT 원문을 수정 가능한 입력창으로 보여준다.
2. 사용자가 잘못 인식된 부분만 고친다.
3. 원문은 `rawText`, 수정한 문장은 `editedText`로 따로 유지한다.
4. 단어 수와 WPM 같은 텍스트 기반 지표는 수정 문장을 기준으로 다시 계산한다.

관련 코드:

- `frontend/src/pages/TranscriptReviewPage.tsx`
- `frontend/src/types/coach.ts`
- `frontend/src/services/transcriptMetricsService.ts`

### 3.5 OPIc 평가

1. 프론트엔드는 프로필, 질문, 수정 전사문, 음성 지표를 JSON으로 만든다.
2. 백엔드는 고정된 평가 prompt와 동적 사용자 payload를 분리한다.
3. 평가 모델은 Pydantic 기반 Structured Output 형식으로 결과를 생성한다.
4. 백엔드는 등급 범위와 개선 답변 같은 결정론적 값을 조립한다.
5. 프론트엔드는 API 결과를 화면용 모델로 변환해 피드백을 보여준다.

관련 코드:

- `backend/app/api/routes/evaluations.py`
- `backend/app/services/evaluation_v2_service.py`
- `backend/app/providers/openai_provider.py`
- `backend/app/schemas/evaluation.py`
- `backend/app/prompts/evaluation_core.txt`
- `frontend/src/services/httpCoachService.ts`
- `frontend/src/pages/FeedbackPage.tsx`

### 3.6 재도전과 기록

첫 답변이 끝나면 사용자는 세 가지 Retry Mission을 보고 같은 질문에 다시 답할 수
있다. 두 답변의 점수와 말하기 지표 비교는 프론트엔드에서 결정론적으로 수행한다.
완료된 전사문과 평가 결과는 localStorage에 저장하지만 오디오 파일은 저장하지 않는다.

관련 코드:

- `frontend/src/services/comparisonService.ts`
- `frontend/src/services/storageService.ts`
- `frontend/src/state/coachReducer.ts`
- `frontend/src/pages/HistoryPage.tsx`

## 4. 프론트엔드 구조

```text
frontend/src/
├─ components/   여러 화면에서 재사용하는 UI
├─ data/         연습 질문과 정적 데이터
├─ hooks/        녹음과 음성 합성처럼 상태이 있는 브라우저 기능
├─ pages/        사용자가 보는 각 단계의 화면
├─ services/     API, 저장, 분석, 비교 같은 로직
├─ state/        연습 단계와 기록을 바꾸는 reducer
├─ types/        화면 모델과 API 계약 타입
├─ App.tsx       전체 화면 흐름을 연결하는 지휘자
└─ main.tsx      React 시작점
```

`App.tsx`는 현재 많은 흐름을 직접 조정한다. 녹음 제출, 전사 완료, 평가 요청,
재도전 결과 저장이 모두 이곳에 연결되어 있다.

## 5. 백엔드 구조

```text
backend/app/
├─ api/routes/   HTTP 주소와 요청·응답 연결
├─ prompts/      STT와 평가 모델에 전달하는 고정 prompt
├─ providers/    OpenAI SDK를 감싸는 외부 서비스 경계
├─ schemas/      Pydantic 요청·응답·Structured Output 모델
├─ services/     검증과 OPIc 도메인 처리
├─ config.py     환경 변수와 기본 설정
├─ errors.py     내부 오류를 안전한 HTTP 오류로 변환
└─ main.py       FastAPI 앱과 middleware 구성
```

route는 HTTP 형식을 다루고, service는 도메인 규칙을 다루며, provider는 외부 AI를
호출한다. 이 세 층을 나눈 덕분에 테스트에서는 실제 비용 없이 가짜 provider를 넣을
수 있다.

## 6. 데이터가 머무는 곳

| 데이터 | 현재 위치 | 장기 저장 |
|---|---|---|
| OpenAI API 키 | 백엔드 `.env` | 서버 설정에만 존재 |
| 녹음 Blob | 브라우저 메모리 | 저장하지 않음 |
| 재생 URL | 브라우저 메모리 | 화면 종료 시 해제 |
| STT 원문 | React 상태 | 평가 완료 후 연습 기록에 포함 |
| 수정 전사문 | React 상태 | 평가 완료 후 localStorage에 저장 |
| 프로필 | React 상태 | localStorage에 저장 |
| 평가 결과 | React 상태 | localStorage에 저장 |
| usage와 latency | 개발 환경의 안전 로그 | 설정을 켠 경우에만 기록 |

## 7. 현재 경계와 책임

- **브라우저**는 사용자 경험과 빠른 로컬 계산을 책임진다.
- **백엔드**는 보안, 파일 검증, AI 호출, 응답 계약을 책임진다.
- **STT 모델**은 들린 말을 글자로 옮길 뿐 평가하지 않는다.
- **평가 LLM**은 확인된 전사문과 제한된 음성 지표로 피드백을 만든다.
- **사용자**는 STT가 잘못 들은 부분을 최종 확인한다.

이 경계를 지키면 전사 오류와 평가 오류를 따로 찾을 수 있다. 전사문이 틀렸다면
STT 단계의 문제이고, 전사문은 맞지만 조언이 나쁘다면 평가 LLM 단계의 문제다.
