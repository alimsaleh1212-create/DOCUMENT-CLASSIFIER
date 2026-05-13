from __future__ import annotations

import json
import uuid

import pytest

from app.domain.contracts import ClassifyJob
from app.infra import queue as queue_module


class FakeRedis:
    @classmethod
    def from_url(cls, redis_url: str) -> str:
        return redis_url


class FakeQueue:
    instances: list[FakeQueue] = []

    def __init__(self, name: str, connection: str) -> None:
        self.name = name
        self.connection = connection
        self.enqueued: list[tuple[str, str]] = []
        FakeQueue.instances.append(self)

    def enqueue(self, job_func: str, payload: str) -> None:
        self.enqueued.append((job_func, payload))


def test_rq_queue_enqueues_serialized_classify_job(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeQueue.instances.clear()
    monkeypatch.setattr(queue_module, "Redis", FakeRedis)
    monkeypatch.setattr(queue_module, "Queue", FakeQueue)
    adapter = queue_module.RQQueue("redis://redis:6379/0")
    job = ClassifyJob(
        batch_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        blob_key="documents/batch/document.tif",
        request_id=str(uuid.uuid4()),
    )

    adapter.enqueue(job)

    fake_queue = FakeQueue.instances[0]
    assert fake_queue.name == "classify"
    assert fake_queue.connection == "redis://redis:6379/0"
    assert fake_queue.enqueued[0][0] == "worker.__main__.classify_job"
    assert json.loads(fake_queue.enqueued[0][1]) == job.model_dump()


def test_build_worker_queues_returns_classify_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeQueue.instances.clear()
    monkeypatch.setattr(queue_module, "Redis", FakeRedis)
    monkeypatch.setattr(queue_module, "Queue", FakeQueue)

    queues = queue_module.build_worker_queues("redis://redis:6379/0")

    assert queues[0].name == "classify"
