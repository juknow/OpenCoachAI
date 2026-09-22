# 프론트엔드 녹음 구조

## 아주 쉽게 설명하면

브라우저 녹음 코드는 작은 녹음기를 관리한다.

```text
준비 → 마이크 연결 → 녹음 중 → 녹음 완료
  ▲                                  │
  └──────────── 다시 녹음 ────────────┘
```

녹음이 끝나면 두 가지 결과를 만든다.

1. STT 서버로 보낼 오디오 Blob
2. 화면에 보여줄 소리 크기와 침묵 관련 지표

## 관련 파일

| 파일 | 책임 |
|---|---|
| `src/hooks/useRecorder.ts` | 마이크, MediaRecorder, 시간, Blob, 재생 URL 관리 |
| `src/components/RecorderPanel.tsx` | 녹음 상태와 버튼 표시 |
| `src/services/audioAnalysisService.ts` | 녹음 후 RMS 기반 음성 지표 계산 |
| `src/services/httpCoachService.ts` | Blob 검증과 전사 API 업로드 |
| `src/services/transcriptMetricsService.ts` | 전사문 기반 단어·WPM·필러 계산 |
| `src/pages/TranscriptReviewPage.tsx` | 전사 원문 확인과 사용자 수정 |
| `src/types/coach.ts` | 녹음, 음성 지표, 전사 결과 타입 |

경로는 모두 `frontend/`를 기준으로 한다.

## 녹음 상태 기계

`RecordingPhase`는 다음 다섯 상태를 가진다.

| 상태 | 뜻 | 사용자 화면 |
|---|---|---|
| `idle` | 아직 시작하지 않음 | 마이크 선택과 녹음 시작 버튼 |
| `requesting` | 마이크 권한과 stream을 기다림 | 마이크 연결 중 |
| `recording` | 녹음 중 | 시간, 입력 크기, 종료 버튼 |
| `recorded` | Blob과 지표 생성 완료 | 재생, 다시 녹음, 제출 버튼 |
| `error` | 권한 또는 녹음 실패 | 오류와 다시 시작 버튼 |

상태와 함께 다음 값을 관리한다.

- `elapsedSeconds`: 전체 녹음 시간
- `inputLevel`: 녹음 중 화면에 보여주는 입력 크기
- `artifact`: 제출 가능한 Blob, URL, MIME, 지표 묶음
- `devices`: 사용 가능한 입력 마이크
- `selectedDeviceId`: 사용자가 고른 마이크

## 지원 파일 선택

브라우저가 실제로 만들 수 있는 첫 번째 형식을 선택한다.

1. `audio/webm;codecs=opus`
2. `audio/webm`
3. `audio/mp4`

브라우저마다 MediaRecorder 지원 범위가 다르기 때문에 순서대로
`MediaRecorder.isTypeSupported()`를 확인한다. 지원 형식이 하나도 없으면 녹음을
시작하지 않고 오류를 보여준다.

현재 녹음 설정:

```text
최대 시간          120초
audioBitsPerSecond 48,000
data chunk 간격    250ms
```

## 자원 정리

녹음 코드는 다음 자원을 반드시 해제한다.

- 마이크 MediaStream track
- 녹음 시간 interval
- 입력 크기 animation frame
- Web Audio AudioContext
- Blob 재생용 object URL

다시 녹음하거나 화면 component가 사라질 때 기존 자원을 정리한다. 사용자가 녹음
중 reset하면 `discardRef`를 사용해 `onstop`에서 새 artifact를 만들지 않는다.

## 녹음 중 입력 크기

녹음 중에는 실시간 stream을 `AnalyserNode`에 연결하고 frequency bin 평균을 계산해
0~100 범위로 표시한다. 이 숫자는 마이크에 소리가 들어오는지 보여주는 UI 값이다.

다음 의미로 사용하면 안 된다.

- 발음 점수
- 마이크 음질 점수
- 실제 음량 dB
- 음성 여부의 확정 판정

## 녹음 후 음성 분석

