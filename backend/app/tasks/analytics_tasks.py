from celery.utils.log import get_task_logger
from app.worker import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="collect_all_metrics")
def collect_all_metrics():
    """Placeholder: collect metrics from all social networks for all published posts."""
    logger.info("collect_all_metrics: not yet implemented")
