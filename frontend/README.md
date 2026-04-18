# Phishing Detection — React UI

## Development (two terminals)

**Terminal 1 — Flask API** (from repo root):

```bash
cd /path/to/project
python -m venv .venv && source .venv/bin/activate   # once
pip install -r requirements.txt
python -m src.api
```

API default: `http://127.0.0.1:5000`

**Terminal 2 — Vite dev server** (proxies `/predict`, `/explain`, `/examples`, `/health` to Flask):

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`

## Production build (single Flask process)

From repo root:

```bash
cd frontend && npm ci && npm run build && cd ..
```

This creates `frontend/dist/`. When `frontend/dist/index.html` exists, `src.api` serves the SPA at `/` and `/assets/...`.

Run:

```bash
gunicorn --bind 0.0.0.0:$PORT src.api:app
```

## Environment

- `CORS_ORIGINS` — optional comma-separated list (e.g. `http://localhost:5173`). Default `*` for dev.
- `PRELOAD_MODEL` — `1`/`0` (default `1`).

## API used by the UI

| Method | Path       | Body                          |
|--------|------------|-------------------------------|
| POST   | `/predict` | `{ "url" }` or `{ "email_text" }` |
| POST   | `/explain` | `{ "url" }`                   |
| GET    | `/examples`| —                             |
| GET    | `/health`  | —                             |
