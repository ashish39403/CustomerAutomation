from fastapi.testclient import TestClient


def test_health_liveness(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_reports_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert "database" in body
    assert body["database"]["status"] in {"ok", "error"}
    if response.status_code == 200:
        assert body["status"] == "ok"
        assert body["database"]["status"] == "ok"
