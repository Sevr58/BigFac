import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AssetType(str, enum.Enum):
    video = "video"
    audio = "audio"
    image = "image"
    text = "text"


class AssetStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class AtomType(str, enum.Enum):
    hook = "hook"
    key_point = "key_point"
    quote = "quote"
    cta = "cta"
    story = "story"
    clip = "clip"


class DraftStatus(str, enum.Enum):
    draft = "draft"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    archived = "archived"


class HumanTaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class SourceAsset(Base):
    __tablename__ = "source_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.uploaded)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    transcription: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="assets")
    atoms: Mapped[list["ContentAtom"]] = relationship(back_populates="source_asset")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="source_asset")


class ContentAtom(Base):
    __tablename__ = "content_atoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    atom_type: Mapped[AtomType] = mapped_column(Enum(AtomType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    clip_start: Mapped[float] = mapped_column(nullable=True)
    clip_end: Mapped[float] = mapped_column(nullable=True)
    clip_key: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_asset: Mapped["SourceAsset"] = relationship(back_populates="atoms")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    source_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=True)
    plan_item_id: Mapped[int] = mapped_column(ForeignKey("content_plan_items.id"), nullable=True)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False)
    funnel_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.draft)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    media_keys: Mapped[list] = mapped_column(JSON, default=list)
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="drafts")
    source_asset: Mapped["SourceAsset"] = relationship(back_populates="drafts")
    versions: Mapped[list["DraftVersion"]] = relationship(back_populates="draft")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="draft")


class DraftVersion(Base):
    __tablename__ = "draft_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    media_keys: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    draft: Mapped["Draft"] = relationship(back_populates="versions")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    draft: Mapped["Draft"] = relationship(back_populates="approval_requests")


class HumanTask(Base):
    __tablename__ = "human_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[HumanTaskStatus] = mapped_column(Enum(HumanTaskStatus), default=HumanTaskStatus.pending)
    result_asset_id: Mapped[int] = mapped_column(ForeignKey("source_assets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="human_tasks")
