import pytest

@pytest.fixture()
def auth_client(client):
    """Returns client with Authorization header for a registered user."""
    client.post("/api/v1/auth/register", json={
        "email": "owner@example.com", "password": "pass123", "full_name": "Owner"
    })
    resp = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "pass123"})
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client

def test_create_workspace(auth_client):
    response = auth_client.post("/api/v1/workspaces/", json={"name": "My Agency"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Agency"
    assert data["my_role"] == "owner"

def test_list_workspaces(auth_client):
    auth_client.post("/api/v1/workspaces/", json={"name": "WS1"})
    auth_client.post("/api/v1/workspaces/", json={"name": "WS2"})
    response = auth_client.get("/api/v1/workspaces/")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_invite_member(auth_client, client):
    # Register second user
    client.post("/api/v1/auth/register", json={
        "email": "editor@example.com", "password": "pass123", "full_name": "Editor"
    })
    ws = auth_client.post("/api/v1/workspaces/", json={"name": "Team WS"}).json()
    response = auth_client.post(f"/api/v1/workspaces/{ws['id']}/members", json={
        "email": "editor@example.com", "role": "editor"
    })
    assert response.status_code == 201
    assert response.json()["role"] == "editor"
