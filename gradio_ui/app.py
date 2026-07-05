"""
UI Gradio principal para Local Indexed Search Engine.

Fase 13.1:
- resultados enriquecidos;
- agrupacion por archivo;
- criterio visual 1 archivo = 1 resultado;
- salida JSON usada como fuente interna;
- salida Markdown resumida agregada;
- endpoint /index-folder agregado;
- filename removido desde busqueda.
"""

from __future__ import annotations

import json
import os
import re
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

import gradio as gr
import requests
from PIL import Image


DEFAULT_API_BASE = "http://127.0.0.1:8000"
API_BASE = os.environ.get("LOCAL_SEARCH_API_BASE", DEFAULT_API_BASE).rstrip("/")


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    clean_value = str(value).strip()
    if not clean_value:
        return None
    return clean_value


def normalize_int(value: Any, default: int, minimum: int = 1, maximum: int = 1000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def api_get(endpoint: str, params: dict | None = None, timeout: int = 60) -> dict:
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=timeout)
        payload = response.json()
        return {"ok": response.ok, "status_code": response.status_code, "endpoint": endpoint, "response": payload}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "status_code": None, "endpoint": endpoint, "error": str(exc)}
    except ValueError:
        return {"ok": False, "status_code": response.status_code, "endpoint": endpoint, "error": "Respuesta no JSON", "text": response.text}


def api_post(endpoint: str, payload: dict | None = None, timeout: int = 120) -> dict:
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.post(url, json=payload or {}, timeout=timeout)
        parsed_response = response.json()
        return {"ok": response.ok, "status_code": response.status_code, "endpoint": endpoint, "request": payload or {}, "response": parsed_response}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "status_code": None, "endpoint": endpoint, "request": payload or {}, "error": str(exc)}
    except ValueError:
        return {"ok": False, "status_code": response.status_code, "endpoint": endpoint, "request": payload or {}, "error": "Respuesta no JSON", "text": response.text}


