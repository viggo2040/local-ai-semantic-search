from fastapi import FastAPI, HTTPException

from .file_registry import init_registry
from .indexer import index_folder
from .rag import ask
from .schemas import AskRequest, IndexFolderRequest, SearchRequest
from .vectorstore import search

app = FastAPI(
    title="Local AI Semantic Search Agent",
    version="0.1.0",
)


@app.on_event("startup")
def startup() -> None:
    init_registry()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "local-ai-semantic-search",
        "version": "0.1.0",
    }


@app.post("/index-folder")
def index_folder_endpoint(request: IndexFolderRequest) -> dict:
    try:
        return index_folder(request.path, request.recursive)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/search")
def search_endpoint(request: SearchRequest) -> dict:
    try:
        return {
            "query": request.query,
            "results": search(request.query, request.top_k),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ask")
def ask_endpoint(request: AskRequest) -> dict:
    try:
        return ask(request.question, request.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
