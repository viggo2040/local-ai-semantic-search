import requests

from .config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL


def embed_text(text: str) -> list[float]:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={
            "model": OLLAMA_EMBED_MODEL,
            "prompt": text,
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    embedding = payload.get("embedding")
    if not embedding:
        raise RuntimeError("Ollama did not return an embedding.")
    return embedding
