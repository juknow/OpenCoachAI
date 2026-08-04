# OPIc Coach frontend

React + TypeScript + Vite client for the OPIc practice flow. The browser records
and plays audio with browser APIs, then calls the FastAPI backend through Vite's
`/api` proxy. It never calls Ollama, faster-whisper, or OpenAI directly.

## Run on Windows

Start the FastAPI backend on `127.0.0.1:8000`, then:

```powershell
cd D:\opic-coach-ai\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The connection dialog reports whether Ollama,
`qwen3:4b`, faster-whisper, and `base.en` are ready. Demo Mode remains available
without either local model.

## Verify

```powershell
npm run lint
npm test
npm run build
```

Stored v1 practice history is migrated to the versioned v2 storage envelope at
read time. The old keys are left intact for rollback.
