from __future__ import annotations

from redis import Redis
from rq import Queue

from app.domain.contracts import ClassifyJob

DEFAULT_QUEUE_NAME = "classify"
DEFAULT_JOB_FUNC = "worker.handler.classify_job"


class RQQueue:
    """RQ queue adapter. Enqueues ClassifyJob payloads serialized via Pydantic."""

    def __init__(
        self,
        redis_url: str,
        queue_name: str = DEFAULT_QUEUE_NAME,
        job_func: str = DEFAULT_JOB_FUNC,
    ) -> None:
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(queue_name, connection=self._redis)
        self._job_func = job_func

    def enqueue(self, job: ClassifyJob) -> None:
        self._queue.enqueue(self._job_func, job.model_dump_json())


def build_worker_queues(redis_url: str) -> list[Queue]:
    redis = Redis.from_url(redis_url)
    return [Queue(DEFAULT_QUEUE_NAME, connection=redis)]
