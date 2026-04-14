from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import Draft, DraftVersion, DraftStatus

router = APIRouter(prefix="/drafts", tags=["drafts"])


class GenerateRequest(BaseModel):
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    source_asset_id: Optional[int] = None


class DraftUpdateRequest(BaseModel):
    text: Optional[str] = None
    hashtags: Optional[list[str]] = None


class DraftOut(BaseModel):
    id: int
    brand_id: int
    network: str
    format: str
    funnel_stage: str
    status: str
    text: Optional[str]
    hashtags: list
    media_keys: list

    class Config:
        from_attributes = True


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_draft(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.tasks.draft_tasks import generate_draft as task
    task.delay(
        brand_id=body.brand_id,
        network=body.network,
        format=body.format,
        funnel_stage=body.funnel_stage,
        source_asset_id=body.source_asset_id,
    )
    return {"status": "queued"}


@router.get("/", response_model=list[DraftOut])
def list_drafts(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Draft).filter(Draft.brand_id == brand_id).all()


@router.get("/{draft_id}", response_model=DraftOut)
def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/{draft_id}", response_model=DraftOut)
def update_draft(
    draft_id: int,
    body: DraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in (DraftStatus.draft, DraftStatus.rejected):
        raise HTTPException(status_code=400, detail="Can only edit drafts in draft/rejected status")

    version_count = db.query(DraftVersion).filter(DraftVersion.draft_id == draft_id).count()
    version = DraftVersion(
        draft_id=draft_id,
        version=version_count + 1,
        text=draft.text,
        media_keys=draft.media_keys,
    )
    db.add(version)

    if body.text is not None:
        draft.text = body.text
    if body.hashtags is not None:
        draft.hashtags = body.hashtags
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/submit", response_model=DraftOut)
def submit_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status not in (DraftStatus.draft, DraftStatus.rejected):
        raise HTTPException(status_code=400, detail="Can only submit draft/rejected drafts")
    draft.status = DraftStatus.needs_review
    db.commit()
    db.refresh(draft)
    return draft


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = db.get(Draft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = DraftStatus.archived
    db.commit()
