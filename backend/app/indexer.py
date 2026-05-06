from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from .chunker import chunk_text
from .config import SUPPORTED_EXTENSIONS
from .extractors.office_extractor import extract_docx
from .extractors.pdf_extractor import extract_pdf
from .extractors.text_extractor import extract_text_file
from .file_registry import compute_file_hash, get_registered_hash, upsert_file_status
from .vectorstore import add_chunks


def iter_files(root: Path, recursive: bool = True) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return [
        p
        for p in root.glob(pattern)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def extract_file(path: Path) -> list[dict]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_pdf(path)

    if ext == ".docx":
        return [{"page": None, "text": extract_docx(path)}]

    if ext in {".txt", ".md", ".csv"}:
        return [{"page": None, "text": extract_text_file(path)}]

    return []


def index_file(path: Path) -> dict:
    file_hash = compute_file_hash(path)
    previous_hash = get_registered_hash(path)

    if previous_hash == file_hash:
        return {
            "file": str(path),
            "status": "skipped",
            "reason": "hash unchanged",
            "chunks": 0,
        }

    try:
        extracted_units = extract_file(path)
        chunks_to_store: list[dict] = []

        for unit_index, unit in enumerate(extracted_units):
            page = unit.get("page")
            text = unit.get("text", "")
            chunks = chunk_text(text)

            for chunk_index, chunk in enumerate(chunks):
                raw_id = f"{path}|{file_hash}|{unit_index}|{chunk_index}"
                chunk_id = str(uuid5(NAMESPACE_URL, raw_id))

                chunks_to_store.append(
                    {
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": {
                            "file_path": str(path),
                            "file_name": path.name,
                            "extension": path.suffix.lower(),
                            "page": page if page is not None else "",
                            "chunk_index": chunk_index,
                            "file_hash": file_hash,
                        },
                    }
                )

        stored_count = add_chunks(chunks_to_store)
        upsert_file_status(path, file_hash, "indexed", None)

        return {
            "file": str(path),
            "status": "indexed",
            "chunks": stored_count,
        }

    except Exception as exc:
        upsert_file_status(path, file_hash, "error", str(exc))
        return {
            "file": str(path),
            "status": "error",
            "error": str(exc),
            "chunks": 0,
        }


def index_folder(path: str, recursive: bool = True) -> dict:
    root = Path(path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root}")

    files = iter_files(root, recursive)
    results = [index_file(file) for file in files]

    return {
        "folder": str(root),
        "recursive": recursive,
        "total_supported_files": len(files),
        "indexed": sum(1 for item in results if item["status"] == "indexed"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "errors": sum(1 for item in results if item["status"] == "error"),
        "results": results,
    }
