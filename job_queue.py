import asyncio
import traceback
from queries import get_job, mark_job_in_progress, mark_job_finished
from crawler import run_crawl

class JobQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._running_id = None
        self._worker_task = None
        self._cancelled_ids = set()
        self._finished_count = 0

    def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, job_id):
        await self._queue.put(job_id)

    def is_running(self, job_id):
        return self._running_id == job_id

    def cancel(self, job_id):
        self._cancelled_ids.add(job_id)

    def queue_size(self):
        return self._queue.qsize()

    def has_pending(self):
        return self._queue.qsize() > 0

    def current_job_id(self):
        return self._running_id

    def finished_count(self):
        return self._finished_count

    async def _worker(self):
        while True:
            job_id = await self._queue.get()
            await self._process_job(job_id)
            self._queue.task_done()

    async def _process_job(self, job_id):
        if job_id in self._cancelled_ids:
            self._cancelled_ids.remove(job_id)
            return

        job = get_job(job_id)
        if job is None:
            return

        self._running_id = job_id
        mark_job_in_progress(job_id, "running", None)

        try:
            await run_crawl(job)
            mark_job_finished(job_id, "done", None)
        except Exception as e:
            self._log_failure(job_id, e)
            mark_job_finished(job_id, "failed", str(e))
        finally:
            self._running_id = None
            self._finished_count += 1

    def _log_failure(self, job_id, err):
        print("job", job_id, "blew up:")
        traceback.print_exc()

job_queue = JobQueue()
