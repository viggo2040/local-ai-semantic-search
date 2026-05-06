# Local AI Semantic Search Agent

Local-first AI semantic search agent for private document repositories.

## Current status

MVP 1 started.

Implemented:

- FastAPI backend skeleton.
- `/health` endpoint.
- `/index-folder` endpoint.
- `/search` endpoint.
- `/ask` endpoint.
- TXT, Markdown, CSV, PDF and DOCX extractors.
- File hash registry using SQLite.
- Ollama embeddings integration.
- Chroma vector store integration.
- GitHub Pages portfolio updated with project progress.

## Stack

- Python
- FastAPI
- Ollama
- nomic-embed-text
- Chroma
- LangChain-compatible architecture
- React + Vite portfolio page
- GitHub Actions deployment to `gh-pages`

## Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ollama models

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Run backend

From repository root:

```bash
uvicorn backend.app.main:app --reload
```

## Test health

```bash
curl http://127.0.0.1:8000/health
```

## Index folder

```bash
curl -X POST http://127.0.0.1:8000/index-folder ^
  -H "Content-Type: application/json" ^
  -d "{\"path\":\"D:/Documents\",\"recursive\":true}"
```

## Search

```bash
curl -X POST http://127.0.0.1:8000/search ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"operational continuity\",\"top_k\":5}"
```

## Ask

```bash
curl -X POST http://127.0.0.1:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What documents mention operational continuity?\",\"top_k\":5}"
```

## GitHub Pages

The portfolio page is deployed through GitHub Actions to the `gh-pages` branch.

After the first successful workflow run:

```text
Settings → Pages
Source: Deploy from a branch
Branch: gh-pages
Folder: /root
Save
```
