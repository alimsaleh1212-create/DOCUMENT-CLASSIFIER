"""API tests: /predictions/recent, /predictions/{pid}/label."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.contracts import PredictionLabel, PredictionOut
from tests.api.conftest import auth_headers


def _seed_prediction(top1: float) -> tuple[str, PredictionOut]:
    """Build a PredictionOut with the given top1 (not yet persisted)."""
    pid = str(uuid.uuid4())
    p = PredictionOut(
        id=pid,
        batch_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        label=PredictionLabel.memo,
        top1_confidence=top1,
        top5=[(PredictionLabel.memo, top1)],
        overlay_url=None,
        model_version="test-v0",
        created_at=datetime.now(UTC),
    )
    return pid, p


def test_list_recent_as_admin_returns_list(client: TestClient, admin_token: str) -> None:
    r = client.get("/predictions/recent", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_recent_no_token_returns_401(client: TestClient) -> None:
    r = client.get("/predictions/recent")
    assert r.status_code == 401


def test_relabel_high_confidence_as_reviewer_returns_422(
    client: TestClient, reviewer_token: str
) -> None:
    """Reviewers cannot relabel documents with confidence >= 0.7."""
    from app.api.deps import get_prediction_repo  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    pid, p = _seed_prediction(top1=0.95)
    app.dependency_overrides[get_prediction_repo]().seed(p)

    r = client.patch(
        f"/predictions/{pid}/label",
        json={"new_label": "letter"},
        headers=auth_headers(reviewer_token),
    )
    assert r.status_code == 422


def test_relabel_high_confidence_as_admin_succeeds(client: TestClient, admin_token: str) -> None:
    """Admins can override any label regardless of confidence."""
    from app.api.deps import get_prediction_repo  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    pid, p = _seed_prediction(top1=0.95)
    app.dependency_overrides[get_prediction_repo]().seed(p)

    r = client.patch(
        f"/predictions/{pid}/label",
        json={"new_label": "letter"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200


def test_relabel_low_confidence_succeeds(client: TestClient, admin_token: str) -> None:
    from app.api.deps import get_prediction_repo  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415

    pid, p = _seed_prediction(top1=0.55)
    app.dependency_overrides[get_prediction_repo]().seed(p)

    r = client.patch(
        f"/predictions/{pid}/label",
        json={"new_label": "form"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["label"] == "form"
