import enum
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class FunnelStage(str, enum.Enum):
    tofu = "tofu"
    mofu = "mofu"
    bofu = "bofu"
    retention = "retention"

class ContentPillar(Base):
    __tablename__ = "content_pillars"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    funnel_stages: Mapped[str] = mapped_column(String(255), nullable=False)  # comma-separated
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="pillars")

class ContentPlanItem(Base):
    __tablename__ = "content_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    pillar_id: Mapped[int] = mapped_column(ForeignKey("content_pillars.id"), nullable=True)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False)
    funnel_stage: Mapped[FunnelStage] = mapped_column(Enum(FunnelStage), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="plan_items")
    pillar: Mapped["ContentPillar"] = relationship()