def first_existing_value(item: dict, keys: list[str]) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def extract_result_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        if "response" in payload:
            return extract_result_items(payload["response"])
        for key in ["results", "items", "files", "documents", "matches", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if "file_path" in payload or "filename" in payload or "path" in payload:
            return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def normalize_result_item(item: dict, rank: int) -> dict:
    file_path = first_existing_value(item, ["file_path", "path", "document_path", "source", "source_path", "full_path"])
    file_name = first_existing_value(item, ["file_name", "filename", "name", "document_name"])
    if not file_name and file_path:
        file_name = Path(str(file_path)).name
    if not file_path:
        file_path = file_name or "archivo_desconocido"

    extension = first_existing_value(item, ["extension", "file_extension", "ext"])
    if not extension and file_path:
        extension = Path(str(file_path)).suffix or None

    score = first_existing_value(item, ["final_score", "best_score", "score", "combined_score", "similarity", "distance", "rank_score", "fts_score", "semantic_score"])
    chunk_text = first_existing_value(item, ["chunk_text", "preview_text", "full_text", "text", "content", "snippet", "preview", "metadata_text"])
    image_prompt_text = first_existing_value(item, ["image_prompt_text", "image_metadata_text"])
    chunk_id = first_existing_value(item, ["chunk_id", "id", "document_id", "rowid"])

    return {
        "rank": rank,
        "file_path": str(file_path),
        "file_name": str(file_name or Path(str(file_path)).name),
        "extension": extension,
        "score": score,
        "chunk_id": chunk_id,
        "chunk_text": str(chunk_text or ""),
        "image_prompt_text": str(image_prompt_text or ""),
        "raw": item,
    }


def group_results_by_file(items: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for index, item in enumerate(items, start=1):
        normalized = normalize_result_item(item, rank=index)
        key = normalized["file_path"]
        if key not in grouped:
            grouped[key] = {
                "file_path": normalized["file_path"],
                "file_name": normalized["file_name"],
                "extension": normalized["extension"],
                "best_rank": normalized["rank"],
                "best_score": normalized["score"],
                "matches_count": 0,
                "image_prompt_text": "",
                "chunks": [],
            }
        grouped_item = grouped[key]
        grouped_item["matches_count"] += 1
        grouped_item["chunks"].append(normalized)
        if normalized["image_prompt_text"] and not grouped_item.get("image_prompt_text"):
            grouped_item["image_prompt_text"] = normalized["image_prompt_text"]
        if normalized["rank"] < grouped_item["best_rank"]:
            grouped_item["best_rank"] = normalized["rank"]
        if grouped_item["best_score"] is None and normalized["score"] is not None:
            grouped_item["best_score"] = normalized["score"]
    return sorted(grouped.values(), key=lambda value: value["best_rank"])


def truncate_text(value: str, max_chars: int = 500) -> str:
    clean_value = " ".join(str(value or "").split())
    if len(clean_value) <= max_chars:
        return clean_value
    return clean_value[:max_chars].rstrip() + "..."


def highlight_search_terms(value: str, query: str) -> str:
    clean_value = str(value or "")
    clean_query = str(query or "").strip()
    if not clean_value or not clean_query:
        return clean_value

    terms = [clean_query]
    terms.extend(clean_query.split())
    unique_terms = sorted({term for term in terms if term.strip()}, key=len, reverse=True)
    if not unique_terms:
        return clean_value

    pattern = re.compile("(" + "|".join(re.escape(term) for term in unique_terms) + ")", re.IGNORECASE)
    return pattern.sub(r"**\1**", clean_value)


def highlight_search_terms_html(value: str, query: str) -> str:
    clean_value = escape(str(value or ""))
    clean_query = str(query or "").strip()
    if not clean_value or not clean_query:
        return clean_value

    terms = [escape(clean_query)]
    terms.extend(escape(term) for term in clean_query.split())
    unique_terms = sorted({term for term in terms if term.strip()}, key=len, reverse=True)
    if not unique_terms:
        return clean_value

    pattern = re.compile("(" + "|".join(re.escape(term) for term in unique_terms) + ")", re.IGNORECASE)
    return pattern.sub(r"<strong>\1</strong>", clean_value)


def file_type_label(extension: Any) -> str:
    clean_extension = str(extension or "").strip().lower().lstrip(".")
    labels = {
        "txt": "File Text",
        "pdf": "PDF",
        "docx": "Word",
        "xlsx": "Excel",
        "pptx": "PowerPoint",
        "png": "Imagen PNG",
        "avif": "Imagen AVIF",
    }
    return labels.get(clean_extension, clean_extension or "No detectado")


def is_image_extension(extension: Any) -> bool:
    clean_extension = str(extension or "").strip().lower().lstrip(".")
    return clean_extension in {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "bmp",
        "webp",
        "tif",
        "tiff",
        "avif",
        "heic",
        "heif",
        "ico",
        "svg",
    }


def parent_location(file_path: str) -> str:
    path = Path(file_path)
    parent = str(path.parent)
    if parent in (".", ""):
        return ""
    return parent + "\\"


def format_score(score: Any) -> str:
    if score is None:
        return ""
    try:
        return f"{float(score):.4f}"
    except (TypeError, ValueError):
        return str(score)


def build_result_table_data(api_payload: dict, error_message: str, search_term: str = "") -> tuple[list[list[str]], list[dict]]:
    if not api_payload.get("ok", False):
        return [["Error", "", "", "", "", api_payload.get("error", error_message)]], []

    items = extract_result_items(api_payload)
    grouped_items = group_results_by_file(items)

    if not grouped_items:
        return [["Sin resultados", "", "", "", "", "No se detectaron resultados estructurados en la respuesta."]], []

    rows = []
    metadata = []
    for file_item in grouped_items:
        chunks = file_item.get("chunks", [])
        first_chunk = chunks[0] if chunks else {}
        full_snippet = str(file_item.get("image_prompt_text") or first_chunk.get("chunk_text", ""))
        snippet = truncate_text(full_snippet, max_chars=300)
        snippet = highlight_search_terms(snippet, search_term)
        extension = file_item.get("extension")
        location = parent_location(file_item["file_path"])
        rows.append([
            file_item["file_name"],
            file_type_label(extension),
            location,
            str(file_item.get("best_rank", "")),
            format_score(file_item.get("best_score")),
            snippet,
        ])
        metadata.append({
            "file_name": file_item["file_name"],
            "file_path": file_item["file_path"],
            "location": location,
            "type": file_type_label(extension),
            "is_image": is_image_extension(extension),
            "snippet_full": full_snippet,
            "search_term": search_term,
        })
    return rows, metadata


def empty_popup_html() -> str:
    return ""


def render_image_snippet_popup(row_metadata: list[dict], evt: gr.SelectData) -> str:
    index = evt.index
    if not isinstance(index, (list, tuple)) or len(index) < 2:
        return empty_popup_html()

    row_index, column_index = index[0], index[1]
    if column_index != 5 or not isinstance(row_index, int):
        return empty_popup_html()

    if row_index < 0 or row_index >= len(row_metadata):
        return empty_popup_html()

    item = row_metadata[row_index]
    if not item.get("is_image"):
        return empty_popup_html()

    snippet_html = highlight_search_terms_html(item.get("snippet_full", ""), item.get("search_term", ""))
    return f"""
<style>
  .gradio-snippet-overlay {{
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--size-8, 32px);
    background: color-mix(in srgb, var(--body-text-color, #0f172a) 38%, transparent);
    backdrop-filter: blur(2px);
  }}
  .gradio-snippet-card {{
    width: min(900px, 92vw);
    max-height: 82vh;
    overflow: hidden;
    border: 1px solid var(--border-color-primary, #e5e7eb);
    border-radius: var(--radius-lg, 12px);
    background: var(--block-background-fill, #ffffff);
    color: var(--body-text-color, #111827);
    box-shadow: var(--shadow-drop-lg, 0 22px 60px rgba(0, 0, 0, 0.28));
  }}
  .gradio-snippet-header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--spacing-lg, 16px);
    padding: var(--block-padding, 16px);
    border-bottom: 1px solid var(--border-color-primary, #e5e7eb);
    background: var(--block-title-background-fill, var(--block-background-fill, #ffffff));
  }}
  .gradio-snippet-title {{
    font-size: var(--text-lg, 18px);
    font-weight: var(--block-title-text-weight, 600);
    line-height: 1.35;
  }}
  .gradio-snippet-subtitle {{
    margin-top: var(--spacing-xs, 4px);
    color: var(--body-text-color-subdued, #6b7280);
    font-size: var(--text-sm, 14px);
  }}
  .gradio-snippet-close {{
    flex: 0 0 auto;
    min-width: 32px;
    height: 32px;
    border: 1px solid var(--button-secondary-border-color, var(--border-color-primary, #e5e7eb));
    border-radius: var(--radius-md, 8px);
    background: var(--button-secondary-background-fill, #f9fafb);
    color: var(--button-secondary-text-color, var(--body-text-color, #111827));
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
  }}
  .gradio-snippet-close:hover {{
    background: var(--button-secondary-background-fill-hover, #f3f4f6);
  }}
  .gradio-snippet-body {{
    max-height: calc(82vh - 88px);
    overflow: auto;
    padding: var(--block-padding, 16px);
    background: var(--input-background-fill, var(--block-background-fill, #ffffff));
    line-height: 1.6;
    white-space: pre-wrap;
    font-size: var(--text-md, 16px);
  }}
  .gradio-snippet-body strong {{
    color: var(--link-text-color, var(--primary-600, #2563eb));
    font-weight: 700;
  }}
</style>
<div data-snippet-popup="true" class="gradio-snippet-overlay" onclick="if (event.target === this) this.remove();">
  <section class="gradio-snippet-card" role="dialog" aria-modal="true" aria-label="Snippet completo de imagen">
    <header class="gradio-snippet-header">
      <div>
        <div class="gradio-snippet-title">{escape(str(item.get('file_name', 'Imagen')))}</div>
        <div class="gradio-snippet-subtitle">{escape(str(item.get('type', 'Imagen')))} | {escape(str(item.get('location', '')))}</div>
      </div>
      <button type="button" class="gradio-snippet-close" aria-label="Cerrar" onclick="this.closest('[data-snippet-popup]').remove();">x</button>
    </header>
    <div class="gradio-snippet-body">{snippet_html or '<em>Sin snippet disponible.</em>'}</div>
  </section>
</div>
"""


def render_grouped_results_table(api_payload: dict, search_term: str = "") -> tuple[list[list[str]], list[dict], str]:
    rows, metadata = build_result_table_data(api_payload, "No se pudo ejecutar la busqueda.", search_term=search_term)
    return rows, metadata, empty_popup_html()


def render_filter_results_table(api_payload: dict, search_term: str = "") -> tuple[list[list[str]], list[dict], str]:
    rows, metadata = build_result_table_data(api_payload, "No se pudo ejecutar el filtro.", search_term=search_term)
    return rows, metadata, empty_popup_html()


def health_info() -> str:
    return pretty_json(api_get("/health", timeout=30))


def registry_health_info() -> str:
    return pretty_json(api_get("/registry/health", timeout=30))


def chroma_health_info() -> str:
    return pretty_json(api_get("/chroma/health", timeout=30))


def monitoring_runtime_info() -> str:
    return pretty_json(api_get("/monitoring/runtime", timeout=30))


def monitoring_status_info() -> str:
    return pretty_json(api_get("/monitoring/status", timeout=30))


def monitoring_metrics_info() -> str:
    return pretty_json(api_get("/monitoring/metrics", timeout=30))


def monitoring_diagnostics_info() -> str:
    return pretty_json(api_get("/monitoring/diagnostics", timeout=30))


def logs_summary_info() -> str:
    return pretty_json(api_get("/logs/summary", timeout=30))


def read_logs(lines: Any) -> str:
    clean_lines = normalize_int(lines, default=200, minimum=1, maximum=5000)
    return pretty_json(api_get("/logs", params={"lines": clean_lines}, timeout=60))


def index_file_ui(file_path: str) -> str:
    clean_path = normalize_text(file_path)
    if not clean_path:
        return pretty_json({"ok": False, "error": "Debe indicar file_path."})
    return pretty_json(api_post("/index-file", payload={"file_path": clean_path}, timeout=300))


def index_folder_ui(folder_path: str, recursive: bool, reindex_existing: bool, limit: Any) -> str:
    clean_path = normalize_text(folder_path)
    if not clean_path:
        return pretty_json({"ok": False, "error": "Debe indicar folder_path."})

    clean_limit = None
    if limit not in (None, ""):
        parsed_limit = normalize_int(limit, default=0, minimum=0, maximum=1000000)
        clean_limit = parsed_limit if parsed_limit > 0 else None

    payload = {
        "folder_path": clean_path,
        "recursive": bool(recursive),
        "reindex_existing": bool(reindex_existing),
        "limit": clean_limit,
    }

    return pretty_json(api_post("/index-folder", payload=payload, timeout=3600))


def search_ui(mode: str, query: str, top_k: Any) -> tuple[list[list[str]], list[dict], str]:
    clean_query = normalize_text(query) or ""
    clean_top_k = normalize_int(top_k, default=20, minimum=1, maximum=200)

    if mode == "Full-text":
        endpoint = "/search/full-text"
        payload = {"query": clean_query, "top_k": clean_top_k}
    elif mode == "Semantic":
        endpoint = "/search/semantic"
        if not clean_query:
            error_payload = {"ok": False, "error": "La busqueda semantica requiere query."}
            return render_grouped_results_table(error_payload, search_term=clean_query)
        payload = {"query": clean_query, "top_k": clean_top_k}
    elif mode == "Hybrid":
        endpoint = "/search/hybrid"
        if not clean_query:
            error_payload = {"ok": False, "error": "La busqueda hibrida requiere query."}
            return render_grouped_results_table(error_payload, search_term=clean_query)
        payload = {"query": clean_query, "top_k": clean_top_k}
    else:
        error_payload = {"ok": False, "error": f"Modo no soportado: {mode}"}
        return render_grouped_results_table(error_payload, search_term=clean_query)

    result = api_post(endpoint, payload=payload, timeout=180)
    return render_grouped_results_table(result, search_term=clean_query)


def files_filter_ui(extension: str, filename: str, path_contains: str, text_contains: str, limit: Any) -> tuple[list[list[str]], list[dict], str]:
    payload = {
        "extension": normalize_text(extension),
        "filename": normalize_text(filename),
        "path_contains": normalize_text(path_contains),
        "text_contains": normalize_text(text_contains),
        "limit": normalize_int(limit, default=100, minimum=1, maximum=5000),
    }
    result = api_post("/files/filter", payload=payload, timeout=180)
    return render_filter_results_table(result, search_term=payload.get("text_contains") or "")


def watcher_status_ui() -> str:
    return pretty_json(api_get("/watcher/status", timeout=30))


def watcher_start_ui(folder_path: str) -> str:
    clean_path = normalize_text(folder_path)
    if not clean_path:
        return pretty_json({"ok": False, "error": "Debe indicar folder_path."})
    return pretty_json(api_post("/watcher/start", payload={"folder_path": clean_path}, timeout=60))


def watcher_stop_ui() -> str:
    return pretty_json(api_post("/watcher/stop", payload={}, timeout=60))


def load_image_preview(image_path: str):
    clean_path = normalize_text(image_path)
    if not clean_path:
        return None, pretty_json({"ok": False, "error": "Debe indicar image_path."})

    path = Path(clean_path)
    if not path.exists():
        return None, pretty_json({"ok": False, "error": "Archivo no existe."})
    if not path.is_file():
        return None, pretty_json({"ok": False, "error": "La ruta no corresponde a archivo."})

    try:
        image = Image.open(path)
        image.thumbnail((768, 768))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        metadata = {
            "ok": True,
            "file_path": str(path),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "image_format": image.format,
            "image_mode": image.mode,
            "image_size": image.size,
        }
        return Image.open(buffer), pretty_json(metadata)
    except Exception as exc:
        return None, pretty_json({"ok": False, "error": str(exc)})


def api_base_info() -> str:
    return pretty_json({"api_base": API_BASE, "env_var": "LOCAL_SEARCH_API_BASE", "default_api_base": DEFAULT_API_BASE})


with gr.Blocks(title="Local Indexed Search Engine") as demo:
    gr.Markdown("# Local Indexed Search Engine")
    gr.Markdown("UI local compatible con backend FastAPI real. Sin Ollama. Sin LLM remoto.")

    with gr.Tab("Estado"):
        gr.Markdown("## Estado backend")
        with gr.Row():
            health_button = gr.Button("Health")
            registry_button = gr.Button("SQLite")
            chroma_button = gr.Button("ChromaDB")
            api_base_button = gr.Button("API Base")
        status_output = gr.Textbox(label="Resultado", lines=28)
        health_button.click(fn=health_info, outputs=status_output)
        registry_button.click(fn=registry_health_info, outputs=status_output)
        chroma_button.click(fn=chroma_health_info, outputs=status_output)
        api_base_button.click(fn=api_base_info, outputs=status_output)

    with gr.Tab("Indexacion"):
        gr.Markdown("## Indexar archivo individual")
        index_file_path = gr.Textbox(label="file_path", placeholder=r"E:\ruta\archivo.pdf")
        index_button = gr.Button("Indexar archivo")
        index_output = gr.Textbox(label="Resultado indexacion archivo", lines=18)
        index_button.click(fn=index_file_ui, inputs=index_file_path, outputs=index_output)

        gr.Markdown("## Indexar carpeta")
        index_folder_path = gr.Textbox(label="folder_path", placeholder=r"E:\ruta\carpeta")
        index_folder_recursive = gr.Checkbox(label="recursive", value=True)
        index_folder_reindex_existing = gr.Checkbox(label="reindex_existing", value=False)
        index_folder_limit = gr.Number(label="limit opcional", value=0, precision=0)
        index_folder_button = gr.Button("Indexar carpeta")
        index_folder_output = gr.Textbox(label="Resultado indexacion carpeta", lines=24)
        index_folder_button.click(
            fn=index_folder_ui,
            inputs=[
                index_folder_path,
                index_folder_recursive,
                index_folder_reindex_existing,
                index_folder_limit,
            ],
            outputs=index_folder_output,
        )

    with gr.Tab("Busqueda"):
        gr.Markdown("## Busqueda full-text, semantica e hibrida")
        search_mode = gr.Radio(choices=["Full-text", "Semantic", "Hybrid"], value="Hybrid", label="Modo busqueda")
        search_query = gr.Textbox(label="query", lines=3)
        search_top_k = gr.Number(label="top_k", value=20, precision=0)
        search_button = gr.Button("Buscar")
        search_grouped_output = gr.Dataframe(
            headers=["Nombre", "Tipo", "Ubicacion", "Ranking", "Score", "Snippet"],
            datatype=["str", "str", "str", "str", "str", "markdown"],
            label="Resultados",
            interactive=False,
            wrap=True,
        )
        search_row_metadata = gr.State([])
        search_snippet_popup = gr.HTML(value="")
        search_button.click(
            fn=search_ui,
            inputs=[search_mode, search_query, search_top_k],
            outputs=[search_grouped_output, search_row_metadata, search_snippet_popup],
        )
        search_grouped_output.select(
            fn=render_image_snippet_popup,
            inputs=search_row_metadata,
            outputs=search_snippet_popup,
            show_progress="hidden",
        )

    with gr.Tab("Filtros"):
        gr.Markdown("## Filtros estructurados")
        filter_extension = gr.Textbox(label="extension", placeholder=".pdf")
        filter_filename = gr.Textbox(label="filename", placeholder="nombre parcial")
        filter_path_contains = gr.Textbox(label="path_contains", placeholder="fragmento de ruta")
        filter_text_contains = gr.Textbox(label="text_contains", placeholder="texto contenido")
        filter_limit = gr.Number(label="limit", value=100, precision=0)
        filter_button = gr.Button("Filtrar")
        filter_grouped_output = gr.Dataframe(
            headers=["Nombre", "Tipo", "Ubicacion", "Ranking", "Score", "Snippet"],
            datatype=["str", "str", "str", "str", "str", "markdown"],
            label="Archivos filtrados",
            interactive=False,
            wrap=True,
        )
        filter_row_metadata = gr.State([])
        filter_snippet_popup = gr.HTML(value="")
        filter_button.click(
            fn=files_filter_ui,
            inputs=[filter_extension, filter_filename, filter_path_contains, filter_text_contains, filter_limit],
            outputs=[filter_grouped_output, filter_row_metadata, filter_snippet_popup],
        )
        filter_grouped_output.select(
            fn=render_image_snippet_popup,
            inputs=filter_row_metadata,
            outputs=filter_snippet_popup,
            show_progress="hidden",
        )

    with gr.Tab("Watcher"):
        gr.Markdown("## Watcher filesystem")
        watcher_folder = gr.Textbox(label="folder_path", placeholder=r"E:\carpeta\a\monitorear")
        with gr.Row():
            watcher_status_button = gr.Button("Estado watcher")
            watcher_start_button = gr.Button("Iniciar watcher")
            watcher_stop_button = gr.Button("Detener watcher")
        watcher_output = gr.Textbox(label="Resultado watcher", lines=28)
        watcher_status_button.click(fn=watcher_status_ui, outputs=watcher_output)
        watcher_start_button.click(fn=watcher_start_ui, inputs=watcher_folder, outputs=watcher_output)
        watcher_stop_button.click(fn=watcher_stop_ui, outputs=watcher_output)

    with gr.Tab("Logs"):
        gr.Markdown("## Logs backend")
        log_lines = gr.Number(label="lineas", value=200, precision=0)
        with gr.Row():
            logs_button = gr.Button("Leer logs")
            logs_summary_button = gr.Button("Resumen logs")
        logs_output = gr.Textbox(label="Logs", lines=36)
        logs_button.click(fn=read_logs, inputs=log_lines, outputs=logs_output)
        logs_summary_button.click(fn=logs_summary_info, outputs=logs_output)

    with gr.Tab("Monitoreo"):
        gr.Markdown("## Monitoreo operacional")
        with gr.Row():
            runtime_button = gr.Button("Runtime")
            monitoring_status_button = gr.Button("Status")
            metrics_button = gr.Button("Metrics")
            diagnostics_button = gr.Button("Diagnostics")
        monitoring_output = gr.Textbox(label="Monitoreo", lines=36)
        runtime_button.click(fn=monitoring_runtime_info, outputs=monitoring_output)
        monitoring_status_button.click(fn=monitoring_status_info, outputs=monitoring_output)
        metrics_button.click(fn=monitoring_metrics_info, outputs=monitoring_output)
        diagnostics_button.click(fn=monitoring_diagnostics_info, outputs=monitoring_output)

    with gr.Tab("Preview imagen"):
        gr.Markdown("## Preview local de imagen")
        image_path = gr.Textbox(label="image_path", placeholder=r"E:\ruta\imagen.png")
        image_button = gr.Button("Cargar preview")
        image_preview = gr.Image(label="Preview", type="pil")
        image_metadata = gr.Textbox(label="Metadata preview", lines=16)
        image_button.click(fn=load_image_preview, inputs=image_path, outputs=[image_preview, image_metadata])
