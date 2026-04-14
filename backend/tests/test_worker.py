def test_celery_app_importable():
    from app.worker import celery_app
    assert celery_app.main == "scf"
