from unittest.mock import patch
from datetime import datetime, timedelta
from app.models.publishing import PublishedPost, PostMetrics
from app.models.content import Draft, DraftStatus
from app.models.brand import Brand, SocialAccount, NetworkType
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole


def _seed_published_post(db, network: str = "vk") -> PublishedPost:
    from app.core.security import hash_password
    user = User(
        email=f"at_{network}@test.com",
        hashed_password=hash_password("pw"),
        full_name="AT",
    )
    db.add(user)
    db.flush()
    ws = Workspace(name="ATW")
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=UserRole.owner))
    brand = Brand(
        workspace_id=ws.id, name="ATB", company_type="smb",
        description="d", target_audience="t", goals=[],
        tone_of_voice="n", posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id,
        network=NetworkType(network),
        handle="@ch", enabled=True,
        credentials={"access_token": "TOK", "owner_id": "-999"},
    )
    db.add(account)
    draft = Draft(
        brand_id=brand.id, network=network, format="post",
        funnel_stage="tofu", status=DraftStatus.published, text="T",
    )
    db.add(draft)
    db.flush()
    pp = PublishedPost(
        draft_id=draft.id, brand_id=brand.id, network=network,
        network_post_id="123", utm_params={},
        published_at=datetime.utcnow() - timedelta(days=2),
    )
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return pp


def test_collect_metrics_for_vk(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post

    pp = _seed_published_post(db, "vk")
    fake_metrics = {"views": 500, "likes": 30, "comments": 5, "shares": 2}

    with patch("app.tasks.analytics_tasks._fetch_vk_metrics", return_value=fake_metrics):
        _collect_metrics_for_post(pp.id, db)

    m = db.query(PostMetrics).filter(PostMetrics.published_post_id == pp.id).first()
    assert m is not None
    assert m.views == 500
    assert m.likes == 30


def test_collect_metrics_for_telegram_returns_empty(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post

    pp = _seed_published_post(db, "telegram")

    with patch("app.tasks.analytics_tasks._fetch_telegram_metrics", return_value={}):
        _collect_metrics_for_post(pp.id, db)

    # No metrics row created for empty result
    m = db.query(PostMetrics).filter(PostMetrics.published_post_id == pp.id).first()
    assert m is None


def test_collect_metrics_skips_posts_older_than_30_days(db):
    from app.tasks.analytics_tasks import _collect_metrics_for_post

    pp = _seed_published_post(db, "vk")
    pp.published_at = datetime.utcnow() - timedelta(days=35)
    db.commit()

    called = []
    with patch(
        "app.tasks.analytics_tasks._fetch_vk_metrics",
        side_effect=lambda *a, **k: called.append(True) or {},
    ):
        _collect_metrics_for_post(pp.id, db)

    assert called == []  # should bail out early for old posts
