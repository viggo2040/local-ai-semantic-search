"""
Motores de busqueda.

Incluye full-text, semantic, hybrid y filtros estructurados.
"""

from collections import defaultdict

from .chroma_store import search_semantic as chroma_search_semantic
from .file_registry import (
    filter_files as registry_filter_files,
    search_full_text as registry_search_full_text,
)


def build_snippet(text: str, query: str, size: int = 300) -> str:
    """Genera snippet contextual."""

    if not text:
        return ""

    if not query:
        return text[:size]

    lower_text = text.lower()
    lower_query = query.lower()
    index = lower_text.find(lower_query)

    if index == -1:
        return text[:size]

    start = max(0, index - 80)
    end = min(len(text), index + 220)
    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet

    if end < len(text):
        snippet += "..."

    return snippet


def aggregate_by_file(rows: list[dict], query: str, score_key: str) -> list[dict]:
    """Agrupa resultados por archivo."""

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["file_path"]].append(row)

    results = []

    for file_path, items in grouped.items():
        best_item = sorted(items, key=lambda item: item.get(score_key, 0.0))[0]

        results.append({
            "file_name": best_item["file_name"],
            "file_path": file_path,
            "extension": best_item["extension"],
            "best_score": best_item.get(score_key),
            "matching_chunks": len(items),
            "preview_chunk_index": best_item.get("chunk_index"),
            "preview_text": build_snippet(best_item.get("text", ""), query),
            "full_text": best_item.get("text", ""),
        })

    return results


def full_text_search(query: str = "", top_k: int = 20) -> dict:
    """Ejecuta busqueda full-text."""

    rows = registry_search_full_text(query=query, filename=None, top_k=top_k)
    results = aggregate_by_file(rows=rows, query=query, score_key="score")

    return {
        "status": "ok",
        "mode": "full-text",
        "query": query,
        "top_k": top_k,
        "results_count": len(results),
        "results": results,
    }


def semantic_search(query: str, top_k: int = 20) -> dict:
    """Ejecuta busqueda semantica."""

    rows = chroma_search_semantic(query=query, top_k=top_k)
    results = aggregate_by_file(rows=rows, query=query, score_key="distance")

    return {
        "status": "ok",
        "mode": "semantic",
        "query": query,
        "top_k": top_k,
        "results_count": len(results),
        "results": results,
    }


def hybrid_search(query: str, top_k: int = 20) -> dict:
    """Combina full-text y semantic search."""

    semantic_rows = chroma_search_semantic(query=query, top_k=top_k * 3)
    fulltext_rows = registry_search_full_text(
        query=query,
        filename=None,
        top_k=top_k * 3,
    )

    merged = {}

    for row in semantic_rows:
        file_path = row["file_path"]
        semantic_distance = row.get("distance", 999.0)
        semantic_score = 1.0 / (1.0 + semantic_distance)

        merged[file_path] = {
            "file_name": row["file_name"],
            "file_path": file_path,
            "extension": row["extension"],
            "semantic_score": semantic_score,
            "fulltext_score": 0.0,
            "bonus_score": 0.0,
            "preview_text": row["text"],
        }

    for row in fulltext_rows:
        file_path = row["file_path"]

        if file_path not in merged:
            merged[file_path] = {
                "file_name": row["file_name"],
                "file_path": file_path,
                "extension": row["extension"],
                "semantic_score": 0.0,
                "fulltext_score": 1.0,
                "bonus_score": 0.0,
                "preview_text": row["text"],
            }
        else:
            merged[file_path]["fulltext_score"] = 1.0
            merged[file_path]["bonus_score"] = 0.5

    results = []

    for item in merged.values():
        final_score = item["semantic_score"] + item["fulltext_score"] + item["bonus_score"]

        results.append({
            "file_name": item["file_name"],
            "file_path": item["file_path"],
            "extension": item["extension"],
            "semantic_score": round(item["semantic_score"], 4),
            "fulltext_score": round(item["fulltext_score"], 4),
            "bonus_score": round(item["bonus_score"], 4),
            "final_score": round(final_score, 4),
            "preview_text": build_snippet(item["preview_text"], query),
        })

    results = sorted(results, key=lambda item: item["final_score"], reverse=True)
    results = results[:top_k]

    return {
        "status": "ok",
        "mode": "hybrid",
        "query": query,
        "top_k": top_k,
        "results_count": len(results),
        "results": results,
    }


def files_filter(
    extension: str | None = None,
    filename: str | None = None,
    path_contains: str | None = None,
    text_contains: str | None = None,
    limit: int = 100,
) -> dict:
    """Ejecuta filtros estructurados sobre archivos."""

    rows = registry_filter_files(
        extension=extension,
        filename=filename,
        path_contains=path_contains,
        text_contains=text_contains,
        limit=limit,
    )

    return {
        "status": "ok",
        "mode": "files-filter",
        "filters": {
            "extension": extension,
            "filename": filename,
            "path_contains": path_contains,
            "text_contains": text_contains,
            "limit": limit,
        },
        "results_count": len(rows),
        "results": rows,
    }
