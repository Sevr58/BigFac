from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, UserRole

def create_workspace(db: Session, name: str, owner_id: int) -> tuple[Workspace, WorkspaceMember]:
    workspace = Workspace(name=name)
    db.add(workspace)
    db.flush()
    member = WorkspaceMember(workspace_id=workspace.id, user_id=owner_id, role=UserRole.owner)
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace, member

def list_workspaces(db: Session, user_id: int) -> list[tuple[Workspace, WorkspaceMember]]:
    members = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()
    return [(m.workspace, m) for m in members]

def add_member(db: Session, workspace_id: int, email: str, role: UserRole) -> WorkspaceMember:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already a member")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
