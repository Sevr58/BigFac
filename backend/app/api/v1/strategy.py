from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserRole
from app.schemas.strategy import PillarOut, ContentPlanItemOut, StrategyOut
from app.services.strategy_service import generate_strategy
from app.services.brand_service import get_brand
from app.models.strategy import ContentPillar, ContentPlanItem
from app.core.dependencies import require_role

router = APIRouter()

@router.post("/workspaces/{workspace_id}/generate", response_model=StrategyOut)
def generate(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner))
):
    return generate_strategy(db, workspace_id)

@router.get("/workspaces/{workspace_id}/pillars", response_model=list[PillarOut])
def get_pillars(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    brand = get_brand(db, workspace_id)
    return db.query(ContentPillar).filter(ContentPillar.brand_id == brand.id).all()

@router.get("/workspaces/{workspace_id}/plan", response_model=list[ContentPlanItemOut])
def get_plan(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    brand = get_brand(db, workspace_id)
    return db.query(ContentPlanItem).filter(ContentPlanItem.brand_id == brand.id)\
        .order_by(ContentPlanItem.planned_date).all()
