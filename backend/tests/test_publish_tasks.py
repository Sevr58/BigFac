from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.models.content import Draft, DraftStatus
from app.models.publishing import PublishedPost


def _make_draft(db, status=DraftStatus.scheduled) -> Draft:
    from app.models.brand import Brand, SocialAccount, NetworkType
    from app.models.workspace import Workspace
    from app.models.user import User

    user = User(email="u@test.com", hashed_password="x", full_name="U")
    db.add(user)
    db.flush()
    ws = Workspace(name="WS")
    db.add(ws)
    db.flush()
    brand = Brand(
        workspace_id=ws.id,
        name="Brand",
        company_type="smb",
        description="desc",
        target_audience="all",
        goals=[],
        tone_of_voice="neutral",
        posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    account = SocialAccount(
        brand_id=brand.id,
        network=NetworkType.telegram,
        handle="@test",
        enabled=True,
        credentials={"bot_token": "TOKEN", "chat_id": "-100123"},
    )
    db.add(account)
    draft = Draft(
        brand_id=brand.id,
        network="telegram",
        format="post",
        funnel_stage="tofu",
        status=status,
        text="Test post content",
        scheduled_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def test_publish_draft_sync_success(db):
    from app.tasks.publish_tasks import _publish_draft_sync
    from app.services.publishers.base import PublishResult

    draft = _make_draft(db)
    draft.status = DraftStatus.publishing
    db.commit()

    with patch(
        "app.services.publishers.telegram.TelegramPublisher.publish",
        return_value=PublishResult(success=True, network_post_id="777"),
    ):
        _publish_draft_sync(draft.id, db)

    db.refresh(draft)
    assert draft.status == DraftStatus.published
    pp = db.query(PublishedPost).filter(PublishedPost.draft_id == draft.id).first()
    assert pp is not None
    assert pp.network_post_id == "777"
    assert pp.error is None


def test_publish_draft_sync_failure(db):
    from app.tasks.publish_tasks import _publish_draft_sync
    from app.services.publishers.base import PublishResult

    draft = _make_draft(db)
    draft.status = DraftStatus.publishing
    db.commit()

    with patch(
        "app.services.publishers.telegram.TelegramPublisher.publish",
        return_value=PublishResult(success=False, error="bot blocked"),
    ):
        _publish_draft_sync(draft.id, db)

    db.refresh(draft)
    assert draft.status == DraftStatus.failed
    pp = db.query(PublishedPost).filter(PublishedPost.draft_id == draft.id).first()
    assert pp.error == "bot blocked"


def test_publish_draft_sync_skips_wrong_status(db):
    from app.tasks.publish_tasks import _publish_draft_sync

    draft = _make_draft(db, status=DraftStatus.approved)  # NOT publishing
    _publish_draft_sync(draft.id, db)
    db.refresh(draft)
    assert draft.status == DraftStatus.approved  # unchanged


def test_schedule_pending_posts_enqueues_due_draft(db):
    from app.tasks.publish_tasks import _schedule_pending_posts_sync, publish_post

    draft = _make_draft(db)  # scheduled, scheduled_at in the past

    with patch.object(publish_post, "delay") as mock_delay:
        _schedule_pending_posts_sync(db)

    mock_delay.assert_called_once_with(draft.id)
