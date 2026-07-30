from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class crawljob:
    id: str
    root_url: str
    status: str
    max_pages: int
    max_depth: int
    pages_queued: int = 0
    pages_crawled: int = 0
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    error: Optional[str] = None

    def is_finished(self):
        return self.status in ("done", "failed")

    def percent_complete(self):
        if self.max_pages == 0:
            return 0
        raw = (self.pages_crawled / self.max_pages) * 100
        return min(100, round(raw, 1))


@dataclass
class PageRecord:
    job_id: str
    url: str
    depth: int
    status_code: Optional[int]
    crawled_at: float = field(default_factory=time.time)


@dataclass
class LinkResult:
    job_id: str
    source_page: str
    target_url: str
    is_internal: bool
    status_code: Optional[int]
    status: str
    redirect_chain: list
    error_message: Optional[str]
    checked_at: float = field(default_factory=time.time)

    def is_ok(self):
        return self.status == "ok"


@dataclass
class QueueItem:
    url: str
    depth: int
