"""
scripts/enqueue_local.py

Minimal RQ client to enqueue a ClassifyJob for local testing.
Usage:
    python scripts/enqueue_local.py <batch_id> <document_id>
Example:
    python scripts/enqueue_local.py test_batch doc_001
"""

import sys
import uuid
from rq import Queue
from redis import Redis

REDIS_URL = "redis://localhost:6379"
QUEUE_NAME = "classify"


def main(batch_id: str, document_id: str) -> None:
    redis_conn = Redis.from_url(REDIS_URL)
    q = Queue(QUEUE_NAME, connection=redis_conn)

    job_payload = {
        "batch_id": batch_id,
        "document_id": document_id,
        "blob_key": f"documents/{batch_id}/{document_id}.tif",
        "request_id": str(uuid.uuid4()),
    }
    q.enqueue("worker.handler.classify_job", job_payload)
    print(f"Enqueued job for batch={batch_id} doc={document_id}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/enqueue_local.py <batch_id> <document_id>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])