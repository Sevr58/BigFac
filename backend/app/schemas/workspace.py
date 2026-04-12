from typing import Annotated
from pydantic import BaseModel, Field
from pydantic import StringConstraints
from app.models.user import UserRole

class WorkspaceCreate(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]

class WorkspaceOut(BaseModel):
    id: int
    name: str
    my_role: UserRole

    model_config = {"from_attributes": True}

class InviteMemberRequest(BaseModel):
    email: str
    role: UserRole

class MemberOut(BaseModel):
    id: int
    user_id: int
    role: UserRole
    full_name: str
    email: str

    model_config = {"from_attributes": True}
