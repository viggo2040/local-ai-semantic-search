"""
Motor simple de chunking.

Divide texto largo en bloques superpuestos para permitir indexacion y
busqueda contextual posterior.
"""

from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> List[str]:
    """
    Divide texto en chunks superpuestos.

    Parametros:
    - text: texto origen
    - chunk_size: tamano maximo chunk
    - overlap: superposicion entre chunks
    """

    if not text:
        return []

    clean = text.strip()

    if not clean:
        return []

    chunks = []

    start = 0

    while start < len(clean):

        end = start + chunk_size

        chunk = clean[start:end]

        chunk = chunk.strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks