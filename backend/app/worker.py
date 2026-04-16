from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "scf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.asset_tasks",
        "app.tasks.draft_tasks",
        "app.tasks.publish_tasks",
        "app.tasks.analytics_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "schedule-pending-posts": {
        "task": "schedule_pending_posts",
        "schedule": 60.0,  # every 60 seconds
    },
    "collect-all-metrics": {
        "task": "collect_all_metrics",
        "schedule": crontab(hour=3, minute=0),  # daily at 03:00 Moscow time
    },
}
