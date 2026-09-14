import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import Book

MONTHS = {
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
}
FORMAT_RE = re.compile(r"^(livro|quadrinho)$", re.IGNORECASE)
VOLUME_RE = re.compile(r"\bvol(?:ume)?\.?\s*(\d+)\b", re.IGNORECASE)
STATUS_TAG_RE = re.compile(r"\[([^\]]+)\]\s*$")
STATUS_LABELS = {
    "lido": "Lido",
    "lendo": "Lendo",
    "quero ler": "Quero ler",
    "relendo": "Relendo",
    "abandonei": "Abandonei",
}


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()


def normalize_volume_labels(value: str) -> str:
    return VOLUME_RE.sub(r"#\1", value)


def _status_from_source(source: str) -> tuple[str, str, str]:
    match = STATUS_TAG_RE.search(source)
    if not match:
        return source, "lido", ""
    tag = re.sub(r"\s+", " ", match.group(1)).strip()
    normalized_tag = normalize_text(tag)
    clean_source = re.sub(r"\s+-\s*$", "", source[: match.start()]).rstrip()
    return clean_source, normalized_tag if normalized_tag in STATUS_LABELS else "lido", "" if normalized_tag in STATUS_LABELS else tag


def extract_pdf_text(pdf_path: Path) -> str:
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


def _is_header(line: str) -> bool:
    value = line.strip()
    return bool(re.fullmatch(r"20\d{2}", value)) or normalize_text(value) in MONTHS


def _join_entries(text: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    text_with_entry_breaks = re.sub(r"\s*([●•])\s*", r"\n\1 ", text)
    for raw_line in text_with_entry_breaks.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or _is_header(line):
            continue
        if line.startswith(("●", "•", "*")):
            if current:
                entries.append(" ".join(current))
            current = [line[1:].strip()]
        elif current:
            current.append(line)
    if current:
        entries.append(" ".join(current))
    return entries


def parse_text(text: str) -> list[Book]:
    books: list[Book] = []
    entries = _join_entries(text)
    if not entries:
        entries = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        books = []
        for source in entries:
            clean_source, desired_status, ignored_status_tag = _status_from_source(source)
            books.append(
                Book(
                    title=normalize_volume_labels(clean_source),
                    author="",
                    format="",
                    source=source,
                    desired_status=desired_status,
                    ignored_status_tag=ignored_status_tag,
                )
            )
        return books

    for source in entries:
        clean_source, desired_status, ignored_status_tag = _status_from_source(source)
        parts = [part.strip() for part in re.split(r"\s+-\s+", clean_source) if part.strip()]
        format_index = next(
            (index for index, part in enumerate(parts) if FORMAT_RE.fullmatch(part)),
            None,
        )
        if format_index is None or format_index < 2:
            continue
        title = normalize_volume_labels(" - ".join(parts[: format_index - 1]))
        author = parts[format_index - 1]
        books.append(
            Book(
                title=title,
                author=author,
                format=parts[format_index],
                source=source,
                desired_status=desired_status,
                ignored_status_tag=ignored_status_tag,
            )
        )
    return books


def parse_pdf(pdf_path: Path) -> list[Book]:
    return parse_text(extract_pdf_text(pdf_path))


def validate_pdf(pdf_path: Path) -> list[Book]:
    if not pdf_path.is_file():
        raise ValueError(f"PDF não encontrado: {pdf_path}")
    try:
        text = extract_pdf_text(pdf_path)
    except Exception as error:
        raise ValueError(f"Não foi possível ler o PDF: {error}") from error
    if not text.strip():
        raise ValueError(
            "O PDF não contém texto extraível. PDFs escaneados como imagem precisam passar por OCR."
        )
    books = parse_text(text)
    if not books:
        raise ValueError(
            "Nenhum livro foi reconhecido. Use uma entrada por linha ou o formato "
            "'● Título - Autor - livro'/'quadrinho'."
        )
    return books
