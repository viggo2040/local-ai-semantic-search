"""
Extraccion texto plano.
"""

from pathlib import Path


def extract_txt(path: Path) -> str:
    """
    Extrae contenido TXT.
    """

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    )