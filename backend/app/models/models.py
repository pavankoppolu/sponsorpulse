"""SQLAlchemy ORM models for SponsorPulse."""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum, Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class KanbanStage(str, enum.Enum):
    """Pipeline stages for outreach tracking."""
    DISCOVERED = "DISCOVERED"
    ENRICHED = "ENRICHED"
    DRAFTED = "DRAFTED"
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"


class OutreachPillar(str, enum.Enum):
    """Core outreach pillars for engagement."""
    CORPORATE = "CORPORATE"  # Companies for placements, internships & partnerships
    CAMPUS = "CAMPUS"        # Colleges to identify and recruit student talent
    COMMUNITY = "COMMUNITY"  # Communities to provide support & opportunities


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    funding_amount = Column(String(100), nullable=True)
    funding_date = Column(DateTime, nullable=True)
    source_url = Column(String(1024), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    outreaches = relationship("Outreach", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_companies_name_domain", "name", "domain"),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    title = Column(String(200), nullable=True)
    linkedin_url = Column(String(1024), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="contacts")
    outreaches = relationship("Outreach", back_populates="contact")


class Outreach(Base):
    __tablename__ = "outreaches"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    kanban_stage = Column(
        SAEnum(KanbanStage, values_callable=lambda e: [s.value for s in e]),
        default=KanbanStage.DISCOVERED,
        nullable=False,
    )
    pillar = Column(
        SAEnum(OutreachPillar, values_callable=lambda e: [s.value for s in e]),
        default=OutreachPillar.CORPORATE,
        nullable=False,
    )
    email_subject = Column(String(500), nullable=True)
    email_body = Column(Text, nullable=True)
    gmail_message_id = Column(String(255), nullable=True)
    gmail_thread_id = Column(String(255), nullable=True)
    last_reply_snippet = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    company = relationship("Company", back_populates="outreaches")
    contact = relationship("Contact", back_populates="outreaches")

