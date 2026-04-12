from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserRole
from app.schemas.brand import BrandCreate, BrandUpdate, BrandOut
from app.services.brand_service import create_brand, get_brand, update_brand
from app.core.dependencies import require_role

router = APIRouter()

@router.post("/workspaces/{workspace_id}/brand", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create(
    workspace_id: int,
    payload: BrandCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor))
):
    return create_brand(db, workspace_id, payload)

@router.get("/workspaces/{workspace_id}/brand", response_model=BrandOut)
def get(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor, UserRole.approver))
):
    return get_brand(db, workspace_id)

@router.patch("/workspaces/{workspace_id}/brand", response_model=BrandOut)
def update(
    workspace_id: int,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner, UserRole.editor))
):
    return update_brand(db, workspace_id, payload)
