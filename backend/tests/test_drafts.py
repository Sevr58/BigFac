import pytest
from unittest.mock import patch


def _auth_and_setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "u@t.com", "password": "pass1234", "full_name": "U"
    })
    resp = client.post("/api/v1/auth/login", json={"email": "u@t.com", "password": "pass1234"})
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
    return headers, ws_id, brand["id"]


def test_generate_draft(client):
    headers, ws_id, brand_id = _auth_and_setup(client)
    with patch("app.tasks.draft_tasks.generate_draft.delay") as mock:
        resp = client.post("/api/v1/drafts/generate", json={
            "brand_id": brand_id,
            "network": "instagram",
            "format": "carousel",
            "funnel_stage": "tofu",
        }, headers=headers)
        assert resp.status_code == 202
        assert mock.called


def test_list_drafts(client):
    headers, ws_id, brand_id = _auth_and_setup(client)
    resp = client.get(f"/api/v1/drafts/?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_update_draft_creates_version(client, db):
    from app.models.content import Draft, DraftStatus
    headers, ws_id, brand_id = _auth_and_setup(client)
    draft = Draft(
        brand_id=brand_id,
        network="instagram",
        format="carousel",
        funnel_stage="tofu",
        status=DraftStatus.draft,
        text="Original text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.patch(f"/api/v1/drafts/{draft.id}", json={"text": "Updated text"}, headers=headers)
    assert resp.status_code == 200

    from app.models.content import DraftVersion
    versions = db.query(DraftVersion).filter(DraftVersion.draft_id == draft.id).all()
    assert len(versions) == 1
    assert versions[0].text == "Original text"


def test_submit_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, ws_id, brand_id = _auth_and_setup(client)
    draft = Draft(
        brand_id=brand_id,
        network="telegram",
        format="longread",
        funnel_stage="mofu",
        status=DraftStatus.draft,
        text="Some text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/drafts/{draft.id}/submit", headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.needs_review
