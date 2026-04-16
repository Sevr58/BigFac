from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftStatus
from app.models.publishing import PublishedPost

router = APIRouter(prefix="/publishing", tags=["publishing"])


class ScheduleRequest(BaseModel):
    draft_id: int
    scheduled_at: datetime


class DraftQueueOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]
    scheduled_at: Optional[datetime]

    class Config:
        from_attributes = True


class PublishedPostOut(BaseModel):
    id: int
    draft_id: int
    brand_id: int
    network: str
    network_post_id: Optional[str]
    utm_params: dict
    error: Optional[str]
    published_at: datetime

    class Config:
        from_attributes = True


@router.post("/schedule", response_model=DraftQueueOut)
def schedule_draft(
    body: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, body.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved drafts can be scheduled")
    draft.status = DraftStatus.scheduled
    draft.scheduled_at = body.scheduled_at
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/cancel/{draft_id}", response_model=DraftQueueOut)
def cancel_scheduled(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.scheduled:
        raise HTTPException(status_code=400, detail="Draft is not scheduled")
    draft.status = DraftStatus.approved
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/queue", response_model=list[DraftQueueOut])
def publishing_queue(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(Draft)
        .filter(
            Draft.brand_id == brand_id,
            Draft.status.in_([DraftStatus.approved, DraftStatus.scheduled, DraftStatus.publishing]),
        )
        .order_by(Draft.scheduled_at.asc().nullslast())
        .all()
    )


@router.get("/log", response_model=list[PublishedPostOut])
def publishing_log(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(PublishedPost)
        .filter(PublishedPost.brand_id == brand_id)
        .order_by(PublishedPost.published_at.desc())
        .limit(100)
        .all()
    )
