from pathlib import Path
from pypdf import PdfReader


def extract_pdf(path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    pages: list[dict] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(
                {
                    "page": index,
                    "text": text,
                }
            )

    return pages
