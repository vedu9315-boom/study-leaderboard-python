
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://appuser:devpassword@localhost:5432/leaderboard",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app import cache, db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture
def student_name():
    return f"Integration-{uuid.uuid4().hex[:10]}"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["postgres"] is True
    assert response.json()["redis"] is True


def test_start_session(student_name):
    response = client.post(
        "/sessions/start",
        json={"student": student_name, "subject": "Testing"},
    )
    assert response.status_code == 201
    assert response.json()["student"] == student_name
    cache.drop(f"live:{student_name}")


def test_start_requires_student():
    response = client.post("/sessions/start", json={"student": ""})
    assert response.status_code == 400


def test_duplicate_timer_conflict(student_name):
    first = client.post(
        "/sessions/start",
        json={"student": student_name, "subject": "Testing"},
    )
    assert first.status_code == 201

    try:
        second = client.post(
            "/sessions/start",
            json={"student": student_name},
        )
        assert second.status_code == 409
    finally:
        cache.drop(f"live:{student_name}")


def test_stop_without_timer(student_name):
    response = client.post(
        "/sessions/stop", json={"student": student_name}
    )
    assert response.status_code == 404


def test_stop_session_persists_to_database(student_name):
    started = client.post(
        "/sessions/start",
        json={"student": student_name, "subject": "Integration"},
    )
    assert started.status_code == 201

    live = cache.get_json(f"live:{student_name}")
    past = datetime.now(timezone.utc) - timedelta(seconds=61)
    live["started"] = past.isoformat()
    cache.set_json(f"live:{student_name}", live, ttl=3600)

    response = client.post(
        "/sessions/stop", json={"student": student_name}
    )
    assert response.status_code == 200

    result = response.json()
    assert result["verdict"] == "ok"
    assert result["credited"] >= 60

    try:
        rows = db.query(
            "SELECT subject, seconds FROM sessions WHERE student=%s",
            (student_name,),
        )
        assert rows
        assert sum(row["seconds"] for row in rows) == result["credited"]
    finally:
        db.query(
            "DELETE FROM sessions WHERE student=%s",
            (student_name,),
            fetch=False,
        )
        cache.drop(f"live:{student_name}", "board:all")


def test_weekly_leaderboard():
    response = client.get("/leaderboard?period=week")
    assert response.status_code == 200
    assert response.json()["period"] == "week"
    assert isinstance(response.json()["leaderboard"], list)


def test_student_not_found(student_name):
    response = client.get(f"/students/{student_name}")
    assert response.status_code == 404
