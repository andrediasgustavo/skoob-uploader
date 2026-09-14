import asyncio
import csv

from skoob_uploader.application import process_batch
from skoob_uploader.models import Book, ProcessResult


class FakeUploader:
    def __init__(self):
        self.processed = []
        self.home_open_count = 0

    async def process(self, book):
        self.processed.append(book.title)
        return ProcessResult(title=book.title, status="atualizado")

    async def open_home(self):
        self.home_open_count += 1


def test_process_batch_processes_books_reopens_home_and_writes_report(tmp_path):
    uploader = FakeUploader()
    books = [
        Book(title="Duna", author="", format="", source="Duna"),
        Book(title="Akira", author="", format="", source="Akira"),
    ]
    report_path = tmp_path / "reports" / "results.csv"

    results = asyncio.run(process_batch(uploader, books, report_path, delay_seconds=0))

    assert [result.title for result in results] == ["Duna", "Akira"]
    assert uploader.processed == ["Duna", "Akira"]
    assert uploader.home_open_count == 2
    with report_path.open(newline="", encoding="utf-8") as report_file:
        assert [row["title"] for row in csv.DictReader(report_file)] == ["Duna", "Akira"]
