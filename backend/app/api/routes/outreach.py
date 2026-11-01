"""Outreach API routes for SponsorPulse.

Handles cold email generation with Gemini, draft editing, sending via Gmail,
reply synchronization, and retrieval of outreach records.
"""

from datetime import datetime, timezone
import inspect
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Company, Contact, KanbanStage, Outreach

try:
    from app.services import gemini_service
except ImportError:
    gemini_service = None

try:
    from app.services import gmail_service
except ImportError:
    gmail_service = None


router = APIRouter()


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class CompanyBasicResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_date: Optional[datetime] = None
    source_url: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactBasicResponse(BaseModel):
    id: int
    company_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None

    model_config = {"from_attributes": True}


class OutreachResponse(BaseModel):
    id: int
    company_id: int
    contact_id: Optional[int] = None
    kanban_stage: str
    pillar: Optional[str] = "CORPORATE"
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    last_reply_snippet: Optional[str] = None
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company: Optional[CompanyBasicResponse] = None
    contact: Optional[ContactBasicResponse] = None

    model_config = {"from_attributes": True}


class GenerateEmailRequest(BaseModel):
    refinement_instructions: Optional[str] = Field(
        None,
        description="Optional human instructions to tailor the generated cold email"
    )


class UpdateDraftRequest(BaseModel):
    email_subject: Optional[str] = Field(None, description="Updated email subject")
    email_body: Optional[str] = Field(None, description="Updated email body content")


class SyncRepliesResponse(BaseModel):
    checked_count: int
    replied_count: int
    updated_outreach_ids: List[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.post("/generate-email/{outreach_id}", response_model=OutreachResponse)
async def generate_email(
    outreach_id: int,
    payload: Optional[GenerateEmailRequest] = None,
    db: Session = Depends(get_db),
):
    """Generates cold email draft using Gemini based on company and contact details, sets stage to DRAFTED."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")

    company = outreach.company
    contact = outreach.contact

    # If contact is not linked to outreach, attempt to link the first company contact
    if not contact and company and company.contacts:
        contact = company.contacts[0]
        outreach.contact = contact
        outreach.contact_id = contact.id

    if gemini_service is None or not hasattr(gemini_service, "generate_cold_email"):
        raise HTTPException(status_code=503, detail="Gemini service is not available")

    refinements = payload.refinement_instructions if payload else None

    try:
        res = gemini_service.generate_cold_email(
            company=company,
            contact=contact,
            outreach=outreach,
            refinement_instructions=refinements,
        )
        if inspect.isawaitable(res):
            res = await res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email with Gemini: {str(e)}")

    # Parse generated subject and body
    subject = ""
    body = ""
    if isinstance(res, dict):
        subject = res.get("subject") or res.get("email_subject") or ""
        body = res.get("body") or res.get("email_body") or ""
    elif isinstance(res, (tuple, list)) and len(res) >= 2:
        subject = str(res[0])
        body = str(res[1])
    elif hasattr(res, "subject") and hasattr(res, "body"):
        subject = getattr(res, "subject") or ""
        body = getattr(res, "body") or ""
    elif isinstance(res, str):
        body = res
        company_name = company.name if company else "Your Team"
        subject = f"Partnership & Collaboration Inquiry — {company_name}"

    outreach.email_subject = subject
    outreach.email_body = body
    outreach.kanban_stage = KanbanStage.DRAFTED
    outreach.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(outreach)
    return outreach


@router.put("/draft/{outreach_id}", response_model=OutreachResponse)
def update_draft(outreach_id: int, payload: UpdateDraftRequest, db: Session = Depends(get_db)):
    """Manually updates the email_subject and/or email_body of an outreach draft."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")

    if payload.email_subject is not None:
        outreach.email_subject = payload.email_subject
    if payload.email_body is not None:
        outreach.email_body = payload.email_body

    outreach.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/approve/{outreach_id}", response_model=OutreachResponse)
