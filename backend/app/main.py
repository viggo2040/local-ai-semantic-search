"""
Backend principal FastAPI.

Fase 11.2:
- full-text;
- semantic;
- hybrid;
- filtros estructurados;
- watcher;
- logs rotativos;
- resumen de logs;
- monitoreo backend;
- metricas SQLite y ChromaDB.

No usa Ollama.
No usa LLM remoto.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .chroma_store import chroma_health, chroma_metrics
from .file_registry import init_registry, registry_health, registry_metrics
from .indexer import index_file, index_folder
from .metrics_store import metrics_store
from .logger_config import (
    backend_runtime_metrics,
    log_exception,
    log_info,
    log_summary,
    read_logs,
)
from .search_engine import (
    files_filter,
    full_text_search,
    hybrid_search,
    semantic_search,
)
from .watcher import (
    start_watcher,
    stop_watcher,
    watcher_status,
)

APP_VERSION = "0.13.1"

app = FastAPI(
    title="Local Indexed Search Engine",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexFileRequest(BaseModel):
    """Request para indexar archivo."""

    file_path: str


class IndexFolderRequest(BaseModel):
    """Request para indexar carpeta."""

    folder_path: str
    recursive: bool = True
    reindex_existing: bool = False
    limit: int | None = None


class FullTextSearchRequest(BaseModel):
    """Request para busqueda full-text."""

    query: str = ""
    top_k: int = 20


class SemanticSearchRequest(BaseModel):
    """Request para busqueda semantica."""

    query: str
    top_k: int = 20


class HybridSearchRequest(BaseModel):
    """Request para busqueda hibrida."""

    query: str
    top_k: int = 20


class FilesFilterRequest(BaseModel):
    """Request para filtros estructurados."""

    extension: str | None = None
    filename: str | None = None
    path_contains: str | None = None
    text_contains: str | None = None
    limit: int = 100


class WatcherStartRequest(BaseModel):
    """Request para iniciar watcher."""

    folder_path: str


@app.on_event("startup")
def startup_event() -> None:
    """Inicializa backend."""

    init_registry()
    log_info(f"Backend startup | version={APP_VERSION}")


@app.get("/health")
def health() -> dict:
    """Estado backend."""

    return {
        "status": "ok",
        "service": "local-indexed-search-engine",
        "version": APP_VERSION,
        "llm": "disabled",
        "ollama": "removed",
    }


@app.get("/logs")
def logs_endpoint(
    lines: int = 200,
    level: str | None = None,
    contains: str | None = None,
) -> dict:
    """Retorna logs recientes."""

    return read_logs(
        lines=lines,
        level=level,
        contains=contains,
    )


@app.get("/logs/summary")
def logs_summary_endpoint() -> dict:
    """Retorna resumen del log backend."""

    return log_summary()


@app.get("/monitoring/runtime")
def monitoring_runtime_endpoint() -> dict:
    """Retorna metricas runtime del backend."""

    return backend_runtime_metrics()


@app.get("/monitoring/metrics")
def monitoring_metrics_endpoint() -> dict:
    """Retorna metricas consolidadas."""

    return {
        "status": "ok",
        "version": APP_VERSION,
        "runtime": backend_runtime_metrics(),
        "registry": registry_metrics(),
        "chroma": chroma_metrics(),
        "watcher": watcher_status(),
        "logs": log_summary(),
    }


@app.get("/monitoring/status")
def monitoring_status_endpoint() -> dict:
    """Retorna estado consolidado del backend."""

    registry = registry_health()
    chroma = chroma_health()
    watcher = watcher_status()
    runtime = backend_runtime_metrics()

    components = {
        "api": "ok",
        "registry": registry.get("status"),
        "chroma": chroma.get("status"),
        "watcher": "running" if watcher.get("running") else "stopped",
        "runtime": runtime.get("status"),
    }

    return {
        "status": "ok",
        "version": APP_VERSION,
        "components": components,
        "registry": registry,
        "chroma": chroma,
        "watcher": watcher,
        "runtime": runtime,
    }


@app.get("/monitoring/diagnostics")
def monitoring_diagnostics_endpoint() -> dict:
    """Retorna diagnostico operacional extendido."""

    from pathlib import Path
    import os

    registry = registry_health()
    chroma = chroma_health()
    watcher = watcher_status()
    runtime = backend_runtime_metrics()
    logs = log_summary()

    registry_db_path = Path("backend/data/registry.sqlite")
    log_file_path = Path("logs/backend.log")
    chroma_path = Path("backend/data/chroma")

    return {
        "status": "ok",
        "version": APP_VERSION,
        "runtime": runtime,
        "metrics_store": metrics_store.snapshot(),
        "registry": registry,
        "chroma": chroma,
        "watcher": watcher,
        "logs": logs,
        "paths": {
            "current_working_directory": os.getcwd(),
            "registry_db": str(registry_db_path),
            "registry_db_exists": registry_db_path.exists(),
            "registry_db_size_bytes": (
                registry_db_path.stat().st_size
                if registry_db_path.exists()
                else 0
            ),
            "chroma_dir": str(chroma_path),
            "chroma_dir_exists": chroma_path.exists(),
            "log_file": str(log_file_path),
            "log_file_exists": log_file_path.exists(),
            "log_file_size_bytes": (
                log_file_path.stat().st_size
                if log_file_path.exists()
                else 0
            ),
        },
    }


@app.get("/registry/health")
def registry_health_endpoint() -> dict:
    """Estado SQLite."""

    return registry_health()


@app.get("/chroma/health")
def chroma_health_endpoint() -> dict:
    """Estado ChromaDB."""

    return chroma_health()


@app.post("/index-file")
def index_file_endpoint(request: IndexFileRequest) -> dict:
    """Indexa archivo."""

    try:
        log_info(f"INDEX REQUEST | {request.file_path}")
        result = index_file(request.file_path, cleanup_existing=True)
        log_info(f"INDEX RESULT | {result}")
        return result

    except Exception as exc:
        log_exception(f"INDEX ERROR | {request.file_path} | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/index-folder")
def index_folder_endpoint(request: IndexFolderRequest) -> dict:
    """Indexa carpeta completa."""

    try:
        log_info(
            f"INDEX FOLDER REQUEST | {request.folder_path} "
            f"recursive={request.recursive} "
            f"reindex_existing={request.reindex_existing} "
            f"limit={request.limit}"
        )
        result = index_folder(
            folder_path=request.folder_path,
            recursive=request.recursive,
            reindex_existing=request.reindex_existing,
            limit=request.limit,
        )
        log_info(
            f"INDEX FOLDER RESULT | found={result.get('files_found')} "
            f"indexed={result.get('indexed_count')} "
            f"skipped={result.get('skipped_count')} "
            f"errors={result.get('errors_count')}"
        )
        return result

    except Exception as exc:
        log_exception(f"INDEX FOLDER ERROR | {request.folder_path} | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/search/full-text")
def full_text_search_endpoint(request: FullTextSearchRequest) -> dict:
    """Ejecuta busqueda full-text."""

    try:
        log_info(f"FULL_TEXT SEARCH | query={request.query} top_k={request.top_k}")
        return full_text_search(
            query=request.query,
            top_k=request.top_k,
        )

    except Exception as exc:
        log_exception(f"FULL_TEXT ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/search/semantic")
def semantic_search_endpoint(request: SemanticSearchRequest) -> dict:
    """Ejecuta busqueda semantica."""

    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="query no puede estar vacio")

        log_info(f"SEMANTIC SEARCH | query={request.query} top_k={request.top_k}")
        return semantic_search(query=request.query, top_k=request.top_k)

    except Exception as exc:
        log_exception(f"SEMANTIC ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/search/hybrid")
def hybrid_search_endpoint(request: HybridSearchRequest) -> dict:
    """Ejecuta busqueda hibrida."""

    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="query no puede estar vacio")

        log_info(f"HYBRID SEARCH | query={request.query} top_k={request.top_k}")
        return hybrid_search(
            query=request.query,
            top_k=request.top_k,
        )

    except Exception as exc:
        log_exception(f"HYBRID ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/files/filter")
def files_filter_endpoint(request: FilesFilterRequest) -> dict:
    """Ejecuta filtros estructurados."""

    try:
        log_info(
            f"FILES FILTER | extension={request.extension} "
            f"filename={request.filename} path_contains={request.path_contains} "
            f"text_contains={request.text_contains} limit={request.limit}"
        )
        return files_filter(
            extension=request.extension,
            filename=request.filename,
            path_contains=request.path_contains,
            text_contains=request.text_contains,
            limit=request.limit,
        )

    except Exception as exc:
        log_exception(f"FILES FILTER ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/watcher/status")
def watcher_status_endpoint() -> dict:
    """Retorna estado del watcher."""

    return watcher_status()


@app.post("/watcher/start")
def watcher_start_endpoint(request: WatcherStartRequest) -> dict:
    """Inicia watcher."""

    try:
        log_info(f"WATCHER START REQUEST | {request.folder_path}")
        return start_watcher(request.folder_path)

    except Exception as exc:
        log_exception(f"WATCHER START ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/watcher/stop")
def watcher_stop_endpoint() -> dict:
    """Detiene watcher."""

    try:
        log_info("WATCHER STOP REQUEST")
        return stop_watcher()

    except Exception as exc:
        log_exception(f"WATCHER STOP ERROR | {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
