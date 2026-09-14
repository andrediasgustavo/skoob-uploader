import csv

from skoob_uploader.models import ProcessResult
from skoob_uploader.reporting import REPORT_FIELDS, write_report


def test_write_report_creates_parent_and_writes_all_result_fields(tmp_path):
    path = tmp_path / "reports" / "results.csv"
    result = ProcessResult(
        title="Duna",
        status="atualizado",
        url="https://example.test/book/1",
        found_title="Duna",
        desired_status="lendo",
        current_status="Adicionar",
        ignored_status_tag="",
    )

    write_report(path, [result])

    with path.open(newline="", encoding="utf-8") as report_file:
        rows = list(csv.DictReader(report_file))

    assert tuple(rows[0]) == REPORT_FIELDS
    assert rows[0]["title"] == "Duna"
    assert rows[0]["desired_status"] == "lendo"
    assert rows[0]["current_status"] == "Adicionar"
