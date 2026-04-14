from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.content import HumanTask, HumanTaskStatus

router = APIRouter(prefix="/human-tasks", tags=["human-tasks"])


class HumanTaskCreate(BaseModel):
    brand_id: int
    title: str
    description: Optional[str] = None
    draft_id: Optional[int] = None


class HumanTaskComplete(BaseModel):
    result_asset_id: Optional[int] = None


class HumanTaskOut(BaseModel):
    id: int
    brand_id: int
    title: str
    description: Optional[str]
    status: str
    result_asset_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/", response_model=HumanTaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    body: HumanTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = HumanTask(
        brand_id=body.brand_id,
        draft_id=body.draft_id,
        title=body.title,
        description=body.description,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[HumanTaskOut])
def list_tasks(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(HumanTask).filter(HumanTask.brand_id == brand_id).all()


@router.patch("/{task_id}/complete", response_model=HumanTaskOut)
def complete_task(
    task_id: int,
    body: HumanTaskComplete,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.get(HumanTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = HumanTaskStatus.completed
    task.completed_at = datetime.utcnow()
    if body.result_asset_id:
        task.result_asset_id = body.result_asset_id
    db.commit()
    db.refresh(task)
    return task
