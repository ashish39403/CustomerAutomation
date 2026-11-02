from fastapi.testclient import TestClient

from app.core.config import settings


def test_admin_can_log_in_and_read_me(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={
            "email": settings.dashboard_username,
            "password": settings.dashboard_password,
        },
    )
    assert login.status_code == 200
    body = login.json()
    assert body["user"]["role"] == "admin"
    assert body["user"]["email"] == settings.admin_email

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_operator_can_log_in(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": settings.seed_operator_email,
            "password": settings.seed_operator_password,
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "operator"


def test_invalid_password_is_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": settings.dashboard_username, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_me_requires_session(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_logout_clears_session(client: TestClient) -> None:
    client.post(
        "/api/auth/login",
        json={
            "email": settings.dashboard_username,
            "password": settings.dashboard_password,
        },
    )
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    me = client.get("/api/auth/me")
    assert me.status_code == 401
