from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, InviteMemberRequest, MemberOut
from app.services.workspace_service import create_workspace, list_workspaces, add_member
from app.core.dependencies import get_current_user, require_role

router = APIRouter()

@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create(payload: WorkspaceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, member = create_workspace(db, payload.name, current_user.id)
    return WorkspaceOut(id=workspace.id, name=workspace.name, my_role=member.role)

@router.get("/", response_model=list[WorkspaceOut])
def list_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pairs = list_workspaces(db, current_user.id)
    return [WorkspaceOut(id=ws.id, name=ws.name, my_role=m.role) for ws, m in pairs]

@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def invite(
    workspace_id: int,
    payload: InviteMemberRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_role(UserRole.owner))
):
    member = add_member(db, workspace_id, payload.email, payload.role)
    # Access user relationship while session is open to avoid lazy loading errors
    user = member.user
    return MemberOut(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        full_name=user.full_name,
        email=user.email
    )
