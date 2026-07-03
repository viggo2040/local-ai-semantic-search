"""
Extraccion metadata imagenes usando ExifTool.
"""

from pathlib import Path
import json
import subprocess


EXIFTOOL_PATH = r"C:\exiftool\exiftool.exe"


def extract_image_metadata(path: Path) -> list[dict]:
    """
    Extrae metadata PNG y AVIF usando ExifTool.
    """

    command = [
        EXIFTOOL_PATH,
        "-j",
        str(path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    data = json.loads(result.stdout)

    if not data:
        return []

    metadata = data[0]

    text = json.dumps(
        metadata,
        ensure_ascii=False,
        indent=2,
    )

    return [
        {
            "page": "metadata",
            "text": text,
        }
    ]