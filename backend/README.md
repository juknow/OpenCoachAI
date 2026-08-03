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

Tests mock the OpenAI provider and do not incur API charges:

```powershell
python -m pytest
python -m ruff check .
python -m compileall app
```
