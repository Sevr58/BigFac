import pytest
from unittest.mock import patch

@pytest.fixture()
def workspace_with_brand(client):
    client.post("/api/v1/auth/register", json={"email": "o@x.com", "password": "p", "full_name": "O"})
    token = client.post("/api/v1/auth/login", json={"email": "o@x.com", "password": "p"}).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()
    ws_id = ws["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "Acme", "company_type": "ecommerce", "description": "Sell widgets",
        "target_audience": "SMBs", "goals": ["leads"], "tone_of_voice": "professional",
        "posting_frequency": "daily", "networks": ["instagram", "vk"]
    })
    return client, ws_id

MOCK_STRATEGY = {
    "pillars": [
        {"title": "Education", "description": "Teach audience", "funnel_stages": "tofu,mofu"},
        {"title": "Cases", "description": "Show results", "funnel_stages": "mofu,bofu"},
    ],
    "plan_items": [
        {"network": "instagram", "format": "reels", "funnel_stage": "tofu",
         "topic": "5 tips for widgets", "planned_date": "2026-04-15", "pillar_index": 0},
    ]
}

def test_generate_strategy(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        response = client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    assert response.status_code == 200
    data = response.json()
    assert len(data["pillars"]) == 2
    assert len(data["plan_items"]) >= 1

def test_get_pillars(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    response = client.get(f"/api/v1/strategy/workspaces/{ws_id}/pillars")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_plan(workspace_with_brand):
    client, ws_id = workspace_with_brand
    with patch("app.services.strategy_service.call_claude", return_value=MOCK_STRATEGY):
        client.post(f"/api/v1/strategy/workspaces/{ws_id}/generate")
    response = client.get(f"/api/v1/strategy/workspaces/{ws_id}/plan")
    assert response.status_code == 200
    assert len(response.json()) >= 1
