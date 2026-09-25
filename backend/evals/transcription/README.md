# STT 평가 자료 폴더

이 폴더는 운영 기능이 아니라 STT 모델과 prompt를 같은 조건으로 비교하기 위한
오프라인 시험 공간이다.

## 파일 구조

```text
transcription/
├─ README.md
├─ manifest.example.json   공개 가능한 구조 예시
├─ manifest.local.json     로컬 실제 목록, Git에서 제외
├─ samples/                평가 음성, Git에서 제외
└─ results/                모델 전사 결과, Git에서 제외
```

## 시작 방법

1. `manifest.example.json`을 `manifest.local.json`으로 복사한다.
2. 명시적 동의를 받았거나 공개 사용이 허용된 음성만 `samples/`에 둔다.
3. [`gold-v1-rc1` 규범안](../../../docs/ai/gold-transcript-guide.md)에 따라 두 사람이
   모델 출력을 보지 않고 독립적으로 전체 Gold를 작성한다. 현재는 파일럿 검증 전이다.
   단어·필러가 미확정인 자료는 보류하고, 조각·단어 내부 중단·혼용 언어·복수 화자는
   수동 도전 자료로 보관한다. 주 비교 manifest에는 적격 단어 평가 자료와 별도
   비음성·입력 거부 검사 자료만 넣는다. 분리한 자료의 수와 이유도 기록한다.
4. 음성의 특징을 소문자 tag로 기록한다.
5. Gold에서 추출한 `referenceTranscript`를 대조한 뒤 아래 명령으로 로컬 manifest를 검사한다.

주석 파일 `samples/<sample-id>.gold.json`은 음성과 함께 Git에서 제외된다. 현재
평가 CLI는 이 파일을 읽거나 검사하지 않는다. 작성 규범의 검수 상태·평가 묶음은
자동으로 반영되지 않으며, tag만 붙여도 제외되지 않는다. 조각을 그대로 출력한 모델이
현 채점에서 감점될 수 있으므로 조각 자료의 점수를 주 WER와 합치지 않는다.
JSON 형식 검사만으로 Gold의 내용이나 실제 녹음과의 일치가 검증되지는 않는다.

다음은 `backend/`에서 실행한다. 성공하면 요약 문장만 출력하고 전사문은 출력하지 않는다.
이 명령은 manifest 계약을 검사하며, 음성·Gold 파일의 존재나 내용은 검사하지 않는다.

```powershell
@'
from pathlib import Path
from app.evals.transcription_dataset import TranscriptionDataset

try:
    TranscriptionDataset.model_validate_json(
        Path("evals/transcription/manifest.local.json").read_text(encoding="utf-8")
    )
except (OSError, ValueError):
    raise SystemExit("Manifest validation failed; inspect the private file locally.")
print("Manifest schema valid.")
'@ | .\.venv\Scripts\python.exe -
```

## 저장된 실행 결과 평가하기

### 로컬 Whisper로 실행 결과 만들기

**현재 구현:** 아래 명령은 `manifest.local.json`과 음성 파일의 존재를 먼저 확인한다.
`--execute-live`를 붙여야 `small.en`을 CPU `int8`로 실행한다. 실행할 때는 제품과 같은
`TranscriptionProcessor`의 입력 검사와 `LocalWhisperTranscriptionProvider`를 사용한다.
평가 음성에 맞춰 파일 상한만 기본 5MB로 높이고, 이 값은 run JSON에 기록한다.
모델 로딩은 측정 전에 끝내므로 `latencyMs`는 준비된 모델의 파일 검사·전사 시간이다.
로컬 모델은 API 요금이 없지만 모델 다운로드와 CPU 사용은 발생할 수 있다.

저장소 루트에서 Docker 이미지를 만들고 평가 폴더와 모델 캐시를 연결한다. Docker
이미지에는 평가 음성과 정답을 복사하지 않는다. 호스트의 `results/`에 결과가 남으므로
컨테이너를 지우거나 다른 컴퓨터로 옮겨도 평가 자료를 따로 관리할 수 있다.

