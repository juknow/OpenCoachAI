# 멀티 엔진 Verbatim STT 평가 실행기

## 1. 무엇을 해결하는가

같은 시험 답안을 여러 채점기에 복사해 각각 채점한다고 생각하면 된다. 이 실행기는 이미
저장된 Gold와 Prediction을 각 평가기에 전달하고, 평가기가 돌려준 결과를 평가기별 파일로
그대로 보존한다. STT 모델을 다시 호출하지 않으므로 같은 Prediction을 다른 평가기로
재평가해도 전사 API 비용은 발생하지 않는다.

```text
저장된 Gold + 저장된 Prediction
                 ↓
        EvaluationOrchestrator
        ├─ Custom Evaluator
        ├─ JiWER
        ├─ Nyra
        ├─ NIST SCTK
        ├─ Hugging Face Evaluate
        └─ MeetEval
                 ↓
       평가기별 native/raw 파일 + 실행 인덱스
```

이 기능은 비교 보고서가 아니다. 평가기 간 자동 비교, 종합 점수, 가중 평균, 순위,
대시보드는 만들지 않는다. `index.json`도 실행 상태와 원본 파일 위치를 찾기 위한 최소
색인일 뿐이다.

## 2. 현재 구현 구조

| 경로 | 책임 |
|---|---|
| `contracts/evaluator.py` | 평가 입력, 시간 구간, 보충 입력, 실행 색인 계약 |
| `evaluators/contract.py` | 공통 Evaluator 규약과 성공 원본 출력 계약 |
| `evaluators/registry.py` | 명시적 평가기 등록과 선택 |
| `evaluators/*.py` | 외부 도구 및 기존 자체 평가기의 얇은 adapter |
| `evaluation_orchestrator.py` | 동시 실행 제한, 실패 격리, 상태 기록 |
| `evaluator_inputs.py` | 기존 manifest/run JSON을 불변 평가 입력으로 변환 |
| `storage/artifacts.py` | 덮어쓰지 않는 평가 실행 폴더와 원본 결과 저장 |
| `interfaces/cli/evaluate_engines.py` | 파일 기반 사용자 명령 |

모든 평가기는 다음 정보를 제공한다.

- `evaluator_id`, `evaluator_version`
- `required_inputs`, `supported_metrics`
- `supports(input)`: 현재 입력과 설치 상태로 실행할 수 있는지 확인
- `evaluate(input)`: 평가기 고유 결과를 반환

오케스트레이터는 선택된 `sample × evaluator`를 제한된 동시성으로 실행한다. 한 평가기가
실패해도 나머지 평가기는 계속 실행된다. 상태는 `success`, `unsupported`, `failed` 중
하나이며 미지원과 실행 실패를 섞지 않는다.

## 3. 평가기 검증 결과

모두 무료로 사용할 수 있는 오픈소스 또는 미국 NIST 배포 소프트웨어다. 다만 사용자는
배포·수정 시 각 upstream 라이선스를 직접 준수해야 한다.

