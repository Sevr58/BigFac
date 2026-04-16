from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from app.worker import celery_app
from app.config import settings

logger = get_task_logger(__name__)

_METRICS_WINDOW_DAYS = 30


def _fetch_vk_metrics(network_post_id: str, credentials: dict) -> dict:
    import httpx
    try:
        owner_id = credentials.get("owner_id", "")
        token = credentials.get("access_token", "")
        resp = httpx.get(
            "https://api.vk.com/method/wall.getById",
            params={
                "posts": f"{owner_id}_{network_post_id}",
                "access_token": token,
                "v": "5.199",
            },
            timeout=30,
        )
        data = resp.json()
        if "response" in data and data["response"]:
            p = data["response"][0]
            return {
                "views": p.get("views", {}).get("count"),
                "likes": p.get("likes", {}).get("count"),
                "comments": p.get("comments", {}).get("count"),
                "shares": p.get("reposts", {}).get("count"),
            }
    except Exception as e:
        logger.warning("VK metrics fetch failed: %s", e)
    return {}


def _fetch_instagram_metrics(network_post_id: str, credentials: dict) -> dict:
    import httpx
    try:
        token = credentials.get("page_access_token", "")
        resp = httpx.get(
            f"https://graph.facebook.com/v19.0/{network_post_id}/insights",
            params={
                "metric": "reach,impressions,like_count,comments_count,shares,saved",
                "access_token": token,
            },
            timeout=30,
        )
        data = resp.json()
        result = {}
        for item in data.get("data", []):
            name = item["name"]
            value = item.get("values", [{}])[-1].get("value", 0)
            result[name] = value
        return {
            "reach": result.get("reach"),
            "views": result.get("impressions"),
            "likes": result.get("like_count"),
            "comments": result.get("comments_count"),
            "shares": result.get("shares"),
            "saves": result.get("saved"),
        }
    except Exception as e:
        logger.warning("Instagram metrics fetch failed: %s", e)
    return {}


def _fetch_telegram_metrics(network_post_id: str, credentials: dict) -> dict:
    # Telegram Bot API does not expose per-message analytics for channels.
    # Metrics require Telegram Analytics API (paid) or third-party tools.
    return {}


def _collect_metrics_for_post(published_post_id: int, db) -> None:
    from app.models.publishing import PublishedPost, PostMetrics
    from app.models.brand import SocialAccount

    pp = db.get(PublishedPost, published_post_id)
    if not pp or not pp.network_post_id:
        return

    cutoff = datetime.utcnow() - timedelta(days=_METRICS_WINDOW_DAYS)
    if pp.published_at < cutoff:
        return  # too old to collect

    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.brand_id == pp.brand_id,
            SocialAccount.network == pp.network,
            SocialAccount.enabled == True,
        )
        .first()
    )
    credentials = account.credentials if account else {}

    fetchers = {
        "vk": _fetch_vk_metrics,
        "instagram": _fetch_instagram_metrics,
        "telegram": _fetch_telegram_metrics,
    }
    fetch_fn = fetchers.get(pp.network)
    if not fetch_fn:
        return

    raw = fetch_fn(pp.network_post_id, credentials)
    if not raw:
        return  # nothing to record

    m = PostMetrics(
        published_post_id=pp.id,
        brand_id=pp.brand_id,
        reach=raw.get("reach"),
        views=raw.get("views"),
        likes=raw.get("likes"),
        comments=raw.get("comments"),
        shares=raw.get("shares"),
        saves=raw.get("saves"),
        clicks=raw.get("clicks"),
    )
    db.add(m)
    db.commit()


@celery_app.task(name="collect_all_metrics")
def collect_all_metrics():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.publishing import PublishedPost

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=_METRICS_WINDOW_DAYS)
        posts = (
            db.query(PublishedPost)
            .filter(
                PublishedPost.published_at >= cutoff,
                PublishedPost.network_post_id.isnot(None),
            )
            .all()
        )
        for pp in posts:
            try:
                _collect_metrics_for_post(pp.id, db)
            except Exception as e:
                logger.error(
                    "Failed to collect metrics for published_post_id=%s: %s", pp.id, e
                )
    finally:
        db.close()
