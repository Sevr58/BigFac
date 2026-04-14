from app.worker import celery_app


@celery_app.task(name="generate_draft")
def generate_draft(brand_id: int, network: str, format: str, funnel_stage: str,
                   source_asset_id=None, draft_id=None):
    """Research path or repurposing path draft generation. Full implementation in Task 8."""
    pass
