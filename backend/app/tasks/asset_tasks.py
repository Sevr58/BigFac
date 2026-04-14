from app.worker import celery_app


@celery_app.task(name="process_asset")
def process_asset(asset_id: int):
    """Transcribe + scene detect + extract atoms. Full implementation in Task 6."""
    pass
