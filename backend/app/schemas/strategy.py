from pydantic import BaseModel
from datetime import date
from app.models.strategy import FunnelStage

class PillarOut(BaseModel):
    id: int
    title: str
    description: str
    funnel_stages: str
    model_config = {"from_attributes": True}

class ContentPlanItemOut(BaseModel):
    id: int
    network: str
    format: str
    funnel_stage: FunnelStage
    topic: str
    planned_date: date
    model_config = {"from_attributes": True}

class StrategyOut(BaseModel):
    pillars: list[PillarOut]
    plan_items: list[ContentPlanItemOut]
