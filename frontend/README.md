# OpenCoachAI 프론트엔드

이 폴더에는 OPIc 영어 말하기 연습 화면이 있다. React 앱에서 녹음하고, 전사문을
검토·수정한 뒤 피드백을 확인한다. 마이크 권한을 사용하는 기능은 `localhost` 또는
HTTPS에서 실행해야 한다.

## 필요한 환경

- Node.js `20.19` 이상 또는 `22.12` 이상
- npm

## 설치와 실행

저장소 루트에서 다음 명령을 실행한다.

```powershell
cd frontend
npm ci
npm run dev
```

Vite가 개발 서버 주소를 표시한다. 기본 주소는 `http://localhost:5173`이다.
터미널에서 `Ctrl+C`를 누르면 서버가 종료된다.

## 백엔드 연결

개발 서버는 `/api` 요청을 `http://127.0.0.1:8000`으로 전달한다. OpenAI 연결을
사용하려면 백엔드도 실행해야 한다. 백엔드 설치, `.env`와 API 키 설정은
[`backend/README.md`](../backend/README.md)를 따른다. API 키는 프론트엔드에 넣지 않는다.

앱은 시작할 때 백엔드 연결을 확인하고, 연결 상태와 선택한 사용 방식에 따라 HTTP 또는
Demo 서비스를 사용한다. Demo Mode는 화면 흐름을 시험하는 mock 응답이며 실제 STT나
LLM 결과가 아니다.

## 확인 명령

`package.json`에 정의된 명령은 다음과 같다.

```powershell
npm test       # Node 내장 테스트 실행
npm run lint   # Oxlint 실행
npm run build  # TypeScript 검사 후 배포용 파일 생성
npm run preview # 빌드 결과 미리보기
```

`npm run preview`를 사용하기 전에 `npm run build`를 실행한다. 배포용 파일은
`frontend/dist/`에 생성된다.

## 화면 구조와 설계 문서

화면과 녹음 코드의 위치, 녹음 흐름, 브라우저 음성 지표의 한계는
[`프론트엔드 녹음 문서`](../docs/frontend/audio-recording.md)를 참고한다. 시스템 전체
흐름은 저장소 루트의 [`README`](../README.md)에서 확인할 수 있다.
