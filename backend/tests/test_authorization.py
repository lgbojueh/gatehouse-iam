from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login(email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_user_cannot_open_admin_users():
    token = login("user@example.com", "User123!")
    response = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_analyst_can_view_security_overview():
    token = login("analyst@example.com", "Analyst123!")
    response = client.get("/api/security/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["viewer_role"] == "analyst"


def test_admin_can_list_users():
    token = login("admin@example.com", "Admin123!")
    response = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) >= 3
