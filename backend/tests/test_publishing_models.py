def test_publishing_models_importable():
    from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
    assert PublishedPost.__tablename__ == "published_posts"
    assert PostMetrics.__tablename__ == "post_metrics"
    assert LeadEvent.__tablename__ == "lead_events"