def approve_outreach(outreach_id: int, db: Session = Depends(get_db)):
    """Approves an outreach draft and advances its stage to READY_TO_SEND."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")

    outreach.kanban_stage = KanbanStage.READY_TO_SEND
    outreach.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/send/{outreach_id}", response_model=OutreachResponse)
async def send_outreach(outreach_id: int, db: Session = Depends(get_db)):
    """Sends the approved cold email via Gmail, records message/thread IDs, sets stage to SENT."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")

    contact = outreach.contact
    if not contact or not contact.email:
        raise HTTPException(
            status_code=400,
            detail="Cannot send email: this outreach has no associated contact with a valid email address."
        )

    if not outreach.email_subject or not outreach.email_body:
        raise HTTPException(
            status_code=400,
            detail="Cannot send email: email subject or body is missing. Generate or edit draft first."
        )

    if gmail_service is None or not hasattr(gmail_service, "send_email"):
        raise HTTPException(status_code=503, detail="Gmail service is not available")

    # Check if Gmail is authenticated before attempting dispatch
    if hasattr(gmail_service, "is_authenticated") and not gmail_service.is_authenticated():
        raise HTTPException(
            status_code=400,
            detail="Gmail account is not connected. Please click 'Connect Gmail' in the top header or use Instant Test Mode to send."
        )

    try:
        try:
            res = gmail_service.send_email(
                to_email=contact.email,
                subject=outreach.email_subject,
                body=outreach.email_body,
            )
        except TypeError:
            try:
                res = gmail_service.send_email(
                    contact.email,
                    outreach.email_subject,
                    outreach.email_body,
                )
            except TypeError:
                res = gmail_service.send_email(outreach)

        if inspect.isawaitable(res):
            res = await res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email via Gmail: {str(e)}")

    msg_id = None
    thread_id = None
    if isinstance(res, dict):
        msg_id = res.get("gmail_message_id") or res.get("message_id") or res.get("id")
        thread_id = res.get("gmail_thread_id") or res.get("thread_id") or res.get("threadId")
    elif hasattr(res, "id"):
        msg_id = getattr(res, "id", None)
        thread_id = getattr(res, "threadId", getattr(res, "thread_id", None))

    outreach.gmail_message_id = msg_id
    outreach.gmail_thread_id = thread_id
    outreach.kanban_stage = KanbanStage.SENT
    outreach.sent_at = datetime.now(timezone.utc)
    outreach.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/sync-replies", response_model=SyncRepliesResponse)
async def sync_replies(db: Session = Depends(get_db)):
    """Iterates all outreaches with stage=SENT and a gmail_thread_id, checks for replies and updates stage."""
    if gmail_service is None or not hasattr(gmail_service, "check_thread_replies"):
        raise HTTPException(status_code=503, detail="Gmail service is not available")

    sent_outreaches = db.query(Outreach).filter(
        Outreach.kanban_stage == KanbanStage.SENT,
        Outreach.gmail_thread_id.isnot(None),
    ).all()

    updated_ids: List[int] = []

    for outreach in sent_outreaches:
        try:
            reply_info = gmail_service.check_thread_replies(outreach.gmail_thread_id)
            if inspect.isawaitable(reply_info):
                reply_info = await reply_info

            has_reply = False
            snippet = None

            if isinstance(reply_info, bool):
                has_reply = reply_info
            elif isinstance(reply_info, dict):
                has_reply = bool(reply_info.get("has_reply") or reply_info.get("replied"))
                snippet = reply_info.get("snippet") or reply_info.get("last_reply_snippet")
            elif reply_info:
                has_reply = True
                snippet = str(reply_info)

            if has_reply:
                outreach.kanban_stage = KanbanStage.REPLIED
                if snippet:
                    outreach.last_reply_snippet = snippet
                outreach.updated_at = datetime.now(timezone.utc)
                updated_ids.append(outreach.id)
        except Exception:
            # Continue checking other outreaches if one check encounters an error
            continue

    if updated_ids:
        db.commit()

    return SyncRepliesResponse(
        checked_count=len(sent_outreaches),
        replied_count=len(updated_ids),
        updated_outreach_ids=updated_ids,
    )


@router.get("", response_model=List[OutreachResponse])
@router.get("/", response_model=List[OutreachResponse])
def list_outreaches(
    stage: Optional[KanbanStage] = Query(None, description="Filter outreaches by pipeline stage"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Limit for pagination"),
    db: Session = Depends(get_db),
):
    """List all outreaches with company and contact details, with optional stage filter."""
    query = db.query(Outreach)
    if stage:
        query = query.filter(Outreach.kanban_stage == stage)

    outreaches = (
        query.order_by(Outreach.updated_at.desc(), Outreach.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return outreaches


@router.get("/{outreach_id}", response_model=OutreachResponse)
def get_outreach(outreach_id: int, db: Session = Depends(get_db)):
    """Get single outreach by ID with full details."""
    outreach = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not outreach:
        raise HTTPException(status_code=404, detail=f"Outreach with ID {outreach_id} not found")
    return outreach
