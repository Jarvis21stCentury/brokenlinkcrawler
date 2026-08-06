from dataclasses import dataclass, field
import time


@dataclass
class CrawlJob:
    id: str
    root_url: str
    status: str
    max_pages: int
    max_depth: int
    pages_queued: int = 0
    pages_crawled: int = 0
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None

    def is_finished(self):
        return self.status in ("done", "failed")


@dataclass
class PageRecord:
    job_id: str
    url: str
    depth: int
    status_code: int | None
    crawled_at: float = field(default_factory=time.time)


@dataclass
class LinkResult:
    job_id: str
    source_page: str
    target_url: str
    is_internal: bool
    status_code: int | None
    status: str
    redirect_chain: list
    error_message: str | None
    checked_at: float = field(default_factory=time.time)


@dataclass
class QueueItem:
    url: str
    depth: int
