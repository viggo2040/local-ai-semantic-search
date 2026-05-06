from pathlib import Path

import chromadb

from .config import CHROMA_DIR, COLLECTION_NAME
from .embeddings import embed_text

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_collection = _client.get_or_create_collection(name=COLLECTION_NAME)


def add_chunks(chunks: list[dict]) -> int:
    if not chunks:
        return 0

    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    embeddings = [embed_text(text) for text in documents]

    _collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def search(query: str, top_k: int = 5) -> list[dict]:
    query_embedding = embed_text(query)
    result = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    output: list[dict] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        output.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return output
