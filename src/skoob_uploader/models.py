from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    format: str
    source: str


@dataclass(frozen=True)
class ProcessResult:
    title: str
    status: str
    url: str = ""
    found_title: str = ""
    reason: str = ""
