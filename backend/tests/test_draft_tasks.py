import pytest
from unittest.mock import patch, MagicMock


def test_generate_draft_research_path(db):
    from app.models.brand import Brand
    from app.models.workspace import Workspace
    ws = Workspace(name="TestWS")
    db.add(ws)
    db.commit()
    brand = Brand(
        workspace_id=ws.id,
        name="Test Brand",
        company_type="product",
        description="A great product",
        target_audience="SMB owners",
        goals=[],
        tone_of_voice="friendly",
        posting_frequency="daily",
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)

    mock_tavily = MagicMock()
    mock_tavily.search.return_value = {
        "results": [{"content": "Trending topic about AI tools for SMB"}]
    }
    mock_claude_msg = MagicMock()
    mock_claude_msg.content = [MagicMock(text="Post text about AI for SMB owners #smb #ai")]

    with patch("app.tasks.draft_tasks.TavilyClient", return_value=mock_tavily), \
         patch("app.tasks.draft_tasks.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_msg

        from app.tasks.draft_tasks import _generate_draft_sync
        _generate_draft_sync(
            brand_id=brand.id,
            network="instagram",
            format="carousel",
            funnel_stage="tofu",
            source_asset_id=None,
            db=db,
        )

    from app.models.content import Draft, DraftStatus
    drafts = db.query(Draft).filter(Draft.brand_id == brand.id).all()
    assert len(drafts) == 1
    assert drafts[0].status == DraftStatus.draft
    assert len(drafts[0].text) > 5


def test_generate_draft_repurposing_path(db):
    from app.models.brand import Brand
    from app.models.workspace import Workspace
    from app.models.content import SourceAsset, ContentAtom, AssetType, AssetStatus, AtomType

    ws = Workspace(name="WS2")
    db.add(ws)
    db.commit()
    brand = Brand(
        workspace_id=ws.id,
        name="B2", company_type="service",
        description="desc", target_audience="ta",
        goals=[], tone_of_voice="professional",
        posting_frequency="weekly",
    )
    db.add(brand)
    db.commit()

    asset = SourceAsset(
        brand_id=brand.id, name="video.mp4",
        asset_type=AssetType.video, status=AssetStatus.ready,
        storage_key="brands/1/video.mp4",
        transcription="Great product launch event",
    )
    db.add(asset)
    db.commit()

    atom = ContentAtom(
        source_asset_id=asset.id, brand_id=brand.id,
        atom_type=AtomType.hook,
        content="Great product launch happening right now!",
    )
    db.add(atom)
    db.commit()

    mock_claude_msg = MagicMock()
    mock_claude_msg.content = [MagicMock(text="Amazing launch carousel text! #launch #product")]

    with patch("app.tasks.draft_tasks.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_msg

        from app.tasks.draft_tasks import _generate_draft_sync
        _generate_draft_sync(
            brand_id=brand.id,
            network="vk",
            format="long_post",
            funnel_stage="mofu",
            source_asset_id=asset.id,
            db=db,
        )

    from app.models.content import Draft
    drafts = db.query(Draft).filter(Draft.brand_id == brand.id).all()
    assert len(drafts) == 1
    assert len(drafts[0].text) > 5
