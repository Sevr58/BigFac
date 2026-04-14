try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from app.worker import celery_app
from app.config import settings


def _research_context(topic: str, brand_description: str) -> str:
    """Fetch relevant context via Tavily search."""
    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        results = client.search(
            query=f"{topic} {brand_description}",
            search_depth="basic",
            max_results=3,
        )
        snippets = [r["content"] for r in results.get("results", [])]
        return "\n".join(snippets)
    except Exception:
        return ""


def _build_research_prompt(brand, network: str, format: str, funnel_stage: str, context: str) -> str:
    return f"""You are a social media content writer for a brand.

Brand: {brand.name}
Description: {brand.description}
Target audience: {brand.target_audience}
Tone of voice: {brand.tone_of_voice}
Network: {network}
Format: {format}
Funnel stage: {funnel_stage} (tofu=awareness, mofu=consideration, bofu=conversion, retention=loyalty)

Relevant context from web research:
{context}

Write one post for {network} in {format} format. Match tone of voice. Include relevant hashtags.
Write in Russian. Return only the post text, no explanations."""


def _build_repurposing_prompt(brand, network: str, format: str, funnel_stage: str, atoms: list) -> str:
    atom_texts = "\n".join([f"- [{a.atom_type}]: {a.content}" for a in atoms])
    return f"""You are a social media content writer repurposing source material.

Brand: {brand.name}
Description: {brand.description}
Target audience: {brand.target_audience}
Tone of voice: {brand.tone_of_voice}
Network: {network}
Format: {format}
Funnel stage: {funnel_stage}

Content atoms extracted from source video/audio:
{atom_texts}

Using the atoms above, write one post for {network} in {format} format.
Match tone of voice. Include hashtags. Write in Russian.
Return only the post text."""


def _call_claude(prompt: str) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _generate_draft_sync(brand_id: int, network: str, format: str, funnel_stage: str,
                          source_asset_id, db):
    from app.models.brand import Brand
    from app.models.content import ContentAtom, Draft, DraftStatus

    brand = db.get(Brand, brand_id)
    if not brand:
        return

    if source_asset_id:
        # Repurposing path
        atoms = db.query(ContentAtom).filter(
            ContentAtom.source_asset_id == source_asset_id
        ).limit(10).all()
        prompt = _build_repurposing_prompt(brand, network, format, funnel_stage, atoms)
    else:
        # Research path
        topic = f"{brand.description} {funnel_stage} content for {network}"
        context = _research_context(topic, brand.description)
        prompt = _build_research_prompt(brand, network, format, funnel_stage, context)

    text = _call_claude(prompt)

    draft = Draft(
        brand_id=brand_id,
        source_asset_id=source_asset_id,
        network=network,
        format=format,
        funnel_stage=funnel_stage,
        status=DraftStatus.draft,
        text=text,
    )
    db.add(draft)
    db.commit()


@celery_app.task(name="generate_draft")
def generate_draft(brand_id: int, network: str, format: str, funnel_stage: str,
                   source_asset_id=None, draft_id=None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        _generate_draft_sync(brand_id, network, format, funnel_stage, source_asset_id, db)
    finally:
        db.close()
