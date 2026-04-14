import pytest
from unittest.mock import patch


def _register_and_login(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "password123", "full_name": "Test"
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com", "password": "password123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_workspace_and_brand(client, headers):
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "Brand", "company_type": "product",
        "description": "desc", "target_audience": "all",
        "goals": [], "tone_of_voice": "friendly",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return ws_id, brand["id"]


def test_initiate_upload(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    resp = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id,
        "name": "interview.mp4",
        "asset_type": "video",
        "file_size": 1024 * 1024 * 100,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "asset_id" in data
    assert "upload_url" in data


def test_list_assets(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    resp = client.get(f"/api/v1/assets/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_confirm_asset(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    init = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    asset_id = init.json()["asset_id"]

    with patch("app.tasks.asset_tasks.process_asset.delay") as mock_task:
        resp = client.post(f"/api/v1/assets/{asset_id}/confirm", headers=headers)
        assert resp.status_code == 200
        mock_task.assert_called_once_with(asset_id)


def test_delete_asset(client):
    headers = _register_and_login(client)
    ws_id, brand_id = _create_workspace_and_brand(client, headers)
    init = client.post("/api/v1/assets/initiate", json={
        "brand_id": brand_id, "name": "file.mp4",
        "asset_type": "video", "file_size": 1000,
    }, headers=headers)
    asset_id = init.json()["asset_id"]
    resp = client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
    assert resp.status_code == 204
