from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.publishing import PublishedPost, PostMetrics, LeadEvent
from app.models.brand import Brand

router = APIRouter(prefix="/analytics", tags=["analytics"])


class LeadEventCreate(BaseModel):
    brand_id: int
    published_post_id: Optional[int] = None
    event_type: str = "lead"
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None


class LeadEventOut(BaseModel):
    id: int
    brand_id: int
    published_post_id: Optional[int]
    event_type: str
    utm_source: Optional[str]
    utm_medium: Optional[str]
    utm_campaign: Optional[str]
    utm_content: Optional[str]

    class Config:
        from_attributes = True


def _call_claude_feedback(prompt: str) -> str:
    from anthropic import Anthropic
    from app.config import settings
    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _build_feedback_prompt(brand: Brand, summary: dict) -> str:
    by_network = "\n".join(
        f"  {net}: {vals['total_posts']} posts, {vals.get('views', 0)} views, "
        f"{vals.get('likes', 0)} likes, {vals.get('shares', 0)} shares"
        for net, vals in summary.get("by_network", {}).items()
    )
    by_format = "\n".join(
        f"  {fmt}: {vals.get('views', 0)} avg views"
        for fmt, vals in summary.get("by_format", {}).items()
    )
    by_funnel = "\n".join(
        f"  {stage}: {vals['total_posts']} posts"
        for stage, vals in summary.get("by_funnel", {}).items()
    )
    return f"""Вы — стратег по контенту в социальных сетях. Проанализируйте результаты за последние 30 дней.

Бренд: {brand.name}
Описание: {brand.description}
Цели: {", ".join(brand.goals)}

Результаты:
По сетям:
{by_network}

По форматам:
{by_format}

По воронке:
{by_funnel}

Всего постов: {summary.get("total_posts", 0)}
Всего просмотров: {summary.get("total_views", 0)}
Всего лидов: {summary.get("total_leads", 0)}

На основе этих данных дайте 3–5 конкретных рекомендаций для контент-плана на следующую неделю.
Будьте конкретны: какие форматы и сети приоритизировать, какой тип контента создавать больше или меньше.
Ответьте только рекомендациями, без вводных слов."""


def _build_summary(brand_id: int, db: Session) -> dict:
    posts = (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .all()
    )
    if not posts:
        return {"total_posts": 0, "total_views": 0, "total_leads": 0,
                "by_network": {}, "by_format": {}, "by_funnel": {}}

    post_ids = [p.id for p in posts]
    metrics = db.query(PostMetrics).filter(PostMetrics.published_post_id.in_(post_ids)).all()
    metrics_by_post = {m.published_post_id: m for m in metrics}

    from app.models.content import Draft
    draft_ids = [p.draft_id for p in posts]
    drafts = db.query(Draft).filter(Draft.id.in_(draft_ids)).all()
    drafts_by_id = {d.id: d for d in drafts}

    by_network: dict = {}
    by_format: dict = {}
    by_funnel: dict = {}
    total_views = 0

    for pp in posts:
        net = pp.network
        m = metrics_by_post.get(pp.id)
        draft = drafts_by_id.get(pp.draft_id)
        views = m.views or 0 if m else 0
        likes = m.likes or 0 if m else 0
        shares = m.shares or 0 if m else 0
        total_views += views

        if net not in by_network:
            by_network[net] = {"total_posts": 0, "views": 0, "likes": 0, "shares": 0}
        by_network[net]["total_posts"] += 1
        by_network[net]["views"] += views
        by_network[net]["likes"] += likes
        by_network[net]["shares"] += shares

        if draft:
            fmt = draft.format
            if fmt not in by_format:
                by_format[fmt] = {"total_posts": 0, "views": 0}
            by_format[fmt]["total_posts"] += 1
            by_format[fmt]["views"] += views

            stage = draft.funnel_stage
            if stage not in by_funnel:
                by_funnel[stage] = {"total_posts": 0}
            by_funnel[stage]["total_posts"] += 1

    total_leads = db.query(LeadEvent).filter(LeadEvent.brand_id == brand_id).count()

    return {
        "total_posts": len(posts),
        "total_views": total_views,
        "total_leads": total_leads,
        "by_network": by_network,
        "by_format": by_format,
        "by_funnel": by_funnel,
    }


@router.get("/summary")
def analytics_summary(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _build_summary(brand_id, db)


@router.get("/posts")
def post_analytics(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    posts = (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .order_by(PublishedPost.published_at.desc())
        .limit(100)
        .all()
    )
    post_ids = [p.id for p in posts]
    metrics = db.query(PostMetrics).filter(PostMetrics.published_post_id.in_(post_ids)).all()
    metrics_map = {m.published_post_id: m for m in metrics}

    result = []
    for pp in posts:
        m = metrics_map.get(pp.id)
        result.append({
            "id": pp.id,
            "draft_id": pp.draft_id,
            "network": pp.network,
            "network_post_id": pp.network_post_id,
            "published_at": pp.published_at.isoformat(),
            "utm_params": pp.utm_params,
            "metrics": {
                "views": m.views if m else None,
                "likes": m.likes if m else None,
                "comments": m.comments if m else None,
                "shares": m.shares if m else None,
                "reach": m.reach if m else None,
                "saves": m.saves if m else None,
                "clicks": m.clicks if m else None,
            } if m else None,
        })
    return result


@router.post("/leads", response_model=LeadEventOut, status_code=http_status.HTTP_201_CREATED)
def record_lead(
    body: LeadEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = LeadEvent(
        brand_id=body.brand_id,
        published_post_id=body.published_post_id,
        event_type=body.event_type,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/feedback-loop")
def run_feedback_loop(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    summary = _build_summary(brand_id, db)
    prompt = _build_feedback_prompt(brand, summary)
    suggestion = _call_claude_feedback(prompt)
    return {"brand_id": brand_id, "suggestion": suggestion}
