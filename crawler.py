import asyncio
import httpx
from fetch_page import fetch_page, extract_links, is_internal_url, normalize_url
from check_link import check_link
from queries import save_page, save_link, bump_pages_crawled, set_pages_queued
from models import PageRecord, LinkResult, QueueItem
from constants import link_check_concurrency


async def run_crawl(job, should_stop=None):
    async with httpx.AsyncClient() as client:
        await Crawl(client, job, should_stop).run()


class Crawl:
    """Walks one site breadth-first, a whole depth level at a time."""

    def __init__(self, client, job, should_stop=None):
        self.client = client
        self.job = job
        self.should_stop = should_stop or (lambda: False)
        self.sem = asyncio.Semaphore(link_check_concurrency)
        self.root = normalize_url(job.root_url)
        self.seen = {self.root}
        # one result per target url, so a nav link sitting on every page
        # gets requested once instead of once per page it shows up on
        self.checked = {}
        self.crawled = 0

    async def run(self):
        level = [QueueItem(self.root, 0)]
        try:
            while level and self.crawled < self.job.max_pages and not self.should_stop():
                set_pages_queued(self.job.id, len(level))
                level = await self.crawl_level(level)
        finally:
            set_pages_queued(self.job.id, 0)

    async def crawl_level(self, level):
        next_level = []
        for item in level:
            if self.crawled >= self.job.max_pages or self.should_stop():
                break
            next_level.extend(await self.crawl_page(item))
            self.crawled += 1
        return next_level

    async def crawl_page(self, item):
        page = await fetch_page(self.client, item.url)
        save_page(PageRecord(self.job.id, item.url, item.depth, page.status_code))
        bump_pages_crawled(self.job.id)
        if page.html is None:
            return []

        found = await asyncio.gather(*[
            self.check_and_queue(item, link)
            for link in extract_links(page.html, item.url)
        ])
        return [queued for queued in found if queued is not None]

    async def check_and_queue(self, item, link):
        result = self.checked.get(link)
        if result is None:
            async with self.sem:
                result = await check_link(self.client, link)
            self.checked[link] = result

        save_link(LinkResult(
            job_id=self.job.id,
            source_page=item.url,
            target_url=link,
            is_internal=is_internal_url(link, self.job.root_url),
            status_code=result.status_code,
            status=result.status,
            redirect_chain=result.redirect_chain,
            error_message=result.error_message,
        ))

        if item.depth >= self.job.max_depth or result.status not in ("ok", "redirect"):
            return None

        # queue where the link actually landed, so a redirect and its
        # destination don't both get crawled as separate pages
        target = normalize_url(result.final_url or link)
        if not is_internal_url(target, self.job.root_url) or target in self.seen:
            return None

        self.seen.add(target)
        return QueueItem(target, item.depth + 1)
