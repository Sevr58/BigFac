from datetime import datetime, timedelta
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole


def _seed_user_brand(db, email: str):
    from app.core.security import hash_password
    user = User(email=email, hashed_password=hash_password("secret123"), full_name="T")
    db.add(user)
    db.flush()
    ws = Workspace(name="TW")
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(
        workspace_id=ws.id, name="TB", company_type="smb",
        description="d", target_audience="t", goals=[],
        tone_of_voice="n", posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id, network=NetworkType.telegram,
        handle="@ch", enabled=True, credentials={},
    )
    db.add(account)
    db.commit()
    db.refresh(brand)
    return user, brand


def _token(client, email, password="secret123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_schedule_draft(client, db):
    user, brand = _seed_user_brand(db, "sched@test.com")
    draft = Draft(
        brand_id=brand.id, network="telegram", format="post",
        funnel_stage="tofu", status=DraftStatus.approved, text="T",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    token = _token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    scheduled_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post(
        "/api/v1/publishing/schedule",
        json={"draft_id": draft.id, "scheduled_at": scheduled_at},
        headers=headers,
    )
    assert resp.status_code == 200
    db.refresh(draft)
    assert draft.status == DraftStatus.scheduled


def test_schedule_draft_wrong_status_returns_400(client, db):
    user, brand = _seed_user_brand(db, "s2@test.com")
    draft = Draft(
        brand_id=brand.id, network="telegram", format="post",
        funnel_stage="tofu", status=DraftStatus.draft, text="T",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    token = _token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    scheduled_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post(
        "/api/v1/publishing/schedule",
        json={"draft_id": draft.id, "scheduled_at": scheduled_at},
        headers=headers,
    )
    assert resp.status_code == 400


def test_publishing_queue(client, db):
    user, brand = _seed_user_brand(db, "q@test.com")
    draft = Draft(
        brand_id=brand.id, network="telegram", format="post",
        funnel_stage="tofu", status=DraftStatus.scheduled, text="T",
        scheduled_at=datetime.utcnow() + timedelta(hours=2),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    token = _token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/publishing/queue?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == draft.id


def test_publishing_log(client, db):
    from app.models.publishing import PublishedPost
    from app.core.security import hash_password

    user, brand = _seed_user_brand(db, "log@test.com")
    draft = Draft(
        brand_id=brand.id, network="telegram", format="post",
        funnel_stage="tofu", status=DraftStatus.published, text="T",
    )
    db.add(draft)
    db.flush()
    pp = PublishedPost(
        draft_id=draft.id, brand_id=brand.id,
        network="telegram", network_post_id="111", utm_params={},
    )
    db.add(pp)
    db.commit()

    token = _token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/publishing/log?brand_id={brand.id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["network_post_id"] == "111"
