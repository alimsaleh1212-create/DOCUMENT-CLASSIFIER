from app.domain.contracts import ClassifyJob


class RQQueue:
    """RQ queue adapter. Enqueues ClassifyJob payloads serialized via Pydantic."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url

    def enqueue(self, job: ClassifyJob) -> None:
        raise NotImplementedError
