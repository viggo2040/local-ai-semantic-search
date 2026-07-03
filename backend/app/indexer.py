"""
Indexer principal.

Fase 5:
- SQLite
- chunking
- ChromaDB
- embeddings locales
"""

from pathlib import Path
from uuid import uuid4
from datetime import datetime

from .chroma_store import add_chunk, delete_chunks_by_file_path
from .chunker import chunk_text
from .document_extractor import (
    extract_docx,
    extract_pdf,
    extract_pptx,
    extract_xlsx,
)
from .file_registry import delete_file_records, file_exists_in_registry, get_connection
from .image_metadata_extractor import extract_image_metadata
from .text_extractor import extract_txt


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".png",
    ".avif",
}


def extract_file(path: Path) -> list[dict]:
    """
    Extrae contenido segun extension.
    """

    extension = path.suffix.lower()

    if extension == ".txt":

        text = extract_txt(path)

        return [
            {
                "page": "",
                "text": text,
            }
        ]

    if extension == ".pdf":
        return extract_pdf(path)

    if extension == ".docx":
        return extract_docx(path)

    if extension == ".xlsx":
        return extract_xlsx(path)

    if extension == ".pptx":
        return extract_pptx(path)

    if extension in {".png", ".avif"}:
        return extract_image_metadata(path)

    raise ValueError(f"Unsupported extension: {extension}")


def index_file(file_path: str, cleanup_existing: bool = False) -> dict:
    """
    Indexa archivo en SQLite y ChromaDB.
    """

    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(path)

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(extension)

    if cleanup_existing:
        delete_file_records(str(path))
        delete_chunks_by_file_path(str(path))

    extracted_units = extract_file(path)

    inserted_chunks = 0

    with get_connection() as conn:

        conn.execute(
            """
            INSERT OR REPLACE INTO files (
                file_path,
                file_name,
                extension,
                indexed_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                str(path),
                path.name,
                extension,
                datetime.utcnow().isoformat(),
            ),
        )

        for unit in extracted_units:

            chunks = chunk_text(unit["text"])

            for chunk_index, chunk in enumerate(chunks):

                chunk_id = str(uuid4())

                conn.execute(
                    """
                    INSERT INTO indexed_chunks (
                        chunk_id,
                        file_path,
                        file_name,
                        extension,
                        chunk_index,
                        text
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        str(path),
                        path.name,
                        extension,
                        chunk_index,
                        chunk,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO indexed_chunks_fts (
                        chunk_id,
                        file_path,
                        file_name,
                        extension,
                        text
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        str(path),
                        path.name,
                        extension,
                        chunk,
                    ),
                )

                add_chunk(
                    chunk_id=chunk_id,
                    text=chunk,
                    file_path=str(path),
                    file_name=path.name,
                    extension=extension,
                    chunk_index=chunk_index,
                )

                inserted_chunks += 1

        conn.commit()

    return {
        "status": "indexed",
        "file_path": str(path),
        "chunks": inserted_chunks,
    }


def iter_supported_files(folder_path: str, recursive: bool = True) -> list[Path]:
    """Lista archivos soportados dentro de una carpeta."""

    folder = Path(folder_path).resolve()

    if not folder.exists():
        raise FileNotFoundError(folder)

    if not folder.is_dir():
        raise NotADirectoryError(folder)

    pattern = "**/*" if recursive else "*"

    files = []

    for path in folder.glob(pattern):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files.append(path.resolve())

    return sorted(files, key=lambda item: str(item).lower())


def index_folder(
    folder_path: str,
    recursive: bool = True,
    reindex_existing: bool = False,
    limit: int | None = None,
) -> dict:
    """Indexa archivos soportados dentro de una carpeta."""

    folder = Path(folder_path).resolve()
    files = iter_supported_files(str(folder), recursive=recursive)

    if limit is not None and limit > 0:
        files = files[:limit]

    indexed = []
    skipped = []
    errors = []

    for path in files:
        path_text = str(path)

        try:
            already_indexed = file_exists_in_registry(path_text)

            if already_indexed and not reindex_existing:
                skipped.append(
                    {
                        "file_path": path_text,
                        "reason": "already_indexed",
                    }
                )
                continue

            result = index_file(
                path_text,
                cleanup_existing=reindex_existing,
            )
            indexed.append(result)

        except Exception as exc:
            errors.append(
                {
                    "file_path": path_text,
                    "error": str(exc),
                }
            )

    return {
        "status": "ok",
        "mode": "index-folder",
        "folder_path": str(folder),
        "recursive": recursive,
        "reindex_existing": reindex_existing,
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "files_found": len(files),
        "indexed_count": len(indexed),
        "skipped_count": len(skipped),
        "errors_count": len(errors),
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
    }
