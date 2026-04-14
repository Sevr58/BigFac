import pytest
from unittest.mock import patch, MagicMock


def _create_brand(db):
    from app.models.workspace import Workspace
    from app.models.brand import Brand
    ws = Workspace(name="Test WS")
    db.add(ws)
    db.flush()
    brand = Brand(
        workspace_id=ws.id,
        name="Test Brand",
        company_type="product",
        description="desc",
        target_audience="all",
        goals=[],
        tone_of_voice="friendly",
        posting_frequency="daily",
    )
    db.add(brand)
    db.flush()
    return brand


def test_process_asset_runs(db):
    from app.models.content import SourceAsset, AssetType, AssetStatus
    brand = _create_brand(db)

    asset = SourceAsset(
        brand_id=brand.id,
        name="test.mp4",
        asset_type=AssetType.video,
        status=AssetStatus.processing,
        storage_key="brands/1/assets/test.mp4",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    with patch("app.tasks.asset_tasks.storage.read", return_value=b"fake_video_data"), \
         patch("app.tasks.asset_tasks._transcribe", return_value="Hello world this is a test"), \
         patch("app.tasks.asset_tasks._detect_scenes", return_value=[]), \
         patch("app.tasks.asset_tasks._extract_atoms", return_value=[
             {"type": "hook", "content": "Hello world"},
             {"type": "key_point", "content": "This is a test"},
         ]):
        from app.tasks.asset_tasks import _process_asset_sync
        _process_asset_sync(asset.id, db)

    db.refresh(asset)
    assert asset.status == AssetStatus.ready
    assert asset.transcription == "Hello world this is a test"

    from app.models.content import ContentAtom
    atoms = db.query(ContentAtom).filter(ContentAtom.source_asset_id == asset.id).all()
    assert len(atoms) == 2
    assert atoms[0].atom_type == "hook"
