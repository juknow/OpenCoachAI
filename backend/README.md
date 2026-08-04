# OPIc Coach API

FastAPI backend for local OPIc transcription and structured practice evaluation.
The default provider uses Ollama and faster-whisper and does not require an API key.

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Install the Windows Ollama application, then explicitly download the configured LLM:

```powershell
ollama pull qwen3:4b
```

Download the faster-whisper model once. Runtime auto-download is disabled so a
practice request never starts a hidden model download:

```powershell
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base.en')"
```

Keep these defaults in `backend/.env` for the confirmed machine profile:

```dotenv
AI_PROVIDER=local
OLLAMA_MODEL=qwen3:4b
OLLAMA_CONTEXT_LENGTH=4096
OLLAMA_MAX_CONCURRENT_EVALUATIONS=1
WHISPER_MODEL=base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_CPU_THREADS=4
WHISPER_LANGUAGE=en
WHISPER_LOCAL_FILES_ONLY=true
```

Run the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

To inspect token and latency metadata locally, set both of these values in
`backend/.env`:

```dotenv
APP_ENVIRONMENT=development
USAGE_LOG_ENABLED=true
```

Usage logs contain request type, model, token counts, latency, success, and retry
count only. They never include audio, transcripts, prompts, evaluation text, or the
API key. Detailed usage logging is forced off when `APP_ENVIRONMENT=production`.

Local usage logs report Ollama prompt and generated token counts when available.
They never contain transcript, prompt, audio, or evaluation content.

## API versions and lazy improvements

- `POST /api/evaluations` keeps the legacy eager response contract.
- `POST /api/v2/evaluations` returns the feedback fields used by the React UI and
  the 10-12 sentence base answer only.
- `POST /api/v2/improvements/higher` creates the 12-15 sentence upper-level answer
  on demand. Identical requests are coalesced and reused by the bounded result cache.
- `GET /api/readiness` distinguishes an unavailable Ollama process, a missing
  Ollama model, a missing faster-whisper package, and a missing Whisper model.
- `POST /api/v3/transcriptions` returns `rawTranscript`, deterministic speech
  metrics, timestamps, model, and request ID.
- `POST /api/v3/evaluations` accepts separate `rawTranscript` and
  `confirmedTranscript` values and evaluates only the user-confirmed value.
- `POST /api/v3/improvements/higher` preserves lazy upper-answer generation.

The frontend stores a generated upper-level answer with the practice record. Older
records that already contain both answers remain readable and do not call the lazy
endpoint again.

The result cache is process-local. Before running more than one backend instance,
follow [shared-idempotency.md](docs/shared-idempotency.md); do not scale horizontally
until a shared implementation has passed the same cache and privacy contract tests.

Tests mock all AI providers and do not call Ollama or faster-whisper:

```powershell
python -m pytest
python -m ruff check .
python -m compileall app
```
