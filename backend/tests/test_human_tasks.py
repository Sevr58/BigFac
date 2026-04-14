def _auth_and_brand(client):
    client.post("/api/v1/auth/register", json={"email": "ht@t.com", "password": "pass1234", "full_name": "HT"})
    resp = client.post("/api/v1/auth/login", json={"email": "ht@t.com", "password": "pass1234"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}, headers=headers)
    ws_id = ws.json()["id"]
    client.post(f"/api/v1/workspaces/{ws_id}/brand", json={
        "name": "B", "company_type": "product",
        "description": "d", "target_audience": "a",
        "goals": [], "tone_of_voice": "f",
        "posting_frequency": "daily", "networks": []
    }, headers=headers)
    brand = client.get(f"/api/v1/workspaces/{ws_id}/brand", headers=headers).json()
    return headers, brand["id"]


def test_create_human_task(client):
    headers, brand_id = _auth_and_brand(client)
    resp = client.post("/api/v1/human-tasks/", json={
        "brand_id": brand_id,
        "title": "Record intro video",
        "description": "Record a 30-second intro for the new product launch",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Record intro video"
    assert data["status"] == "pending"


def test_list_human_tasks(client):
    headers, brand_id = _auth_and_brand(client)
    client.post("/api/v1/human-tasks/", json={
        "brand_id": brand_id, "title": "Task 1",
    }, headers=headers)
    resp = client.get(f"/api/v1/human-tasks/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_complete_human_task(client, db):
    from app.models.content import HumanTask, HumanTaskStatus
    headers, brand_id = _auth_and_brand(client)
    task = HumanTask(brand_id=brand_id, title="Record video")
    db.add(task)
    db.commit()
    db.refresh(task)

    resp = client.patch(f"/api/v1/human-tasks/{task.id}/complete",
                        json={}, headers=headers)
    assert resp.status_code == 200
    db.refresh(task)
    assert task.status == HumanTaskStatus.completed
