import asyncio
import logging
from queries import get_job, mark_job_running, mark_job_finished
from crawler import run_crawl

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task = None
        self._cancelled_ids = set()

    def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None

    async def enqueue(self, job_id):
        await self._queue.put(job_id)

    def cancel(self, job_id):
        self._cancelled_ids.add(job_id)

    def queue_size(self):
        return self._queue.qsize()

    async def _worker(self):
        while True:
            job_id = await self._queue.get()
            try:
                await self._process_job(job_id)
            except Exception:
                # never let one bad job take the worker down with it
                logger.exception("could not process job %s", job_id)
            finally:
                self._cancelled_ids.discard(job_id)
                self._queue.task_done()

    async def _process_job(self, job_id):
        job = get_job(job_id)
        if job is None:
            return

        if job_id in self._cancelled_ids:
            mark_job_finished(job_id, "failed", "cancelled")
            return

        mark_job_running(job_id)
        try:
            await run_crawl(job, should_stop=lambda: job_id in self._cancelled_ids)
        except Exception as e:
            logger.exception("crawl job %s failed", job_id)
            mark_job_finished(job_id, "failed", str(e))
            return

        if job_id in self._cancelled_ids:
            mark_job_finished(job_id, "failed", "cancelled")
        else:
            mark_job_finished(job_id, "done", None)


job_queue = JobQueue()
