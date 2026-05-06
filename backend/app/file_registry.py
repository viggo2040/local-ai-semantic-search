import hashlib
import sqlite3
from pathlib import Path
from time import time

from .config import REGISTRY_DB


def init_registry() -> None:
    with sqlite3.connect(REGISTRY_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at REAL NOT NULL,
                indexed_at REAL NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        conn.commit()


def compute_file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def get_registered_hash(path: Path) -> str | None:
    init_registry()
    with sqlite3.connect(REGISTRY_DB) as conn:
        row = conn.execute(
            "SELECT file_hash FROM files WHERE file_path = ?",
            (str(path),),
        ).fetchone()
    return row[0] if row else None


def upsert_file_status(
    path: Path,
    file_hash: str,
    status: str,
    error_message: str | None = None,
) -> None:
    init_registry()
    stat = path.stat()
    with sqlite3.connect(REGISTRY_DB) as conn:
        conn.execute(
            """
            INSERT INTO files (
                file_path,
                file_hash,
                size_bytes,
                modified_at,
                indexed_at,
                status,
                error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at,
                indexed_at = excluded.indexed_at,
                status = excluded.status,
                error_message = excluded.error_message
            """,
            (
                str(path),
                file_hash,
                stat.st_size,
                stat.st_mtime,
                time(),
                status,
                error_message,
            ),
        )
        conn.commit()
