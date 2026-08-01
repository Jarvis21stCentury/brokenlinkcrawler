import asyncio
import httpx
from fetch_page import fetch_page, extract_links, is_internal_url
from check_link import check_link
from queries import save_page, save_link, bump_pages_crawled, set_pages_queued
from models import PageRecord, LinkResult, QueueItem
from constants import link_check_concurrency

class CrawlStats:
    def __init__(self):
        self.pages_crawled = 0
        self.links_checked = 0
        self.links_broken = 0

    def record_page(self):
        self.pages_crawled += 1

    def record_link(self, result):
        self.links_checked += 1
        if result.status == "broken":
            self.links_broken += 1

async def run_crawl(job):
    seen = {job.root_url}
    queue = [QueueItem(job.root_url, 0)]
    stats = CrawlStats()

    async with httpx.AsyncClient() as client:
        while queue and stats.pages_crawled < job.max_pages:
            queue = await process_level(client, job, queue, seen, stats)

async def process_level(client, job, level, seen, stats):
    next_queue = []
    set_pages_queued(job.id, len(level))

    for item in level:
        if stats.pages_crawled >= job.max_pages:
            break
        if item.depth > job.max_depth:
            continue
        await process_single_page(client, job, item, seen, stats, next_queue)

    return next_queue

async def process_single_page(client, job, item, seen, stats, next_queue):
    page = await fetch_page(client, item.url)
    save_page(PageRecord(job.id, item.url, item.depth, page.status_code))
    stats.record_page()
    bump_pages_crawled(job.id)
    if page.html is None:
        return

    links_on_page = extract_links(page.html, item.url)
    can_go_deeper = (item.depth + 1) <= job.max_depth
    await check_all_links(client, job, item, links_on_page, seen, can_go_deeper, next_queue, stats)

async def check_all_links(client, job, item, links, seen, can_go_deeper, next_queue, stats):
    sem = asyncio.Semaphore(link_check_concurrency)
    tasks = []

    for link in links:
        task = handle_one_link(client, sem, job, item, link, seen, can_go_deeper, next_queue, stats)
        tasks.append(task)

    if tasks:
        await asyncio.gather(*tasks)

async def handle_one_link(client, sem, job, item, link, seen, can_go_deeper, next_queue, stats):
    async with sem:
        internal = is_internal_url(link, job.root_url)
        result = await check_link(client, link)
        stats.record_link(result)
        save_link(LinkResult(
            job_id = job.id,
            source_page = item.url,
            target_url = link,
            is_internal = internal,
            status_code = result.status_code,
            status = result.status,
            redirect_chain = result.redirect_chain,
            error_message = result.error_message,
        ))

        should_follow = internal and result.status != "broken" and link not in seen and can_go_deeper
        if should_follow:
            seen.add(link)
            next_queue.append(QueueItem(link, item.depth + 1))