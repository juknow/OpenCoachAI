# OPIc Coach API

FastAPI backend for OpenAI transcription and structured OPIc practice evaluation.
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

Tests mock the OpenAI provider and do not incur API charges:

```powershell
python -m pytest
python -m ruff check .
python -m compileall app
```
