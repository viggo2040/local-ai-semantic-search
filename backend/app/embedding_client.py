"""
Cliente local de embeddings.

Esta implementacion usa SentenceTransformers localmente y elimina
completamente la dependencia de Ollama.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Carga modelo local una sola vez.
    """

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def create_embedding(
    text: str,
    is_query: bool = False,
) -> list[float]:
    """
    Genera embedding local.

    E5 recomienda prefijos distintos para query y documentos.
    """

    if not text:
        raise ValueError("Empty text")

    prefix = "query: " if is_query else "passage: "

    model = get_embedding_model()

    embedding = model.encode(
        prefix + text,
        normalize_embeddings=True,
    )

    return embedding.tolist()