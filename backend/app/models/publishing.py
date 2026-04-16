from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    network_post_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm_params: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    draft: Mapped["Draft"] = relationship(back_populates="published_posts")
    brand: Mapped["Brand"] = relationship(back_populates="published_posts")
    metrics: Mapped[list["PostMetrics"]] = relationship(back_populates="published_post")
    lead_events: Mapped[list["LeadEvent"]] = relationship(back_populates="published_post")


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    published_post_id: Mapped[int] = mapped_column(ForeignKey("published_posts.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    reach: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    published_post: Mapped["PublishedPost"] = relationship(back_populates="metrics")
    brand: Mapped["Brand"] = relationship(back_populates="metrics")


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    published_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("published_posts.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), default="lead")
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand: Mapped["Brand"] = relationship(back_populates="lead_events")
    published_post: Mapped[Optional["PublishedPost"]] = relationship(
        back_populates="lead_events", foreign_keys=[published_post_id]
    )
