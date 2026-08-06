import json
import time
import uuid

from db import conn
from models import CrawlJob, LinkResult


def row_to_job(row):
    return CrawlJob(
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


def create_job(root_url, max_pages, max_depth):
    job = CrawlJob(
        id=str(uuid.uuid4()),
        root_url=root_url,
        status="queued",
        max_pages=max_pages,
        max_depth=max_depth,
        pages_queued=1,
    )
    conn.execute(
        """
        insert into jobs (id, root_url, status, max_pages, max_depth, pages_queued, pages_crawled, created_at, finished_at, error)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (job.id, job.root_url, job.status, job.max_pages, job.max_depth, job.pages_queued,
         job.pages_crawled, job.created_at, job.finished_at, job.error),
    )
    conn.commit()
    return job


def get_job(job_id):
    row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return row_to_job(row)


def get_recent_jobs(limit=10):
    rows = conn.execute("select * from jobs order by created_at desc limit ?", (limit,)).fetchall()
    return [row_to_job(row) for row in rows]


def delete_job(job_id):
    conn.execute("delete from links where job_id = ?", (job_id,))
    conn.execute("delete from pages where job_id = ?", (job_id,))
    conn.execute("delete from jobs where id = ?", (job_id,))
    conn.commit()


def mark_job_running(job_id):
    conn.execute("update jobs set status = 'running', error = null where id = ?", (job_id,))
    conn.commit()


def mark_job_finished(job_id, status, error):
    conn.execute(
        "update jobs set status = ?, error = ?, finished_at = ? where id = ?",
        (status, error, time.time(), job_id),
    )
    conn.commit()


def bump_pages_crawled(job_id):
    conn.execute("update jobs set pages_crawled = pages_crawled + 1 where id = ?", (job_id,))
    conn.commit()


def set_pages_queued(job_id, count):
    conn.execute("update jobs set pages_queued = ? where id = ?", (count, job_id))
    conn.commit()


def save_page(rec):
    conn.execute(
        "insert into pages (job_id, url, depth, status_code, crawled_at) values (?, ?, ?, ?, ?)",
        (rec.job_id, rec.url, rec.depth, rec.status_code, rec.crawled_at),
    )
    conn.commit()


def save_link(rec):
    conn.execute(
        """
        insert into links (job_id, source_page, target_url, is_internal, status_code, status, redirect_chain, error_message, checked_at)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (rec.job_id, rec.source_page, rec.target_url, int(rec.is_internal), rec.status_code,
         rec.status, json.dumps(rec.redirect_chain), rec.error_message, rec.checked_at),
    )
    conn.commit()


def get_all_links_for_job(job_id):
    rows = conn.execute("select * from links where job_id = ?", (job_id,)).fetchall()
    return [row_to_link(row) for row in rows]


def get_status_breakdown(job_id):
    rows = conn.execute(
        "select status, count(*) as c from links where job_id = ? group by status", (job_id,)
    ).fetchall()
    return {row["status"]: row["c"] for row in rows}
