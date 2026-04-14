def _auth_and_brand(client):
    client.post("/api/v1/auth/register", json={"email": "a@t.com", "password": "pass1234", "full_name": "A"})
    resp = client.post("/api/v1/auth/login", json={"email": "a@t.com", "password": "pass1234"})
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


def test_approval_queue_empty(client):
    headers, brand_id = _auth_and_brand(client)
    resp = client.get(f"/api/v1/approvals/queue?brand_id={brand_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_approve_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="telegram",
        format="longread", funnel_stage="mofu",
        status=DraftStatus.needs_review, text="Review me",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/approve",
                       json={"comment": "Looks great"}, headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.approved


def test_reject_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="vk",
        format="long_post", funnel_stage="bofu",
        status=DraftStatus.needs_review, text="Draft text",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/reject",
                       json={"comment": "Wrong tone"}, headers=headers)
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.rejected


def test_cannot_approve_non_review_draft(client, db):
    from app.models.content import Draft, DraftStatus
    headers, brand_id = _auth_and_brand(client)
    draft = Draft(
        brand_id=brand_id, network="instagram",
        format="carousel", funnel_stage="tofu",
        status=DraftStatus.draft, text="Not submitted",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    resp = client.post(f"/api/v1/approvals/{draft.id}/approve",
                       json={}, headers=headers)
    assert resp.status_code == 400
