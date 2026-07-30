import json
import uuid
import time
from db import conn
from models import crawljob, PageRecord, LinkResult
from queries_help import row_to_link, row_to_job, row_to_page


def create_job(root_url, max_pages, max_depth):
    job = crawljob(
        id=str(uuid.uuid4()),
        root_url=root_url,
        status="queued",
        max_pages=max_pages,
        max_depth=max_depth,
        pages_queued=1,
    )
    insert_job_row(job)
    return job


def insert_job_row(job):
    conn.execute(
        """
        insert into jobs (id, root_url, status, max_pages, max_depth, pages_queued, pages_crawled, created_at, finished_at, error)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (job.id, job.root_url, job.status, job.max_pages, job.max_depth, job.pages_queued, job.pages_crawled, job.created_at, job.finished_at, job.error),
    )
    conn.commit()


def get_job(job_id):
    row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return row_to_job(row)


def get_recent_jobs(limit=10):
    rows = conn.execute("select * from jobs order by created_at desc limit ?", (limit,)).fetchall()
    jobs = []
    for row in rows:
        jobs.append(row_to_job(row))
    return jobs


def delete_job(job_id):
    conn.execute("delete from jobs where id = ?", (job_id,))
    conn.execute("delete from pages where job_id = ?", (job_id,))
    conn.execute("delete from links where job_id = ?", (job_id,))
    conn.commit()


def mark_job_finished(job_id, status, error):
    conn.execute(
        "update jobs set status = ?, error = ?, finished_at = ? where id = ?",
        (status, error, time.time(), job_id),
    )
    conn.commit()

def mark_job_in_progress(job_id, status, error):
    conn.execute("update jobs set status = ?, error = ? where id = ?", (status, error, job_id))
    conn.commit()

def bump_pages_crawled(job_id):
    conn.execute("update jobs set pages_crawled = pages_crawled + 1 where id = ?", (job_id,))
    conn.commit()

def set_pages_queued(job_id, n):
    conn.execute("update jobs set pages_queued = ? where id = ?", (n, job_id))
    conn.commit()

def save_page(rec):
    conn.execute("insert into pages (job_id, url, depth, status_code, crawled_at) values (?, ?, ?, ?, ?)",
                 (rec.job_id, rec.url, rec.depth, rec.status_code, rec.crawled_at),
                 )
    conn.commit()

def save_link(rec):
    conn.execute("""
Insert into links (
    job_id, source_page, target_url, is_internal,
    status_code, status, redirect_chain, error_message, checked_at
)
values (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
    rec.job_id, rec.source_page, rec.target_url, int(rec.is_internal),
    rec.status_code, rec.status, json.dumps(rec.redirect_chain),
    rec.error_message, rec.checked_at,
))
    conn.commit()

def get_all_links_for_job(job_id):
    rows = conn.execute("select * from links where job_id = ?", (job_id,)).fetchall()
    results = []
    for row in rows:
        results.append(row_to_link(row))
    return results

def get_status_breakdown(job_id):
    rows = conn.execute(
        "select status, count(*) as c from links where job_id = ? group by status", (job_id,)
    ).fetchall()
    breakdown = {}
    for row in rows:
        breakdown[row["status"]] = row["c"]
    return breakdown

