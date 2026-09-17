from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_inquiry_status_endpoint():
    response = client.get("/api/inquiry/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_inquiry_start_endpoint_generates_questions():
    response = client.post(
        "/api/inquiry/start",
        json={"task_id": "task-123", "goal": "Build a RAG application", "state": {"project": "demo"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["questions"]


def test_inquiry_answer_endpoint_accepts_answer():
    start = client.post(
        "/api/inquiry/start",
        json={"task_id": "task-240", "goal": "Build a RAG application", "state": {"project": "demo"}},
    )
    question_id = start.json()["questions"][0]["question_id"]
    response = client.post(
        f"/api/inquiry/{question_id}/answer",
        json={"task_id": "task-240", "answer": "Use PostgreSQL + pgvector", "confidence": 0.92},
    )
    assert response.status_code == 200
    assert response.json()["status"] in {"resolved", "answered", "accepted"}


def test_computer_endpoints_are_available():
    apps = client.get("/api/computer/applications")
    assert apps.status_code == 200
    assert apps.json()["applications"]

    inspect_response = client.post(
        "/api/computer/inspect",
        json={"application": "Notepad"},
    )
    assert inspect_response.status_code == 200
    assert inspect_response.json()["success"] is True


def test_lab_observability_snapshot_contains_runtime_domains():
    response = client.get("/api/lab/observability")
    assert response.status_code == 200
    data = response.json()
    assert data["agents"]
    assert data["tools"]
    assert "work_context" in data
    assert "verification" in data
