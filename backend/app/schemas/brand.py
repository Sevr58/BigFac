from pydantic import BaseModel
from app.models.brand import NetworkType

class NetworkOut(BaseModel):
    id: int
    network: NetworkType
    handle: str | None
    enabled: bool
    model_config = {"from_attributes": True}

class BrandCreate(BaseModel):
    name: str
    company_type: str
    description: str
    target_audience: str
    goals: list[str]
    tone_of_voice: str
    posting_frequency: str
    networks: list[NetworkType]

class BrandUpdate(BaseModel):
    name: str | None = None
    company_type: str | None = None
    description: str | None = None
    target_audience: str | None = None
    goals: list[str] | None = None
    tone_of_voice: str | None = None
    posting_frequency: str | None = None

class BrandOut(BaseModel):
    id: int
    name: str
    company_type: str
    description: str
    target_audience: str
    goals: list[str]
    tone_of_voice: str
    posting_frequency: str
    social_accounts: list[NetworkOut]
    model_config = {"from_attributes": True}
