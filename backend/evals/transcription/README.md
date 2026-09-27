# STT 평가 자료 폴더

이 폴더는 운영 기능이 아니라 STT 모델과 prompt를 같은 조건으로 비교하기 위한
오프라인 시험 공간이다.

## 파일 구조

```text
transcription/
├─ README.md
├─ manifest.example.json   공개 가능한 구조 예시
├─ supplements.example.json 평가기별 추가 입력의 공개 형식 예시
├─ manifest.local.json     로컬 실제 목록, Git에서 제외
├─ supplements.local.json  intended·화자·시간 정보, Git에서 제외
├─ samples/                평가 음성, Git에서 제외
└─ results/                모델 전사·평가기 원본 결과, Git에서 제외
   └─ predictions/<experiment-id>/
      ├─ raw/              provider가 반환한 JSON 원본
      └─ run.json          평가기에 넣을 기존 run 계약
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

**현재 로컬 파일럿:** park·travel 음성은 `explicit-test-consent` 자료이며,
`supplements.local.json`의 Gold 검수 상태는 `single-reviewed`다. 위의 두 사람 독립
검수는 목표 절차이지 이 두 샘플에서 완료된 작업이 아니다. 사건·시간 주석도 아직 원음
검수 전이므로 현재 전사문을 확정 Gold 또는 검증된 verbatim 기준으로 표시하지 않는다.

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

### 이미 받은 OpenAI 응답 가져오기

**현재 구현:** `import-openai`는 이미 저장한 JSON 응답의 `text`만 기존 run의
`transcript`로 복사한다. 원본 JSON은 바꾸지 않고 `rawResponsePath`와 원본 바이트
SHA-256을 남긴다. OpenAI API를 다시 호출하지 않는다. `createdAt`은 **가져온 시각**이지
원래 API 호출 시각이 아니다. 응답에 없는 모델명·요청 프롬프트·호출 지연 시간·단어
타임스탬프를 추정하지 않는다. `latencyMs`는 `null`이고, 지연 시간 백분위도 알려진
샘플이 없다면 `null`이다. 원본 `usage`의 duration seconds는 토큰 사용량이나
실측 음성 길이로 바꾸지 않고 원본 JSON에만 보존한다.

park·travel의 현재 비공개 배치는 다음처럼 둔다. `manifest.local.json`의 Gold는
수정하지 않는다. 모델 출력은 Gold의 후보나 대조 자료일 뿐 검수된 정답이 아니다.

```text
samples/junho-opic-park-001.m4a
samples/junho-opic-travel-001.m4a
manifest.local.json                         기존 단독 검수 Gold
results/predictions/openai-gpt-transcribe-001/
├─ raw/junho-opic-park-001.json            API 응답 원본
├─ raw/junho-opic-travel-001.json          API 응답 원본
└─ run.json                                평가용 모델 답안
```

`backend/`에서 다음처럼 가져온다. 모든 manifest 샘플에 대해 응답을 지정하고,
모델명과 요청 설정은 **원본 응답에 없으므로** 실제 호출 기록을 확인한 뒤 기입한다.
프롬프트 SHA-256을 검증할 수 있으면 `--prompt-sha256 SAMPLE_ID=SHA256`을 추가한다.
없다면 값을 만들지 말고 비워 둔다. 원본·run 파일은 Git에서 제외되며 출력 파일이
이미 있으면 덮어쓰지 않는다.

아래는 기존 `openai-gpt-transcribe-001` 배치를 처음 가져올 때의 **기록용 예시**다.
현재 로컬에는 해당 `run.json`이 이미 있으므로 그대로 재실행하면 실패한다. 새 응답을
가져올 때는 원본 파일을 새 비공개 배치 폴더에 두고 `--output`과 `--experiment-id`에
새 값을 사용한다. 기존 배치를 다시 평가하려면 가져오기를 반복하지 말고 저장된
`run.json`을 `evaluate-engines --run`에 전달한다.

```powershell
.\.venv\Scripts\python.exe -m app.stt_benchmark import-openai `
  --manifest evals/transcription/manifest.local.json `
  --response "junho-opic-park-001=evals/transcription/results/predictions/openai-gpt-transcribe-001/raw/junho-opic-park-001.json" `
  --response "junho-opic-travel-001=evals/transcription/results/predictions/openai-gpt-transcribe-001/raw/junho-opic-travel-001.json" `
  --output evals/transcription/results/predictions/openai-gpt-transcribe-001/run.json `
  --experiment-id openai-gpt-transcribe-001 `
  --model gpt-transcribe `
  --prompt-version manual-mixed-v1
```

