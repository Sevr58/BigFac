import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class NetworkType(str, enum.Enum):
    instagram = "instagram"
    vk = "vk"
    telegram = "telegram"

class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    goals: Mapped[list] = mapped_column(JSON, default=list)
    tone_of_voice: Mapped[str] = mapped_column(String(100), nullable=False)
    posting_frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="brand")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="brand")
    pillars: Mapped[list["ContentPillar"]] = relationship(back_populates="brand")
    plan_items: Mapped[list["ContentPlanItem"]] = relationship(back_populates="brand")

class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    network: Mapped[NetworkType] = mapped_column(Enum(NetworkType), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)

    brand: Mapped["Brand"] = relationship(back_populates="social_accounts")