녹음이 멈추면 `analyzeAudio()`와 재생 URL 생성을 동시에 실행한다. 분석이 성공하면
50ms frame의 RMS를 계산하고 침묵 구간을 추정한다.

오디오 decode가 실패하면 녹음 제출을 바로 막지 않는다. 모든 지표를 0으로 둔
`analysisSucceeded: false` 결과를 반환한다. 지원 브라우저의 decode 제약 때문에
유효한 음성을 잘못 차단하지 않기 위한 현재 정책이다.

반대로 decode에 성공했고 `peakRms < 0.01`, `voicedFrameRatio < 1%`이면 사실상
무음으로 보고 제출 버튼을 막는다.

## 전사 제출

`RecorderPanel`은 다음 조건을 모두 만족할 때만 제출 버튼을 활성화한다.

- 상태가 `recorded`
- artifact가 존재
- 로컬 분석 결과가 사실상 무음이 아님

`App.submitRecording()`은 같은 작업이 진행 중이면 새 요청을 시작하지 않는 in-flight
lock을 사용한다. 이후 provider에 따라 실제 HTTP 서비스 또는 Demo 서비스를 선택한다.

HTTP 서비스는 다음을 수행한다.

1. MIME에서 codec parameter를 제거한다.
2. 허용 확장자를 결정한다.
3. 파일이 900,000바이트 이하인지 검사한다.
4. `FormData`에 파일, 시간, 시도 번호를 넣는다.
5. `/api/transcriptions`에 POST한다.
6. 전사문과 로컬 음성 지표를 `TranscriptResult`로 합친다.
7. request ID, 모델명, usage, provider 오디오 길이를 metadata로 보존한다.

## 원문과 수정문

전사 결과는 두 텍스트를 가진다.

```text
rawText    STT가 처음 반환한 원문
editedText 사용자가 확인하고 수정한 문장
```

수정 화면은 `editedText`만 변경한다. `rawText`를 유지해야 나중에 STT가 무엇을
틀렸는지 평가할 수 있다.

현재 단어 수와 WPM은 사용자가 수정한 문장을 기준으로 다시 계산된다. 따라서 화면의
WPM은 순수한 STT 결과의 단어 수가 아니라 최종 확인 문장의 단어 수를 반영한다.

실제 API 전사에는 `metadata`가 존재하고 Demo 전사에는 없을 수 있다. metadata는
전사 품질과 비용을 나중에 비교하기 위한 관측 정보이며 음성 또는 전사문을 추가로
복제하지 않는다.

## 알려진 한계

- 음량 기반 분석은 배경 음악이나 키보드 소리를 음성으로 오인할 수 있다.
- 첫 번째 오디오 채널만 분석한다.
- pause 경계는 고정된 휴리스틱이며 마이크별로 보정하지 않는다.
- `durationSeconds`는 파일 metadata가 아니라 브라우저 시계로 측정한다.
- 녹음 중 네트워크 상태나 예상 업로드 크기를 알려주지 않는다.
- HTTP timeout 이후 서버의 외부 AI 호출까지 취소되는지는 보장하지 않는다.
- 900KB 제한 값이 프론트엔드와 백엔드에 각각 존재한다.

## 프론트엔드 전사 개선 체크리스트

- [ ] Chrome, Edge, Safari에서 생성되는 MIME과 실제 codec을 기록한다.
- [ ] 3초, 30초, 120초 파일의 실제 크기를 브라우저별로 확인한다.
- [ ] 무음, 작은 목소리, 일정한 배경 소음 fixture로 휴리스틱을 검증한다.
- [ ] 낮은 신뢰 전사 구간을 수정 화면에서 표시한다.
- [ ] 원문으로 되돌리는 동작을 제공한다.
- [ ] 원문 대비 사용자가 수정한 부분을 STT 평가 데이터로 익명 집계할지 결정한다.
- [ ] 집계한다면 명시적 동의, 보존 기간, 삭제 방법을 먼저 설계한다.
