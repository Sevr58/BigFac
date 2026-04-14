from celery import Celery
from app.config import settings

celery_app = Celery(
    "scf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.asset_tasks",
        "app.tasks.draft_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    task_track_started=True,
)
