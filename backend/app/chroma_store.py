"""
Persistencia ChromaDB.

Esta fase incorpora:
- insercion embeddings;
- busqueda semantica;
- ranking por distancia.
"""

from pathlib import Path

import chromadb

from .embedding_client import create_embedding


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"

CHROMA_DIR = DATA_DIR / "chroma"

CHROMA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

COLLECTION_NAME = "local_documents_st_e5_small"

client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
)


def chroma_health() -> dict:
    """
    Estado ChromaDB.
    """

    return {
        "status": "ok",
        "persist_directory": str(CHROMA_DIR),
        "collection_name": COLLECTION_NAME,
    }


def add_chunk(
    chunk_id: str,
    text: str,
    file_path: str,
    file_name: str,
    extension: str,
    chunk_index: int,
) -> dict:
    """
    Inserta chunk vectorial.
    """

    embedding = create_embedding(
        text=text,
        is_query=False,
    )

    collection.upsert(
        ids=[chunk_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[
            {
                "file_path": file_path,
                "file_name": file_name,
                "extension": extension,
                "chunk_index": chunk_index,
            }
        ],
    )

    return {
        "chunk_id": chunk_id,
        "embedding_dimensions": len(embedding),
    }


def search_semantic(
    query: str,
    top_k: int = 20,
) -> list[dict]:
    """
    Ejecuta busqueda semantica.
    """

    embedding = create_embedding(
        text=query,
        is_query=True,
    )

    result = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = result["documents"][0]

    metadatas = result["metadatas"][0]

    distances = result["distances"][0]

    output = []

    for index in range(len(documents)):

        metadata = metadatas[index]

        output.append(
            {
                "rank": index + 1,
                "text": documents[index],
                "distance": distances[index],
                "file_path": metadata["file_path"],
                "file_name": metadata["file_name"],
                "extension": metadata["extension"],
                "chunk_index": metadata["chunk_index"],
            }
        )

    return output


def delete_chunks_by_file_path(file_path: str) -> dict:
    """Elimina chunks vectoriales asociados a un archivo."""

    try:
        collection.delete(where={"file_path": file_path})
        return {"status": "ok", "file_path": file_path}
    except Exception as exc:
        return {"status": "error", "file_path": file_path, "error": str(exc)}

def chroma_metrics() -> dict:
    """Retorna metricas basicas de ChromaDB."""

    try:
        return {
            "status": "ok",
            "persist_directory": str(CHROMA_DIR),
            "collection_name": COLLECTION_NAME,
            "collection_count": collection.count(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "persist_directory": str(CHROMA_DIR),
            "collection_name": COLLECTION_NAME,
            "error": str(exc),
        }
