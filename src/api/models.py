"""SQLAlchemy ORM models for PostgreSQL user + character storage."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    characters: Mapped[list[Character]] = relationship(
        "Character", back_populates="user", cascade="all, delete-orphan"
    )
    gm_campaigns: Mapped[list[Campaign]] = relationship(
        "Campaign", back_populates="gm", cascade="all, delete-orphan"
    )
    campaign_memberships: Mapped[list[CampaignMember]] = relationship(
        "CampaignMember", back_populates="user", cascade="all, delete-orphan"
    )


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="characters")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gm_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gm: Mapped[User] = relationship("User", back_populates="gm_campaigns")
    members: Mapped[list[CampaignMember]] = relationship(
        "CampaignMember", back_populates="campaign", cascade="all, delete-orphan"
    )
    allowed_sources: Mapped[list[CampaignSource]] = relationship(
        "CampaignSource", back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    __table_args__ = (
        UniqueConstraint("campaign_id", "user_id", name="uq_campaign_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="player")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="campaign_memberships")


class CampaignSource(Base):
    __tablename__ = "campaign_sources"
    __table_args__ = (
        UniqueConstraint("campaign_id", "source_id", name="uq_campaign_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="allowed_sources")
