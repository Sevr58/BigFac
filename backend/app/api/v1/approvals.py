from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftStatus, ApprovalRequest, ApprovalDecision

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionRequest(BaseModel):
    comment: Optional[str] = None


class DraftOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]

    class Config:
        from_attributes = True


@router.get("/queue", response_model=list[DraftOut])
def approval_queue(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Draft).filter(
        Draft.brand_id == brand_id,
        Draft.status == DraftStatus.needs_review,
    ).all()


@router.post("/{draft_id}/approve", response_model=DraftOut)
def approve_draft(
    draft_id: int,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.needs_review:
        raise HTTPException(status_code=400, detail="Draft is not in needs_review status")

    ar = ApprovalRequest(
        draft_id=draft_id,
        reviewer_id=current_user.id,
        decision=ApprovalDecision.approved,
        comment=body.comment,
        decided_at=datetime.utcnow(),
    )
    db.add(ar)
    draft.status = DraftStatus.approved
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/reject", response_model=DraftOut)
def reject_draft(
    draft_id: int,
    body: DecisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.needs_review:
        raise HTTPException(status_code=400, detail="Draft is not in needs_review status")

    ar = ApprovalRequest(
        draft_id=draft_id,
        reviewer_id=current_user.id,
        decision=ApprovalDecision.rejected,
        comment=body.comment,
        decided_at=datetime.utcnow(),
    )
    db.add(ar)
    draft.status = DraftStatus.rejected
    db.commit()
    db.refresh(draft)
    return draft
