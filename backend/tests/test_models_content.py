def test_content_models_importable():
    from app.models.content import (
        SourceAsset, ContentAtom, Draft, DraftVersion,
        ApprovalRequest, HumanTask, DraftStatus, AssetStatus
    )
    assert DraftStatus.draft == "draft"
    assert AssetStatus.ready == "ready"
