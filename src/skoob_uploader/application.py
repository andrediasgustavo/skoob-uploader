import asyncio
from collections.abc import Sequence
from pathlib import Path

from .models import Book, ProcessResult
from .reporting import write_report
from .skoob import SkoobUploader


async def process_batch(
    uploader: SkoobUploader,
    books: Sequence[Book],
    report_path: Path,
    delay_seconds: float = 0.8,
) -> list[ProcessResult]:
    results: list[ProcessResult] = []
    for index, book in enumerate(books, start=1):
        result = await uploader.process(book)
        results.append(result)
        print(f"[{index}/{len(books)}] {book.title}: {result.status}")
        await asyncio.sleep(delay_seconds)
        await uploader.open_home()
    write_report(report_path, results)
    return results
