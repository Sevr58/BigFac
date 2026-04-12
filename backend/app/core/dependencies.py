from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.database import get_db
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceMember
from app.core.security import decode_token

# Re-export get_db for consistent import path
__all__ = ["get_db", "get_current_user", "require_role"]

bearer = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    try:
        user_id = decode_token(credentials.credentials)
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles: UserRole):
    def dependency(
        workspace_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> WorkspaceMember:
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id
        ).first()
        if not member or member.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return member
    return dependency
