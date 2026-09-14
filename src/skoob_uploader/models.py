from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    format: str
    source: str
    desired_status: str = "lido"
    ignored_status_tag: str = ""


@dataclass(frozen=True)
class ProcessResult:
    title: str
    status: str
    url: str = ""
    found_title: str = ""
    reason: str = ""
    desired_status: str = "lido"
    current_status: str = ""
    ignored_status_tag: str = ""
