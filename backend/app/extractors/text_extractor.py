from pathlib import Path


def extract_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")