| 평가기 | 연결 방식 | 라이선스와 공식 근거 | 입력 및 현재 환경 상태 |
|---|---|---|---|
| Custom | 기존 `evaluation_engine.py` 직접 재사용 | 이 저장소 코드 | 기존 WER, 개수 기반 filler, 인접 repetition, 비음성 단어 계산의 의미를 유지한다. |
| JiWER 4.0.0 | Python API `process_words`, `process_characters` | [공식 저장소·Apache-2.0](https://github.com/jitsi/jiwer), [사용법](https://jitsi.github.io/jiwer/usage/) | 원문 두 개가 필요하다. 현재 Windows/Python 3.12 설치와 실제 호출을 확인했다. |
| Nyra Verbatim Speech Benchmark | 공식 source checkout을 별도 프로세스로 호출 | [공식 저장소·MIT](https://github.com/nyrahealth/nyra_verbatim_speech_benchmark), [연구 설명](https://nyra-labs.com/research/nyra-verbatim-speech-benchmark) | pip 라이브러리가 아니다. Gold verbatim과 Gold intended가 모두 필요하다. 공식 checkout으로 실제 bridge 호출을 확인했다. |
| NIST SCTK | 설치된 `sclite` 실행 파일 호출 | [공식 저장소와 NIST 라이선스](https://github.com/usnistgov/SCTK) | TRN 입력으로 실행한다. 현재 Windows 작업 환경에는 바이너리가 없어 실제 실행은 미검증이며 `unsupported`가 된다. |
| Hugging Face Evaluate 0.4.6 | `evaluate.load("wer")`, `evaluate.load("cer")` | [공식 저장소·Apache-2.0](https://github.com/huggingface/evaluate), [공식 문서](https://huggingface.co/docs/evaluate/) | 첫 실행에 공식 Hub metric module 다운로드가 필요하다. 현재 환경에서 WER/CER 실제 호출을 확인했다. upstream loader는 한 프로세스에서 직렬화하며 빈 Gold WER은 미지원 처리한다. |
| MeetEval 0.4.3 | SISO WER, cpWER, tcpWER Python API | [공식 저장소·MIT](https://github.com/fgnt/meeteval), [API 문서](https://meeteval.readthedocs.io/) | 텍스트만 있으면 SISO, 양쪽 화자 segment면 cpWER, 완전한 시간까지 있으면 tcpWER다. 현재 Windows/Python 3.12에서는 upstream source build가 실패해 선택 설치하지 못했고 Linux용 의존성으로 제한했다. |

Nyra를 설치된 Python 패키지처럼 흉내 내는 가짜 구현은 만들지 않았다. checkout에 공식 핵심
파일이 있는지 확인한 후, upstream의 `preprocess_gold`와 `evaluate_sample`을 호출한다.
checkout 파일 해시가 평가기 버전에 기록된다. SCTK 역시 결과를 흉내 내지 않고 실제
`sclite`가 없으면 미지원으로 남긴다.

## 4. 원문과 정규화

manifest의 `referenceTranscript`와 run의 `transcript`는 수정하지 않는다. 평가기 입력
계약에 원문 그대로 담고 각 adapter가 자신의 정규화 방식을 명시한다.

| 평가기 | `normalizationProfile` |
|---|---|
| Custom | `legacy-english-token-v1`의 기존 정규화 |
| JiWER | 대소문자·문장부호를 보존하고 연속 공백과 가장자리 공백만 정리하는 `verbatim-whitespace-v1` |
| Nyra | upstream 자체 처리인 `nyra-native-v1` |
| SCTK | 원문을 TRN 한 발화로 전달하는 `sctk-trn-native-v1` |
| HF Evaluate | metric module 자체 처리인 `huggingface-metric-native-v1` |
| MeetEval | upstream 자체 처리인 `meeteval-native-v1` |

평가기별 결과를 같은 의미의 점수로 변환하지 않는다. 예를 들어 Custom WER와 JiWER WER은
정규화 계약이 다르므로 숫자가 우연히 같더라도 같은 결과로 합산하면 안 된다.
HF Evaluate에는 sample/prediction에서 만든 충돌 방지용 `experiment_id`를 전달해 계산
캐시 파일을 분리한다. upstream의 동적 module loader가 thread-safe하지 않아 HF adapter
내부 호출끼리는 직렬화하지만, 다른 평가기와는 계속 병렬 실행된다. 이 값은 STT 실험
ID나 평가 결과를 합치는 키가 아니다.

## 5. 보충 입력

기존 manifest/run 형식은 바꾸지 않는다. 버전, intended 전사, 화자, 타임스탬프가 필요한
평가기에는 선택적인 supplements JSON을 전달한다. 공개 형식 예시는
`backend/evals/transcription/supplements.example.json`에 있다.

- Gold intended는 Nyra가 Gold에서 verbatim 사건 label을 만들 때 필요하다.
- `goldVersion`은 해당 샘플 정답의 개정판이다. `goldConventionVersion`은 정답을
  작성할 때 적용한 규칙 버전이므로 두 값을 구별한다.
- `goldReviewStatus`는 `unknown`, `draft`, `single-reviewed`, `independent-reviewed` 중
  하나다. 검수 완료 상태에는 `goldVersion`과 원문 `goldSha256`을 기록한다. 실행 시
  manifest의 텍스트와 이 해시가 다르면 거부한다. 규칙 버전이 확인되지 않았다면
  `goldConventionVersion`을 비워 두고, 독립 검수 완료를 기록할 때는 규칙 버전도 요구한다. 프로그램은
  청취 사실 자체를 증명하지 않으므로 검수 초안과 판정 기록은 비공개로 별도 보관한다.
- Prediction intended는 Nyra의 intended 계열 결과가 필요할 때 넣는다.
- MeetEval segment는 Gold와 Prediction 양쪽이 모두 있어야 한다.
- 화자 없는 segment, 한쪽만 있는 segment, 일부만 시간이 있는 segment는 자동 보완하지
  않고 `unsupported`로 기록한다.
- 시간 없는 텍스트에 임의 시간을 생성하지 않는다.

supplements는 원문을 대체하지 않고 추가 메타데이터만 제공한다. `sampleId`가 manifest에
없거나 중복이면 실행 전에 거부한다.

supplements가 없으면 평가 실행은 계속 가능하지만 `goldVersion`은 데이터셋 버전에서
임시로 가져오고 `goldVersionSource`를 `dataset-version-fallback`, `goldReviewStatus`를
`unknown`으로 기록한다. 이는 Gold가 독립 검수됐다는 뜻이 아니다.

### 실제 녹음의 Gold 검수 순서

`manifest.local.json`의 `referenceTranscript`는 평가 입력으로 사용되고,
`samples/` 아래의 해당 음성 파일이 원음이다. 각 녹음을 모델 답안을 보지 않고
독립 작성·재청취한다. 필러, 반복, false start,
조각, 불명확 구간을 [`Gold 작성 규범`](gold-transcript-guide.md)에 따라 판정한 뒤
검수 기록을 비공개로 남긴다. 한 명만 검수했다면 `single-reviewed`로 표시한다.
Gold 내용이 바뀌면 이전 manifest를 덮어쓰지 말고 새 데이터셋 개정판과 새 평가
실행 ID를 부여한다. 원음 파일 자체도 고정됐는지 파일 SHA-256으로 확인한다.

## 6. 설치와 실행

기본 개발 환경과 평가 전용 의존성을 분리했다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
```

Windows에서는 MeetEval 항목이 환경 marker로 건너뛰어진다. SCTK와 Nyra는 pip 의존성이
아니다. 공식 SCTK를 빌드·설치한 후 `--sctk-executable`로 `sclite`를 지정하고, Nyra는
공식 저장소 checkout을 `--nyra-checkout`으로 지정한다.

저장소의 공개 예시를 Custom과 JiWER로 실행하는 명령은 다음과 같다.

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.stt_benchmark evaluate-engines `
  --manifest evals/transcription/manifest.example.json `
  --run evals/transcription/run.example.json `
  --output-dir evals/transcription/results `
  --evaluation-run-id example-evaluation-001 `
  --evaluators custom,jiwer `
  --max-concurrency 2
```

모든 등록 평가기를 시도하려면 `--evaluators all`을 사용한다. 설치되지 않았거나 입력이
부족한 평가기는 실행 전체를 중단하지 않고 `unsupported`로 남는다.
쓰기 권한이 제한된 실행 환경에서는 HF Evaluate의 계산 캐시를
`--huggingface-cache-dir <writable-directory>`로 지정한다.

```powershell
.\.venv\Scripts\python.exe -m app.stt_benchmark evaluate-engines `
  --manifest evals/transcription/manifest.local.json `
  --run evals/transcription/results/small-en-001.json `
  --supplements evals/transcription/supplements.local.json `
  --output-dir evals/transcription/results `
  --evaluation-run-id small-en-evaluation-001 `
  --evaluators all `
  --nyra-checkout C:\tools\nyra_verbatim_speech_benchmark `
  --sctk-executable C:\tools\sctk\bin\sclite.exe
```

같은 Prediction을 재평가할 때는 새 `--evaluation-run-id`를 사용한다. 기존 폴더를
덮어쓰지 않으며 같은 ID가 이미 있으면 실패한다.

## 7. 저장 결과

```text
results/<evaluation-run-id>/
├─ index.json
└─ raw/
   └─ <sample-id>/
      ├─ custom.json
      ├─ jiwer.json
      └─ nist-sctk.txt
```

새 `index.json`의 스키마는 `stt-evaluator-index-v2`다. experiment/sample/prediction ID,
Gold·Prediction 버전, Gold 버전 출처·검수 상태·규칙 버전, 원문 UTF-8 SHA-256,
evaluator ID와 버전, 정규화 프로필, 시작·완료 시각, 상태, 원본 결과 상대 경로와
SHA-256, 오류 또는 미지원 사유를 기록한다. 해시는 **정규화하지 않은 텍스트 값**으로
계산한다. Gold나 Prediction 본문은 색인에 복제하지 않는다. 기존 v1 색인은 바꾸거나
소급해 `reviewed`로 표시하지 않는다.

JiWER 원본 결과의 축약 예시는 다음과 같다. 실제 파일에는 정렬 구간과 문자 결과도
포함된다.

```json
{
  "word": {
    "wer": 0.3333333333333333,
    "hits": 4,
    "substitutions": 0,
    "insertions": 0,
    "deletions": 2,
    "references": [["Um", "I", "I", "wan-", "wanted", "that."]],
    "hypotheses": [["Um", "I", "wanted", "that."]]
  }
}
```

## 8. 테스트 구분

비용 없는 일반 테스트는 가짜 evaluator/loader로 선택 실행, 동시 실행 제한, 실패 격리,
미지원, 재평가, 원본 파일과 메타데이터, 기존 Custom 의미와 CLI 호환성을 확인한다.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall app
```

외부 도구 검증은 별도 marker와 환경 변수로 분리한다. 이 테스트도 STT API를 호출하지
않는다. Hugging Face 테스트만 첫 metric 다운로드를 위해 네트워크를 사용한다.

```powershell
$env:RUN_HUGGINGFACE_INTEGRATION = "1"
$env:NYRA_BENCHMARK_CHECKOUT = "C:\tools\nyra_verbatim_speech_benchmark"
$env:SCTK_EXECUTABLE = "C:\tools\sctk\bin\sclite.exe"
.\.venv\Scripts\python.exe -m pytest tests/test_stt_evaluators.py `
  -m "external_integration or network_integration"
```

## 9. 현재 한계와 의도적으로 만들지 않은 것

- fragment, 위치 기반 filler, false start, pause 전용 Custom 지표는 계약상 확장할 수
  있지만 아직 구현하지 않았다. 현재 점수를 그런 지표로 표시하지 않는다.
- MeetEval은 현재 Windows 개발 환경에서 설치되지 않았다. Linux 이미지나 검증된 wheel
  환경에서 별도 통합 검증이 필요하다.
- SCTK는 현재 환경에 실행 파일이 없어 어댑터 계약과 미지원 처리는 검증했지만 실제
  바이너리 출력은 검증하지 못했다.
- HF Evaluate는 metric module을 처음 내려받는 환경에서 네트워크와 캐시가 필요하다.
- 실행 인덱스는 로컬 비공개 파일 저장을 사용한다. 이번 범위에서는 PostgreSQL, 새 API,
  worker queue를 추가하지 않았다.
- 제품 Docker 이미지는 FastAPI와 로컬 Whisper 실행 환경이다. 선택 평가 도구를 모두
  넣으면 이미지 크기·빌드 실패 범위가 커지고 SCTK/Nyra source 관리까지 결합되므로 이번
  구현에서는 바꾸지 않았다. 재현 가능한 전용 평가 이미지가 필요해질 때 별도 Dockerfile로
  분리하는 것이 적절하다.
