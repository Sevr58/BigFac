from celery.utils.log import get_task_logger
from app.worker import celery_app
from app.config import settings

logger = get_task_logger(__name__)


def _get_publisher(network: str, credentials: dict):
    from app.services.publishers.telegram import TelegramPublisher
    from app.services.publishers.vk import VKPublisher
    from app.services.publishers.instagram import InstagramPublisher

    if network == "telegram":
        return TelegramPublisher(
            bot_token=credentials.get("bot_token", ""),
            chat_id=credentials.get("chat_id", ""),
        )
    if network == "vk":
        return VKPublisher(
            access_token=credentials.get("access_token", ""),
            owner_id=credentials.get("owner_id", ""),
        )
    if network == "instagram":
        return InstagramPublisher(
            page_access_token=credentials.get("page_access_token", ""),
            instagram_account_id=credentials.get("instagram_account_id", ""),
        )
    raise ValueError(f"Unknown network: {network}")


def _publish_draft_sync(draft_id: int, db) -> None:
    from app.models.content import Draft, DraftStatus
    from app.models.publishing import PublishedPost
    from app.models.brand import Brand, SocialAccount
    from app.services.utm import build_utm_params

    draft = db.get(Draft, draft_id)
    if not draft or draft.status != DraftStatus.publishing:
        return

    brand = db.get(Brand, draft.brand_id)
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.brand_id == draft.brand_id,
            SocialAccount.network == draft.network,
            SocialAccount.enabled == True,
        )
        .first()
    )

    if not account:
        draft.status = DraftStatus.failed
        db.add(PublishedPost(
            draft_id=draft_id,
            brand_id=draft.brand_id,
            network=draft.network,
            error="No enabled social account found for this network",
            utm_params={},
        ))
        db.commit()
        return

    utm = build_utm_params(
        brand_name=brand.name if brand else "unknown",
        network=draft.network,
        format=draft.format,
        funnel_stage=draft.funnel_stage,
    )

    publisher = _get_publisher(draft.network, account.credentials)
    result = publisher.publish(
        text=draft.text or "",
        media_keys=draft.media_keys,
        utm_params=utm,
    )

    pp = PublishedPost(
        draft_id=draft_id,
        brand_id=draft.brand_id,
        network=draft.network,
        network_post_id=result.network_post_id if result.success else None,
        utm_params=utm,
        error=result.error if not result.success else None,
    )
    db.add(pp)
    draft.status = DraftStatus.published if result.success else DraftStatus.failed
    db.commit()


@celery_app.task(name="publish_post", bind=True, max_retries=3)
def publish_post(self, draft_id: int):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.content import Draft, DraftStatus

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        draft = db.get(Draft, draft_id)
        if not draft:
            return
        draft.status = DraftStatus.publishing
        db.commit()
        _publish_draft_sync(draft_id, db)
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            draft = db.get(Draft, draft_id)
            if draft:
                draft.status = DraftStatus.archived
                db.commit()
            logger.error("publish_post max retries exceeded for draft_id=%s", draft_id)
    finally:
        db.close()


def _schedule_pending_posts_sync(db) -> None:
    from datetime import datetime
    from app.models.content import Draft, DraftStatus

    now = datetime.utcnow()
    due_drafts = (
        db.query(Draft)
        .filter(Draft.status == DraftStatus.scheduled, Draft.scheduled_at <= now)
        .all()
    )
    for draft in due_drafts:
        publish_post.delay(draft.id)
        logger.info("Enqueued publish_post for draft_id=%s", draft.id)


@celery_app.task(name="schedule_pending_posts")
def schedule_pending_posts():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _schedule_pending_posts_sync(db)
    finally:
        db.close()
