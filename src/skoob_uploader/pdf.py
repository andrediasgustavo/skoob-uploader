import re
from pathlib import Path

from pypdf import PdfReader


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        rows: dict[float, list[str]] = {}

        def collect_row(text: str, cm: list[float], _tm: list[float], _font: object, _size: float) -> None:
            if text.strip():
                rows.setdefault(round(cm[5], 1), []).append(text)

        page.extract_text(visitor_text=collect_row)
        pages.append("\n".join(re.sub(r"\s+", " ", " ".join(parts)).strip() for parts in rows.values()))
    return "\n".join(pages)
