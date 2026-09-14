import re
import unicodedata

DEFAULT_STATUS = "lido"
STATUS_LABELS = {
    "lido": "Lido",
    "lendo": "Lendo",
    "quero ler": "Quero ler",
    "relendo": "Relendo",
    "abandonei": "Abandonei",
}


def resolve_status_tag(tag: str) -> tuple[str, str]:
    normalized = normalize_status_text(tag)
    if normalized in STATUS_LABELS:
        return normalized, ""
    return DEFAULT_STATUS, tag


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, STATUS_LABELS[DEFAULT_STATUS])


def normalize_status_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()
