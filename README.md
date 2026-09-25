# OpenCoachAI

OpenCoachAI는 영어로 말한 OPIc 연습 답변을 글자로 옮기고, 그 답변을 분석해
다음 답변에서 무엇을 개선할지 알려주는 연습용 코치다.

## 한눈에 보는 동작

```text
사용자가 영어로 말한다
        ↓
브라우저가 목소리를 녹음한다
        ↓
백엔드가 파일을 검사하고 STT에 전사를 요청한다
        ↓
사용자가 받아쓰기 결과를 확인하고 필요한 부분만 고친다
        ↓
평가 LLM이 OPIc 관점의 피드백과 개선 답변을 만든다
```

아주 쉽게 말하면 `녹음기 → 받아쓰기 선생님 → 확인 책상 → OPIc 코치` 구조다.

## 프로젝트 폴더

| 경로 | 역할 |
|---|---|
| [`frontend/`](frontend/) | 화면, 마이크 녹음, 음성 지표 추정, 전사문 수정, 피드백 표시 |
| [`backend/`](backend/) | 오디오 검증, OpenAI STT 호출, 평가 LLM 호출, API 오류 처리 |
| [`docs/`](docs/) | 전체 구조, 전사 파이프라인, AI 평가법, 협업 규칙 |
| [`AGENTS.md`](AGENTS.md) | 이 저장소에서 작업하는 AI 에이전트의 필수 규칙 |

## 문서 읽는 순서

1. [`docs/README.md`](docs/README.md)에서 문서 지도를 확인한다.
2. 시스템 전체 흐름은 `docs/architecture/`에서 읽는다.
3. 첫 번째 개선 대상인 녹음과 전사는 `docs/frontend/`, `docs/backend/`,
   `docs/ai/`의 관련 문서에서 자세히 읽는다.
   STT 평가 정답 작성 기준은 [`Gold Transcript 규범안`](docs/ai/gold-transcript-guide.md)에서
   확인한다. 현재 `gold-v1-rc1`은 실제 음성 파일럿 검증 전이다.
   평가 코드의 중심 파일과 실행법은 [`STT 품질 평가 방법`](docs/ai/stt-evaluation.md)에서
   확인한다. 여러 오픈소스 평가기를 독립 실행하는 방법은
   [`멀티 엔진 Verbatim STT 평가 실행기`](docs/ai/stt-multi-engine-evaluation.md)에서
   확인한다.
4. 브랜치와 커밋 규칙은
   [`docs/contributing/git-convention.md`](docs/contributing/git-convention.md)에서 확인한다.

## 실행 안내

- 프론트엔드 실행과 빌드: [`frontend/README.md`](frontend/README.md)
- 백엔드 실행과 환경 변수: [`backend/README.md`](backend/README.md)

## 현재 중요한 원칙

- STT 원문과 사용자가 수정한 전사문을 따로 보관한다.
- 필러, 반복, 말 더듬기, 틀린 문법을 STT가 임의로 고치지 않도록 한다.
- 음량 기반 지표와 실제 발음 평가는 구분한다.
- 모델과 프롬프트는 느낌이 아니라 고정된 평가 자료로 비교한다.
- API 키, 음성, 전사문 같은 민감 정보는 로그에 남기지 않는다.

