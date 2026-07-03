# AGENTS.md

## Project Shape
- This is a local-only Python search app: FastAPI backend in `backend/app`, Gradio UI in `gradio_ui`, launcher `run_gradio.py`.
- Ignore `semantica/` and `semantica310/` when searching or editing source; they are checked-in virtual environments with many third-party files.
- Use the Python 3.10 venv `semantica310`; the older `semantica` venv is Python 3.14 and is not the documented runtime.

## Run Commands
- Activate on Windows CMD: `semantica310\Scripts\activate.bat`.
- Start backend from repo root: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`.
- Start UI after backend is running: `python run_gradio.py`.
- Backend health check: `curl http://127.0.0.1:8000/health`.
- Full status check: `curl http://127.0.0.1:8000/monitoring/status`; `watcher: stopped` is normal unless started manually.

## Runtime Defaults
- Backend listens on `127.0.0.1:8000`; Gradio defaults to `127.0.0.1:7861` via `GRADIO_SERVER_PORT`.
- Gradio calls `LOCAL_SEARCH_API_BASE` if set, otherwise `http://127.0.0.1:8000`.
- Persistent state is under `backend/data/registry.sqlite` and `backend/data/chroma`; logs go to `logs/backend.log` with rotation.
- Embeddings are local SentenceTransformers using `intfloat/multilingual-e5-small`; there is no Ollama or remote LLM dependency.

## Indexing And Search Gotchas
- Supported indexed extensions are `.txt`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.png`, `.avif`.
- `POST /index-file` calls `index_file(..., cleanup_existing=True)` to avoid duplicate chunks when reindexing one file.
- `POST /index-folder` skips already indexed files unless `reindex_existing` is true; use `limit` for focused local checks.
- Semantic and hybrid search reject empty queries; full-text search can accept an empty query.
- Watcher is not started on backend startup; start it explicitly with `POST /watcher/start` and stop with `POST /watcher/stop`.

## Verification
- There is no configured pytest/ruff/mypy/CI in the repo; prefer targeted smoke checks against the running API.
- Useful focused flow: index from `test_docs`, then check `/monitoring/metrics`, `/search/full-text`, `/search/semantic`, and `/search/hybrid`.
- For reindex regressions, compare `/monitoring/metrics` before and after reindexing the same file; chunk counts should not grow artificially.

## Style Notes
- Existing code and docstrings are mostly Spanish and often omit accents; keep edits consistent unless touching user-facing text that already uses accents.
