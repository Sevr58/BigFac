from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel as _BaseModel
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


class CredentialsUpdate(_BaseModel):
    credentials: dict


class SocialAccountOut(_BaseModel):
    id: int
    network: str
    handle: str | None
    enabled: bool

    class Config:
        from_attributes = True


@router.patch(
    "/workspaces/{workspace_id}/brand/social-accounts/{account_id}/credentials",
    response_model=SocialAccountOut,
)
def update_credentials(
    workspace_id: int,
    account_id: int,
    payload: CredentialsUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner)),
):
    from app.models.brand import SocialAccount
    account = db.get(SocialAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    account.credentials = payload.credentials
    db.commit()
    db.refresh(account)
    return account
