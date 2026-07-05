"""
Registro persistente SQLite con FTS5.

Administra archivos, chunks, indice full-text y filtros estructurados.
"""

from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_DB = DATA_DIR / "registry.sqlite"


def get_connection() -> sqlite3.Connection:
    """Crea una conexion SQLite con filas accesibles por nombre."""

    conn = sqlite3.connect(REGISTRY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_registry() -> None:
    """Inicializa tablas SQLite y el indice FTS5."""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_path TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS indexed_chunks (
                chunk_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS indexed_chunks_fts
            USING fts5(
                chunk_id UNINDEXED,
                file_path UNINDEXED,
                file_name UNINDEXED,
                extension UNINDEXED,
                text
            )
        """)

        conn.commit()


def registry_health() -> dict:
    """Retorna informacion basica del registro SQLite."""

    init_registry()

    with get_connection() as conn:
        files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        chunks_count = conn.execute("SELECT COUNT(*) FROM indexed_chunks").fetchone()[0]

    return {
        "status": "ok",
        "database": str(REGISTRY_DB),
        "files_count": files_count,
        "chunks_count": chunks_count,
    }


def search_full_text_like(
    query: str = "",
    filename: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """Fallback LIKE para terminos no compatibles con MATCH."""

    clean_query = (query or "").strip()
    clean_filename = (filename or "").strip()

    sql = """
        SELECT
            chunk_id,
            file_path,
            file_name,
            extension,
            chunk_index,
            text,
            0.0 AS score
        FROM indexed_chunks
        WHERE 1 = 1
    """

    params: list[object] = []

    if clean_query:
        sql += " AND text LIKE ?"
        params.append(f"%{clean_query}%")

    if clean_filename:
        sql += " AND file_name LIKE ?"
        params.append(f"%{clean_filename}%")

    sql += " LIMIT ?"
    params.append(top_k)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def search_full_text(
    query: str = "",
    filename: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """Busca contenido usando SQLite FTS5 y filtro opcional por filename."""

    init_registry()

    clean_query = (query or "").strip()
    clean_filename = (filename or "").strip()

    with get_connection() as conn:
        if clean_query:
            sql = """
                SELECT
                    c.chunk_id,
                    c.file_path,
                    c.file_name,
                    c.extension,
                    c.chunk_index,
                    c.text,
                    bm25(indexed_chunks_fts) AS score
                FROM indexed_chunks_fts
                JOIN indexed_chunks c
                    ON indexed_chunks_fts.chunk_id = c.chunk_id
                WHERE indexed_chunks_fts MATCH ?
            """

            params: list[object] = [clean_query]

            if clean_filename:
                sql += " AND c.file_name LIKE ?"
                params.append(f"%{clean_filename}%")

            sql += " ORDER BY score LIMIT ?"
            params.append(top_k)

            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return search_full_text_like(clean_query, clean_filename, top_k)

        else:
            sql = """
                SELECT
                    chunk_id,
                    file_path,
                    file_name,
                    extension,
                    chunk_index,
                    text,
                    0.0 AS score
                FROM indexed_chunks
                WHERE 1 = 1
            """

            params = []

            if clean_filename:
                sql += " AND file_name LIKE ?"
                params.append(f"%{clean_filename}%")

            sql += " LIMIT ?"
            params.append(top_k)

            rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def filter_files(
    extension: str | None = None,
    filename: str | None = None,
    path_contains: str | None = None,
    text_contains: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Filtra archivos por extension, nombre, ruta o contenido indexado."""

    init_registry()

    sql = """
        SELECT
            f.file_path,
            f.file_name,
            f.extension,
            f.indexed_at,
            COUNT(c.chunk_id) AS chunks_count
        FROM files f
        LEFT JOIN indexed_chunks c
            ON f.file_path = c.file_path
        WHERE 1 = 1
    """

    params: list[object] = []

    if extension:
        sql += " AND f.extension = ?"
        params.append(extension)

    if filename:
        sql += " AND f.file_name LIKE ?"
        params.append(f"%{filename}%")

    if path_contains:
        sql += " AND f.file_path LIKE ?"
        params.append(f"%{path_contains}%")

    if text_contains:
        sql += """
            AND EXISTS (
                SELECT 1
                FROM indexed_chunks c2
                WHERE c2.file_path = f.file_path
                AND c2.text LIKE ?
            )
        """
        params.append(f"%{text_contains}%")

    sql += """
        GROUP BY
            f.file_path,
            f.file_name,
            f.extension,
            f.indexed_at
        ORDER BY f.indexed_at DESC
        LIMIT ?
    """
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def get_chunks_by_file_path(file_path: str) -> list[dict]:
    """Retorna chunks de un archivo ordenados por indice."""

    init_registry()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                chunk_index,
                text
            FROM indexed_chunks
            WHERE file_path = ?
            ORDER BY chunk_index
            """,
            (file_path,),
        ).fetchall()

    return [dict(row) for row in rows]



def file_exists_in_registry(file_path: str) -> bool:
    """Verifica si un archivo ya existe en el registro SQLite."""

    init_registry()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM files WHERE file_path = ? LIMIT 1",
            (file_path,),
        ).fetchone()

    return row is not None


def delete_file_records(file_path: str) -> dict:
    """Elimina registros SQLite asociados a un archivo."""

    init_registry()

    with get_connection() as conn:
        chunk_rows = conn.execute(
            "SELECT chunk_id FROM indexed_chunks WHERE file_path = ?",
            (file_path,),
        ).fetchall()

        chunk_ids = [row["chunk_id"] for row in chunk_rows]

        for chunk_id in chunk_ids:
            conn.execute(
                "DELETE FROM indexed_chunks_fts WHERE chunk_id = ?",
                (chunk_id,),
            )

        conn.execute(
            "DELETE FROM indexed_chunks WHERE file_path = ?",
            (file_path,),
        )

        conn.execute(
            "DELETE FROM files WHERE file_path = ?",
            (file_path,),
        )

        conn.commit()

    return {
        "status": "deleted",
        "file_path": file_path,
        "deleted_chunks": len(chunk_ids),
    }

def registry_metrics() -> dict:
    """Retorna metricas basicas del registro SQLite."""

    init_registry()

    with get_connection() as conn:
        files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        chunks_count = conn.execute("SELECT COUNT(*) FROM indexed_chunks").fetchone()[0]
        extensions_rows = conn.execute(
            """
            SELECT extension, COUNT(*) AS count
            FROM files
            GROUP BY extension
            ORDER BY extension
            """
        ).fetchall()

    return {
        "status": "ok",
        "database": str(REGISTRY_DB),
        "files_count": files_count,
        "chunks_count": chunks_count,
        "extensions": [dict(row) for row in extensions_rows],
    }
