import os
import tempfile
from app.worker import celery_app
from app.config import settings
from app.services.storage import storage


def _transcribe(audio_path: str) -> str:
    """Call OpenAI Whisper API on local file. Returns transcript text."""
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ru",
        )
    return result.text


def _detect_scenes(video_path: str) -> list[dict]:
    """Detect scene changes. Returns list of {start, end} in seconds."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
    except ImportError:
        return []

    video = open_video(video_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video)
    scene_list = manager.get_scene_list()
    return [
        {"start": s[0].get_seconds(), "end": s[1].get_seconds()}
        for s in scene_list
    ]


def _extract_clip(video_path: str, start: float, end: float, out_path: str) -> None:
    """Use ffmpeg-python to extract clip."""
    import ffmpeg
    (
        ffmpeg
        .input(video_path, ss=start, to=end)
        .output(out_path, c="copy")
        .overwrite_output()
        .run(quiet=True)
    )


def _extract_atoms(transcription: str, brand_id: int) -> list[dict]:
    """Call Claude to extract content atoms from transcription."""
    import json
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Extract content atoms from this transcription for social media reuse.
Return a JSON array of objects with fields: type (hook/key_point/quote/cta/story) and content.
Extract 5-10 atoms. Transcription:

{transcription}

Return only valid JSON array, no other text."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    return json.loads(text)


def _process_asset_sync(asset_id: int, db):
    from app.models.content import SourceAsset, ContentAtom, AssetStatus, AtomType

    asset = db.get(SourceAsset, asset_id)
    if not asset:
        return

    try:
        raw = storage.read(asset.storage_key)
        suffix = os.path.splitext(asset.name)[1] or ".mp4"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        transcription = ""
        scenes = []

        if asset.asset_type in ("video", "audio"):
            transcription = _transcribe(tmp_path)
            asset.transcription = transcription

        if asset.asset_type == "video":
            scenes = _detect_scenes(tmp_path)
            for i, scene in enumerate(scenes[:10]):
                clip_key = f"{asset.storage_key}_clip_{i}.mp4"
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as clip_tmp:
                    _extract_clip(tmp_path, scene["start"], scene["end"], clip_tmp.name)
                    with open(clip_tmp.name, "rb") as f:
                        storage.save(clip_key, f.read())
                    os.unlink(clip_tmp.name)

                atom = ContentAtom(
                    source_asset_id=asset.id,
                    brand_id=asset.brand_id,
                    atom_type=AtomType.clip,
                    content=f"Clip {i+1}: {scene['start']:.1f}s\u2013{scene['end']:.1f}s",
                    clip_start=scene["start"],
                    clip_end=scene["end"],
                    clip_key=clip_key,
                )
                db.add(atom)

        if transcription:
            atoms_data = _extract_atoms(transcription, asset.brand_id)
            for a in atoms_data:
                try:
                    atype = AtomType(a["type"])
                except ValueError:
                    atype = AtomType.key_point
                atom = ContentAtom(
                    source_asset_id=asset.id,
                    brand_id=asset.brand_id,
                    atom_type=atype,
                    content=a["content"],
                )
                db.add(atom)

        os.unlink(tmp_path)
        asset.status = AssetStatus.ready

    except Exception as e:
        asset.status = AssetStatus.failed
        asset.meta = {"error": str(e)}

    db.commit()


@celery_app.task(name="process_asset")
def process_asset(asset_id: int):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _process_asset_sync(asset_id, db)
    finally:
        db.close()
