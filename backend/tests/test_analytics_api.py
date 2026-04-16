from datetime import datetime
from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole
from app.core.security import hash_password


def _seed_analytics(db):
    user = User(email="an@test.com", hashed_password=hash_password("pw"), full_name="A")
    db.add(user)
    db.flush()
    ws = Workspace(name="AW")
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(
        workspace_id=ws.id, name="AB", company_type="smb",
        description="Test brand", target_audience="t",
        goals=["awareness"], tone_of_voice="friendly", posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    draft = Draft(
        brand_id=brand.id, network="vk", format="post",
        funnel_stage="tofu", status=DraftStatus.published, text="T",
    )
    db.add(draft)
    db.flush()
    pp = PublishedPost(
        draft_id=draft.id, brand_id=brand.id, network="vk",
        network_post_id="p1", utm_params={}, published_at=datetime.utcnow(),
    )
    db.add(pp)
    db.flush()
    m = PostMetrics(
        published_post_id=pp.id, brand_id=brand.id,
        views=1000, likes=50, comments=5, shares=10, reach=800,
    )
    db.add(m)
    db.commit()
    db.refresh(brand)
    return user, brand, pp


def _get_token(client, email, password="pw"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_analytics_summary(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/analytics/summary?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_posts" in data
    assert data["total_posts"] == 1
    assert "by_network" in data
    assert data["by_network"]["vk"]["views"] == 1000


def test_analytics_posts(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/analytics/posts?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["network"] == "vk"
    assert data[0]["metrics"]["views"] == 1000


def test_record_lead_event(client, db):
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/analytics/leads",
        json={
            "brand_id": brand.id,
            "published_post_id": pp.id,
            "event_type": "lead",
            "utm_source": "vk",
            "utm_medium": "post",
            "utm_campaign": "scf",
            "utm_content": "tofu",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    ev = db.query(LeadEvent).filter(LeadEvent.brand_id == brand.id).first()
    assert ev is not None
    assert ev.utm_source == "vk"


def test_feedback_loop(client, db):
    from unittest.mock import patch
    user, brand, pp = _seed_analytics(db)
    token = _get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    with patch(
        "app.api.v1.analytics._call_claude_feedback",
        return_value="Рекомендация: публикуйте больше Reels.",
    ):
        resp = client.post(
            f"/api/v1/analytics/feedback-loop?brand_id={brand.id}",
            headers=headers,
        )
    assert resp.status_code == 200
    assert "Рекомендация" in resp.json()["suggestion"]
