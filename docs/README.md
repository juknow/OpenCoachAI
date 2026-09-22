# OpenCoachAI 문서 지도

## 이 문서 폴더의 역할

코드가 장난감 상자라면 이 폴더는 “어떤 장난감이 어디에 있고 어떻게 함께
움직이는지” 알려주는 설명서다.

문서는 현재 코드에서 직접 확인한 동작과 앞으로 만들 계획을 구분해서 기록한다.
계획이 코드보다 먼저 바뀌더라도 아직 구현된 것처럼 표현하지 않는다.

## 문서 구조

```text
docs/
├─ README.md                 문서 전체 지도
├─ architecture/            프론트엔드부터 AI까지 이어지는 전체 흐름
├─ frontend/                브라우저 화면, 녹음, 로컬 음성 분석
├─ backend/                 FastAPI, 검증, 외부 AI provider
├─ ai/                      STT·LLM 도메인 지식과 평가 방법
├─ contributing/            Git과 협업 규칙
├─ decisions/               중요한 설계 결정을 기록하는 ADR
└─ legacy-site-handoff/     이전 Sites 시스템의 인수인계 자료
```

## 추천 읽기 순서

### 프로젝트를 처음 보는 사람

1. [`../README.md`](../README.md)
2. `architecture/system-overview.md`
3. `architecture/transcription-pipeline.md`

### 녹음과 전사를 작업하는 사람

1. `frontend/audio-recording.md`
2. `backend/transcription-api.md`
3. `ai/stt-domain-guide.md`
4. `ai/stt-evaluation.md`

### 협업과 커밋 규칙을 확인하는 사람

1. [`../AGENTS.md`](../AGENTS.md)
2. [`contributing/git-convention.md`](contributing/git-convention.md)

## 현재 문서 상태

| 문서 | 상태 | 의미 |
|---|---|---|
| `legacy-site-handoff/` | 참고 자료 | 이전 구현을 옮길 때 만든 자료이며 현재 코드와 다를 수 있음 |
| `contributing/git-convention.md` | 현재 규칙 | 앞으로 적용할 브랜치와 커밋 규칙 |
| `architecture/`, `frontend/`, `backend/`, `ai/` | 작성 중 | 현재 React/FastAPI 구현을 기준으로 새로 정리하는 문서 |

## 문서 관리 규칙

- 파일과 함수 이름은 실제 코드와 연결한다.
- “현재 동작”, “문제점”, “목표 설계”를 섞지 않는다.
- API 계약이 바뀌면 관련 프론트엔드와 백엔드 문서를 함께 고친다.
- 중요한 선택에는 선택 이유, 검토한 대안, 되돌릴 조건을 남긴다.
- 문서를 처음 읽는 사람이 이해할 수 있도록 쉬운 설명을 먼저 배치한다.
