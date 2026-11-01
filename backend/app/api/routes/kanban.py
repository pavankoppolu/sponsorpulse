"""Kanban API routes for SponsorPulse.

Handles the outreach pipeline board view, stage transitions, and pipeline metrics.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import KanbanStage, Outreach

router = APIRouter()


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class KanbanCardContact(BaseModel):
    id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None

    model_config = {"from_attributes": True}


class KanbanCard(BaseModel):
    id: int
    company_id: int
    company_name: str
    company_domain: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_badge: Optional[str] = None
    funding_date: Optional[datetime] = None
    contact_id: Optional[int] = None
    contact: Optional[KanbanCardContact] = None
    kanban_stage: str
    pillar: Optional[str] = "CORPORATE"
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    last_reply_snippet: Optional[str] = None
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MoveStageRequest(BaseModel):
    stage: str = Field(..., description="Target Kanban stage (e.g., 'ENRICHED', 'DRAFTED', etc.)")


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def _build_kanban_card(outreach: Outreach) -> KanbanCard:
    company = outreach.company
    contact = outreach.contact

    contact_info = None
    if contact:
        full_name = f"{contact.first_name} {contact.last_name}".strip()
        contact_info = KanbanCardContact(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            name=full_name or None,
            email=contact.email,
            title=contact.title,
            linkedin_url=contact.linkedin_url,
        )

    funding_val = company.funding_amount if company else None
    stage_val = (
        outreach.kanban_stage.value
        if hasattr(outreach.kanban_stage, "value")
        else str(outreach.kanban_stage)
    )

    return KanbanCard(
        id=outreach.id,
        company_id=outreach.company_id,
        company_name=company.name if company else "Unknown",
        company_domain=company.domain if company else None,
        funding_amount=funding_val,
        funding_badge=funding_val,
        funding_date=company.funding_date if company else None,
        contact_id=outreach.contact_id,
        contact=contact_info,
        kanban_stage=stage_val,
        pillar=outreach.pillar.value if hasattr(outreach, "pillar") and hasattr(outreach.pillar, "value") else str(getattr(outreach, "pillar", "CORPORATE")),
        email_subject=outreach.email_subject,
        email_body=outreach.email_body,
        gmail_message_id=outreach.gmail_message_id,
        gmail_thread_id=outreach.gmail_thread_id,
        last_reply_snippet=outreach.last_reply_snippet,
        sent_at=outreach.sent_at,
        updated_at=outreach.updated_at,
        created_at=company.created_at if company else None,
    )


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.get("/board", response_model=Dict[str, List[KanbanCard]])
def get_kanban_board(db: Session = Depends(get_db)):
    """Returns all outreaches grouped by kanban_stage in a structured board format."""
    board: Dict[str, List[KanbanCard]] = {stage.value: [] for stage in KanbanStage}

    outreaches = (
        db.query(Outreach)
        .order_by(Outreach.updated_at.desc(), Outreach.id.desc())
        .all()
    )

    for outreach in outreaches:
        card = _build_kanban_card(outreach)
        stage_key = card.kanban_stage
        if stage_key in board:
            board[stage_key].append(card)
        else:
            board.setdefault(stage_key, []).append(card)

    return board


@router.put("/move/{outreach_id}", response_model=KanbanCard)
def move_outreach_stage(outreach_id: int, payload: MoveStageRequest, db: Session = Depends(get_db)):
    """Moves an outreach to a new stage, validating stage transition rules."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")

    target_stage_str = payload.stage.strip().upper()
    valid_stages = {s.value: s for s in KanbanStage}

    if target_stage_str not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{payload.stage}'. Must be one of: {list(valid_stages.keys())}"
        )

    target_stage = valid_stages[target_stage_str]

    # Stage transition validations
    if target_stage == KanbanStage.SENT:
        if not outreach.contact or not outreach.contact.email:
            raise HTTPException(
                status_code=400,
                detail="Cannot move to SENT: outreach has no contact with an email address."
            )
        if not outreach.email_subject or not outreach.email_body:
            raise HTTPException(
                status_code=400,
                detail="Cannot move to SENT: email subject and body are required."
            )

    outreach.kanban_stage = target_stage
    outreach.updated_at = datetime.now(timezone.utc)
    if target_stage == KanbanStage.SENT and not outreach.sent_at:
        outreach.sent_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(outreach)

    return _build_kanban_card(outreach)


@router.get("/stats", response_model=Dict[str, int])
def get_kanban_stats(db: Session = Depends(get_db)):
    """Returns count of outreaches per stage and total pipeline count."""
    stats = {stage.value: 0 for stage in KanbanStage}

    counts = (
        db.query(Outreach.kanban_stage, func.count(Outreach.id))
        .group_by(Outreach.kanban_stage)
        .all()
    )

    total = 0
    for stage, count in counts:
        stage_key = stage.value if hasattr(stage, "value") else str(stage)
        stats[stage_key] = count
        total += count

    stats["total"] = total
    return stats
