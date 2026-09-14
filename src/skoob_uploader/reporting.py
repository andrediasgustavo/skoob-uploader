import csv
from collections.abc import Iterable
from pathlib import Path

from .models import ProcessResult

REPORT_FIELDS = (
    "title",
    "status",
    "url",
    "found_title",
    "reason",
    "desired_status",
    "current_status",
    "ignored_status_tag",
)


def write_report(path: Path, results: Iterable[ProcessResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(result.__dict__ for result in results)
