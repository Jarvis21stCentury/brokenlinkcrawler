import json
from models import LinkResult, crawljob, PageRecord


def row_to_link(row):
    return LinkResult(
        job_id=row["job_id"],
        source_page=row["source_page"],
        target_url=row["target_url"],
        is_internal=bool(row["is_internal"]),
        status_code=row["status_code"],
        status=row["status"],
        redirect_chain=json.loads(row["redirect_chain"]),
        error_message=row["error_message"],
        checked_at=row["checked_at"],
    )


def row_to_job(row):
    return crawljob(
        id=row["id"],
        root_url=row["root_url"],
        status=row["status"],
        max_pages=row["max_pages"],
        max_depth=row["max_depth"],
        pages_queued=row["pages_queued"],
        pages_crawled=row["pages_crawled"],
        created_at=row["created_at"],
        finished_at=row["finished_at"],
        error=row["error"],
    )


def row_to_page(row):
    return PageRecord(
        job_id=row["job_id"],
        url=row["url"],
        depth=row["depth"],
        status_code=row["status_code"],
        crawled_at=row["crawled_at"],
    )
