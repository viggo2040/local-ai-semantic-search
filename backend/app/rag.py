import requests

from .config import OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL
from .vectorstore import search


def ask(question: str, top_k: int = 5) -> dict:
    retrieved = search(question, top_k)

    context_blocks = []
    for index, item in enumerate(retrieved, start=1):
        metadata = item["metadata"]
        context_blocks.append(
            f"[Source {index}]\n"
            f"File: {metadata.get('file_path')}\n"
            f"Page: {metadata.get('page')}\n"
            f"Text: {item['text']}"
        )

    context = "\n\n".join(context_blocks)

    prompt = f"""You are a local document assistant.

Answer only using the context below.
If the context is insufficient, say that there is not enough evidence in the indexed documents.
Include the source file paths used.

Context:
{context}

Question:
{question}
"""

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=240,
    )
    response.raise_for_status()

    payload = response.json()
    return {
        "answer": payload.get("response", ""),
        "sources": retrieved,
    }
