from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import init_db, close_db
from queries import create_job, get_job, get_recent_jobs
from job_queue import job_queue
from report import build_report, report_filters
from constants import (
    min_pages_limit, max_pages_limit,
    min_depth_limit, max_depth_limit,
    default_max_pages, default_max_depth
)

index_file = Path(__file__).parent / "index.html"


@asynccontextmanager
async def lifespan(app):
    init_db()
    job_queue.start()
    yield
    await job_queue.stop()
    close_db()


app = FastAPI(lifespan=lifespan)


class StartCrawlBody(BaseModel):
    url: str
    max_pages: int = default_max_pages
    max_depth: int = default_max_depth


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


def job_payload(job):
    return {
        "id": job.id,
        "root_url": job.root_url,
        "status": job.status,
        "pages_queued": job.pages_queued,
        "pages_crawled": job.pages_crawled,
        "max_pages": job.max_pages,
        "max_depth": job.max_depth,
        "error": job.error,
    }


def load_job(job_id):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "no job with that id")
    return job


@app.get("/api/health")
async def health_check():
    return {"ok": True, "queue_size": job_queue.queue_size()}


@app.post("/api/crawl")
async def start_crawl(body: StartCrawlBody):
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, "that doesn't look like a valid url")

    job = create_job(
        root_url=body.url,
        max_pages=clamp(body.max_pages, min_pages_limit, max_pages_limit),
        max_depth=clamp(body.max_depth, min_depth_limit, max_depth_limit),
    )

    await job_queue.enqueue(job.id)
    return {"job_id": job.id}


@app.get("/api/crawl")
async def list_recent_crawls():
    return [job_payload(job) for job in get_recent_jobs(limit=10)]


@app.get("/api/crawl/{job_id}")
async def crawl_status(job_id: str):
    return job_payload(load_job(job_id))


@app.delete("/api/crawl/{job_id}")
async def cancel_crawl(job_id: str):
    job = load_job(job_id)
    if job.is_finished():
        raise HTTPException(409, "that job already finished")
    job_queue.cancel(job_id)
    return {"cancelled": True}


@app.get("/api/crawl/{job_id}/report")
async def crawl_report(job_id: str, filter_by: str = Query("all", alias="filter")):
    if filter_by not in report_filters:
        raise HTTPException(400, "filter must be one of: " + ", ".join(report_filters))

    job = load_job(job_id)
    if not job.is_finished():
        raise HTTPException(409, "still crawling, check back in a sec")

    report = build_report(job_id, filter_by=filter_by)
    report["job"] = job_payload(job)
    return report


@app.get("/")
async def serve_index():
    return FileResponse(index_file)