park 호출에는 프롬프트가 없고 travel 호출에는 verbatim 프롬프트가 있었다. 따라서
`manual-mixed-v1`은 **샘플마다 설정이 달랐다는 기록**이며, 이 배치만으로 공정한
모델 우열을 판정하면 안 된다. 같은 Gold와 Prediction으로 오케스트레이터를 돌리려면
아래의 `evaluate-engines` 명령에서 `--run`을 위 `run.json`으로 지정한다.

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
$runId = "small-en-$([guid]::NewGuid().ToString('N'))"
$runOutput = "/evals/results/$runId.json"
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_execute_cli --manifest /evals/manifest.local.json --output $runOutput --experiment-id $runId
```

마지막 명령에 `--execute-live`를 덧붙이면 실제 전사를 실행한다. 같은 이름의 결과를
덮어쓰지 않는다. 위 검증 명령은 파일을 쓰지 않으므로 바로 아래 실제 실행에서
같은 `$runId`를 재사용한다. 다음 반복 측정에는 새 `$runId`를 만든다.

```powershell
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --mount source=opencoachai-whisper-cache,target=/home/appuser/.cache/huggingface --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_execute_cli --manifest /evals/manifest.local.json --output $runOutput --experiment-id $runId --execute-live
```

다른 컴퓨터에서는 저장소 코드와 별도로 `manifest.local.json`, `samples/`, `results/`를
안전하게 옮기고 위 명령을 다시 실행한다. 모델 캐시 볼륨은 새 컴퓨터에서 다시 준비해도
된다. 평가 자료는 Git과 Docker 이미지에서 제외되어 있다.

실행 결과는 기존 채점 명령으로 분석한다.

```powershell
$reportOutput = "/evals/results/$runId-report.json"
docker run --rm --network none --mount "type=bind,source=$evalDir,target=/evals" --entrypoint python opencoachai-backend:local-whisper -m app.evals.transcription_cli --manifest /evals/manifest.local.json --run $runOutput --output $reportOutput
```

기존 단일 성적표 명령은 출력 경로가 이미 있으면 **덮어쓴다**. 과거 성적표를
보존하려면 매번 새 `$reportOutput`을 지정한다.

`run JSON`에는 모델 전사 원문이 들어 있다. 이 파일과 성적표를 콘솔에 출력하거나 Git에
추가하지 않는다. 현재 필러·반복 지표는 단어의 위치까지 검증하지 않는 개수 기반
지표이므로, 모델 선택 전에 음성별 출력도 직접 확인한다. RTF는 각 음성의
`latencyMs / 1000 / audioSeconds`로 계산한다. 음성 두 개만으로 p95를 일반화할 수 없다.

### 저장된 답안 채점하기

외부 API를 매번 다시 호출하지 않고, manifest와 저장된 모델 답안을 성적표로 바꿀 수
있다. 아래 명령은 공개 예시 두 파일을 사용해 새 결과 이름을 만든다.

```powershell
$exampleReport = "evals/transcription/results/example-report-$([guid]::NewGuid().ToString('N')).json"
.\.venv\Scripts\python.exe -m app.evals.transcription_cli `
  --manifest evals/transcription/manifest.example.json `
  --run evals/transcription/run.example.json `
  --output $exampleReport
```

`--output`을 생략하면 JSON 성적표를 표준 출력에 표시하므로 비공개 자료에는
생략하지 않는다. 성적표에는 다음이 포함된다.

- 전체 micro WER와 단어 오류 수
- 필러와 연속 반복어의 보존율·정밀도
- 음성 sample 실패 수
- 무음·비음성 환각 sample 수
- 기대와 다른 결과 수
- latency p50과 p95
- sample별 상세 점수

## 여러 독립 평가기로 같은 답안 평가하기

기존 성적표와 별개로 Custom·JiWER 등 여러 평가기를 선택해 동시에 실행할 수 있다.
평가기 하나가 실패하거나 설치되지 않아도 다른 평가기는 계속되며 결과를 합산하거나
순위로 바꾸지 않는다.

```powershell
$evaluationRunId = "example-evaluation-$([guid]::NewGuid().ToString('N'))"
.\.venv\Scripts\python.exe -m app.stt_benchmark evaluate-engines `
  --manifest evals/transcription/manifest.example.json `
  --run evals/transcription/run.example.json `
  --output-dir evals/transcription/results `
  --evaluation-run-id $evaluationRunId `
  --evaluators custom,jiwer `
  --max-concurrency 2
```

결과는 `results/<evaluationRunId>/index.json`과
`results/<evaluationRunId>/raw/<sample-id>/<evaluator-id>.*`에 저장된다. 기존 폴더를
덮어쓰지 않으므로 재평가에는 새 실행 ID를 쓴다. Nyra·SCTK·HF Evaluate·MeetEval의
설치 상태와 supplements 입력은
[`멀티 엔진 평가 문서`](../../../docs/ai/stt-multi-engine-evaluation.md)를 확인한다.
새 실행의 색인 v2에는 정규화 전 Gold·Prediction의 UTF-8 SHA-256과 Gold 개정판 출처가
함께 기록된다. 해시가 같으면 채점한 텍스트 값이 같았다는 근거가 되지만, 사람이 원음을
듣고 정답을 검수했다는 증거는 아니다.

## 로컬 산출물 보존과 정리

**현재 상태:** `samples/`, `results/`, `manifest.local.json`, `supplements.local.json`은
Git과 제품 Docker 이미지에 들어가지 않는다. 이 폴더의 파일은 코드만 다시 받아서는
복원되지 않는다. 저장소에는 실제 보존 만료일·백업·복원 절차가 아직 확정돼 있지 않다.

음성·Gold·검수 작업지와 모델 원본 응답은 원천 자료다. `run.json`은 평가에 사용한
Prediction을, 평가 폴더의 `index.json`과 `raw/`는 그 실행 조건과 평가기 원본
출력을 보존한다. 점수 파일의 내용이 같아도 색인의 버전·검수 상태·설정이 다르면
실행 이력을 합치거나 삭제하지 않는다. 공개 예시로 만든 출력만 재생성 가능한
정리 후보로 분류하되, 참조와 백업을 확인하기 전에는 자동 삭제하지 않는다.

정확한 파일별 분류, 동의·보존 기간 확인, 백업·복구 검증, 별도 삭제 승인 절차는
[`ADR 0003`](../../../docs/decisions/0003-stt-evaluation-artifact-retention.md)에 있다.
이 문서를 작성하면서 기존 로컬 파일을 이동하거나 삭제하지 않았다.

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
