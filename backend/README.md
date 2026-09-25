# OPIc Coach API

FastAPI backend for OpenAI or local Whisper transcription and OpenAI OPIc evaluation.
The browser never receives or stores the OpenAI API key.

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set a newly issued `OPENAI_API_KEY` in `.env`, then run:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

To inspect token and latency metadata locally, set both of these values in
`backend/.env`:

```dotenv
APP_ENVIRONMENT=development
OPENAI_USAGE_LOG_ENABLED=true
```

Usage logs contain request type, model, token counts, latency, success, and retry
count only. They never include audio, transcripts, prompts, evaluation text, or the
API key. Detailed usage logging is forced off when `APP_ENVIRONMENT=production`.

The evaluation calls use an explicit 30-minute prompt-cache breakpoint after the
stable system prompt. Dynamic profile, question, metrics, and transcript JSON stays
after that breakpoint. Logs report `cached_tokens` and `cache_write_tokens`
separately because a GPT-5.6 cache miss can cost more than an uncached read.

## API versions and lazy improvements

- `POST /api/evaluations` keeps the legacy eager response contract.
- `POST /api/v2/evaluations` returns the feedback fields used by the React UI and
  the 10-12 sentence base answer only.
- `POST /api/v2/improvements/higher` creates the 12-15 sentence upper-level answer
  on demand. Identical requests are coalesced and reused by the bounded result cache.

The frontend stores a generated upper-level answer with the practice record. Older
records that already contain both answers remain readable and do not call the lazy
endpoint again.

The result cache is process-local. Before running more than one backend instance,
follow [shared-idempotency.md](docs/shared-idempotency.md); do not scale horizontally
until a shared implementation has passed the same cache and privacy contract tests.

Tests use fake providers and do not incur API charges or download Whisper models:

```powershell
python -m pytest
python -m ruff check .
python -m compileall app
```

## 저장된 STT 답안의 멀티 엔진 평가

제품 API와 별도로, 저장된 Gold와 Prediction을 Custom·JiWER 등 독립 평가기에 전달할
수 있다. 선택 의존성은 제품/개발 의존성과 분리되어 있다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
.\.venv\Scripts\python.exe -m app.stt_benchmark evaluate-engines --help
```

이 명령은 STT 모델이나 유료 API를 호출하지 않는다. 평가기별 입력 조건, 외부 실행
파일, 라이선스, 실행 예시는
[`멀티 엔진 평가 문서`](../docs/ai/stt-multi-engine-evaluation.md)를 확인한다. 평가 도구는
제품 Docker 이미지에 포함하지 않았다.

## Docker에서 로컬 Whisper 전사 선택

**현재 구현:** 기본 `TRANSCRIPTION_PROVIDER=openai`는 기존 전사 경로를 유지한다.
`TRANSCRIPTION_PROVIDER=local_whisper`를 명시하면 전사 API만 로컬 Whisper를 사용한다.
평가 LLM은 여전히 OpenAI다. 로컬 모델은 CPU `int8`로 실행하며 기본 후보는
`small.en`이다. 이 모델의 OPIc 원문 보존 품질은 아직 평가되지 않았다.

저장소 루트에서 이미지와 재사용할 모델 캐시를 준비한다. 모델 다운로드는 이 명령에서
명시적으로 한 번 실행하며, 평가 음성이나 API 키는 필요하지 않다.

```powershell
docker build -t opencoachai-backend:local-whisper -f backend/Dockerfile backend
docker volume create opencoachai-whisper-cache
docker run --rm --mount source=opencoachai-whisper-cache,target=/home/appuser/.cache/huggingface --entrypoint python opencoachai-backend:local-whisper -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8'); print('model ready')"
```

같은 캐시를 연결해 백엔드를 실행한다.

```powershell
docker run --rm -p 127.0.0.1:8000:8000 --mount source=opencoachai-whisper-cache,target=/home/appuser/.cache/huggingface -e TRANSCRIPTION_PROVIDER=local_whisper -e LOCAL_WHISPER_MODEL=small.en opencoachai-backend:local-whisper
```

`GET http://127.0.0.1:8000/api/health`는 모델 다운로드 없이 확인할 수 있다.
실제 `POST /api/transcriptions`는 유효한 음성 파일을 제출할 때 모델을 메모리에
한 번 로드한다. 파일 검사에 실패하면 모델을 로드하지 않는다. 캐시를 연결하지 않으면
새 컨테이너에서 모델을 다시 내려받을 수 있다. 큰 모델은 `LOCAL_WHISPER_MODEL`을
바꾸어 시험할 수 있지만 CPU 속도와 품질을 따로 측정해야 한다.

직접 전사를 확인할 때는 본인이 녹음했거나 평가 사용에 동의받은 900KB 이하 음성을
사용한다. 아래 `sample.webm`과 초 단위 길이는 실제 파일에 맞게 바꾼다.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/transcriptions -F "audio=@sample.webm;type=audio/webm" -F "durationSeconds=5" -F "attemptNumber=1"
```

성공 응답의 `metadata.model`이 `local-whisper/small.en`인지 확인한다.

OpenAI API 키가 없어도 이 전사 API는 직접 호출할 수 있다. 다만 현재 브라우저는
평가 LLM 연결을 확인하기 위해 OpenAI 설정 여부를 사용하므로, 키가 없으면
Demo Mode로 전환된다. 브라우저 전체를 무료 모드로 전환하는 작업은 포함되지 않는다.
