import pytest

@pytest.fixture()
def owner_client(client):
    client.post("/api/v1/auth/register", json={"email": "o@x.com", "password": "p", "full_name": "O"})
    token = client.post("/api/v1/auth/login", json={"email": "o@x.com", "password": "p"}).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()
    return client, ws["id"]

BRAND_PAYLOAD = {
    "name": "Acme Corp",
    "company_type": "ecommerce",
    "description": "We sell widgets",
    "target_audience": "SMBs in Russia",
    "goals": ["increase_brand_awareness", "generate_leads"],
    "tone_of_voice": "professional",
    "posting_frequency": "daily",
    "networks": ["instagram", "vk", "telegram"]
}

def test_create_brand(owner_client):
    client, ws_id = owner_client
    response = client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert len(data["social_accounts"]) == 3

def test_get_brand(owner_client):
    client, ws_id = owner_client
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    response = client.get(f"/api/v1/workspaces/{ws_id}/brand")
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"

def test_update_brand(owner_client):
    client, ws_id = owner_client
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json=BRAND_PAYLOAD)
    response = client.patch(f"/api/v1/workspaces/{ws_id}/brand", json={"tone_of_voice": "casual"})
    assert response.status_code == 200
    assert response.json()["tone_of_voice"] == "casual"