```powershell
docker build -t opencoachai-backend:local-whisper -f backend/Dockerfile backend
docker volume create opencoachai-whisper-cache
$evalDir = (Resolve-Path -LiteralPath .\backend\evals\transcription).Path
New-Item -ItemType Directory -Force .\backend\evals\transcription\results | Out-Null
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_execute_cli --manifest /evals/manifest.local.json --output /evals/results/small-en-001.json --experiment-id small-en-001
```

마지막 명령에 `--execute-live`를 덧붙이면 실제 전사를 실행한다. 같은 이름의 결과를
덮어쓰지 않으므로 반복 측정은 `--output`과 `--experiment-id`에 새 번호를 쓴다.

```powershell
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --mount source=opencoachai-whisper-cache,target=/home/appuser/.cache/huggingface --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_execute_cli --manifest /evals/manifest.local.json --output /evals/results/small-en-001.json --experiment-id small-en-001 --execute-live
```

다른 컴퓨터에서는 저장소 코드와 별도로 `manifest.local.json`, `samples/`, `results/`를
안전하게 옮기고 위 명령을 다시 실행한다. 모델 캐시 볼륨은 새 컴퓨터에서 다시 준비해도
된다. 평가 자료는 Git과 Docker 이미지에서 제외되어 있다.

실행 결과는 기존 채점 명령으로 분석한다.

```powershell
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_cli --manifest /evals/manifest.local.json --run /evals/results/small-en-001.json --output /evals/results/small-en-001-report.json
```

`run JSON`에는 모델 전사 원문이 들어 있다. 이 파일과 성적표를 콘솔에 출력하거나 Git에
추가하지 않는다. 현재 필러·반복 지표는 단어의 위치까지 검증하지 않는 개수 기반
지표이므로, 모델 선택 전에 음성별 출력도 직접 확인한다. RTF는 각 음성의
`latencyMs / 1000 / audioSeconds`로 계산한다. 음성 두 개만으로 p95를 일반화할 수 없다.

### 저장된 답안 채점하기

외부 API를 매번 다시 호출하지 않고, manifest와 저장된 모델 답안을 성적표로 바꿀 수
있다. 아래 명령은 공개 예시 두 파일을 사용해 `results/example-report.json`을 만든다.

```powershell
.\.venv\Scripts\python.exe -m app.evals.transcription_cli `
  --manifest evals/transcription/manifest.example.json `
  --run evals/transcription/run.example.json `
  --output evals/transcription/results/example-report.json
```

`--output`을 생략하면 JSON 성적표를 표준 출력에 표시한다. 성적표에는 다음이 포함된다.

- 전체 micro WER와 단어 오류 수
- 필러와 연속 반복어의 보존율·정밀도
- 음성 sample 실패 수
- 무음·비음성 환각 sample 수
- 기대와 다른 결과 수
- latency p50과 p95
- sample별 상세 점수

## source 값

| 값 | 의미 |
|---|---|
| `synthetic` | 테스트 목적으로 만든 합성 음성 |
| `explicit-test-consent` | 평가 자료 사용에 명시적으로 동의한 사람의 음성 |
| `public-license` | 평가 용도를 허용하는 공개 라이선스 자료 |

출처를 확인할 수 없는 음성은 사용하지 않는다.

## expectedBehavior 값

| 값 | 기대 결과 |
|---|---|
| `transcribe` | 사람이 검수한 `referenceTranscript`와 비교 |
| `empty-or-rejected` | 무음·비음성 입력이며 빈 결과 또는 안전한 거부를 기대 |
| `rejected` | 손상 또는 잘못된 파일이며 입력 단계 거부를 기대 |

## 개인정보 원칙

- 운영 사용자 녹음을 자동으로 복사하지 않는다.
- 이름, 학교, 회사, 주소처럼 개인을 알아볼 수 있는 내용을 넣지 않는다.
- 실제 사람의 음성은 동의 범위와 삭제 요청 방법을 별도로 기록한다.
- `samples/`, `results/`, `manifest.local.json`은 기본적으로 Git에서 제외된다.
- 공개 저장소에는 합성 또는 공개 허가를 확실히 증명할 수 있는 작은 fixture만 별도
  검토 후 추가한다.
