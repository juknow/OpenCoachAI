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

Tests mock the OpenAI provider and do not incur API charges:

```powershell
python -m pytest
python -m ruff check .
python -m compileall app
```
