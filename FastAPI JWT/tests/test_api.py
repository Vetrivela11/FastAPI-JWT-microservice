import os
import tempfile

# Use a temporary database for tests, configured before importing the app.
fd, test_db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough"

from fastapi.testclient import TestClient
from main import app, Base, engine

client = TestClient(app)

def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_register_login_and_profile():
    response = client.post("/auth/register", json={
        "username": "tester",
        "email": "tester@example.com",
        "password": "StrongPass123"
    })
    assert response.status_code == 201
    assert "hashed_password" not in response.json()

    response = client.post("/auth/login", data={
        "username": "tester",
        "password": "StrongPass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "tester"

def test_protected_items_crud():
    client.post("/auth/register", json={
        "username": "cruduser",
        "email": "crud@example.com",
        "password": "StrongPass123"
    })
    login = client.post("/auth/login", data={
        "username": "cruduser",
        "password": "StrongPass123"
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post("/items", json={
        "title": "Learn FastAPI",
        "description": "Build a secure API",
        "completed": False
    }, headers=headers)
    assert created.status_code == 201
    item_id = created.json()["id"]

    listed = client.get("/items", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(f"/items/{item_id}", json={"completed": True}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["completed"] is True

    deleted = client.delete(f"/items/{item_id}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/items/{item_id}", headers=headers)
    assert missing.status_code == 404

def test_items_require_authentication():
    response = client.get("/items")
    assert response.status_code == 401

def test_duplicate_username_rejected():
    payload = {"username": "duplicate", "email": "one@example.com", "password": "StrongPass123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    payload["email"] = "two@example.com"
    assert client.post("/auth/register", json=payload).status_code == 409
