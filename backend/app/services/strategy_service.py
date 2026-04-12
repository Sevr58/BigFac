import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.models.brand import Brand
from app.models.strategy import ContentPillar, ContentPlanItem, FunnelStage
from app.services.brand_service import get_brand

_client_anthropic = None

def get_anthropic_client():
    global _client_anthropic
    if _client_anthropic is None:
        from anthropic import Anthropic
        _client_anthropic = Anthropic(api_key=settings.anthropic_api_key)
    return _client_anthropic

def call_claude(prompt: str) -> dict:
    """Call Claude API and parse JSON response."""
    message = get_anthropic_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text
    # Extract JSON from response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise HTTPException(status_code=502, detail="AI response did not contain JSON")
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI response parsing failed: {e}")

def build_strategy_prompt(brand: Brand) -> str:
    from datetime import date, timedelta
    today = date.today()
    # Start from next Monday
    days_until_monday = (7 - today.weekday()) % 7 or 7
    start = today + timedelta(days=days_until_monday)
    end = start + timedelta(weeks=4) - timedelta(days=1)

    networks = [a.network.value for a in brand.social_accounts if a.enabled]
    return f"""You are an expert social media strategist for Russian-market brands.

Brand: {brand.name}
Type: {brand.company_type}
Description: {brand.description}
Target audience: {brand.target_audience}
Goals: {', '.join(brand.goals)}
Tone of voice: {brand.tone_of_voice}
Posting frequency: {brand.posting_frequency}
Active networks: {', '.join(networks)}

Generate a content strategy in JSON format with this exact structure:
{{
  "pillars": [
    {{"title": "...", "description": "...", "funnel_stages": "tofu,mofu"}}
  ],
  "plan_items": [
    {{
      "network": "instagram",
      "format": "reels",
      "funnel_stage": "tofu",
      "topic": "...",
      "planned_date": "{start.isoformat()}",
      "pillar_index": 0
    }}
  ]
}}

Rules:
- Create 4-6 content pillars covering all funnel stages (tofu, mofu, bofu, retention)
- Create 28 plan items (4 weeks of content) distributed across selected networks
- Format must match network: instagram uses reels/carousel/static_post/story, vk uses clip/post/poll/long_video, telegram uses longread/voice/image_post/poll/link
- Balance funnel stages: ~40% tofu, 30% mofu, 20% bofu, 10% retention
- No more than 2 bofu posts per week
- All dates from {start.isoformat()} to {end.isoformat()}
- Respond ONLY with valid JSON, no explanation
"""

def generate_strategy(db: Session, workspace_id: int) -> dict:
    brand = get_brand(db, workspace_id)

    # Clear old strategy
    db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id).delete()
    db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).delete()
    db.commit()

    prompt = build_strategy_prompt(brand)
    data = call_claude(prompt)

    pillars = []
    for p in data["pillars"]:
        pillar = ContentPillar(
            brand_id=brand.id,
            title=p["title"],
            description=p["description"],
            funnel_stages=p["funnel_stages"]
        )
        db.add(pillar)
        pillars.append(pillar)
    db.flush()

    for item in data["plan_items"]:
        idx = item.get("pillar_index")
        pillar_id = pillars[idx].id if idx is not None and 0 <= idx < len(pillars) else None
        db.add(ContentPlanItem(
            brand_id=brand.id,
            pillar_id=pillar_id,
            network=item["network"],
            format=item["format"],
            funnel_stage=FunnelStage(item["funnel_stage"]),
            topic=item["topic"],
            planned_date=item["planned_date"]
        ))

    db.commit()

    pillars_out = db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).all()
    items_out = db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id).all()
    return {"pillars": pillars_out, "plan_items": items_out}
