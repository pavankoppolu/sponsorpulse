"""Enrichment API routes for SponsorPulse.

Integrates with Enricho MCP to discover contacts and enrich company data.
"""

from datetime import datetime, timezone
import inspect
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Company, Contact, KanbanStage, Outreach

try:
    from app.services import mcp_enricho_service
except ImportError:
    mcp_enricho_service = None


router = APIRouter()


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class ContactResponse(BaseModel):
    id: int
    company_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None

    model_config = {"from_attributes": True}


class EnrichmentResultResponse(BaseModel):
    company_id: int
    company_name: str
    outreach_id: Optional[int] = None
    stage: str = KanbanStage.ENRICHED.value
    contacts_count: int = 0
    contacts: List[ContactResponse] = Field(default_factory=list)
    raw_data: Optional[Any] = None
    message: str = "Company enriched successfully"

    model_config = {"from_attributes": True}


class MCPStatusResponse(BaseModel):
    configured: bool
    api_key_present: bool
    server_url_set: bool
    server_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.post("/enrich/{company_id}", response_model=EnrichmentResultResponse)
async def enrich_company(company_id: int, db: Session = Depends(get_db)):
    """Enriches a company using Enricho MCP: creates Contact records, creates/updates Outreach, advances to ENRICHED."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")

    if mcp_enricho_service is None or not hasattr(mcp_enricho_service, "enrich_company"):
        raise HTTPException(status_code=503, detail="Enricho MCP service is not available")

    # Call enrich_company
    try:
        res = mcp_enricho_service.enrich_company(
            company_name=company.name,
            domain=company.domain,
            db=db,
        )
        if inspect.isawaitable(res):
            res = await res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment service failed: {str(e)}")

    # Extract contact data and optional company updates
    raw_contacts = []
    if isinstance(res, dict):
        raw_contacts = res.get("contacts") or []
        if res.get("summary") and not company.summary:
            company.summary = res.get("summary")
        if res.get("domain") and not company.domain:
            company.domain = res.get("domain")
    elif isinstance(res, list):
        raw_contacts = res
    elif hasattr(res, "contacts"):
        raw_contacts = getattr(res, "contacts") or []

    # Process and save contacts
    processed_contacts: List[Contact] = []
    for item in raw_contacts:
        c_dict = item if isinstance(item, dict) else (item.__dict__ if hasattr(item, "__dict__") else {})
        first_name = c_dict.get("first_name") or ""
        last_name = c_dict.get("last_name") or ""
        full_name = c_dict.get("name") or c_dict.get("full_name") or ""

        if not first_name and full_name:
            parts = full_name.strip().split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        first_name = first_name or "Unknown"
        last_name = last_name or "Contact"

        email = c_dict.get("email")
        title = c_dict.get("title") or c_dict.get("role") or c_dict.get("position")
        linkedin_url = c_dict.get("linkedin_url") or c_dict.get("linkedin")

        # Deduplication check
        existing_contact = None
        if email:
            existing_contact = db.query(Contact).filter(
                Contact.company_id == company.id,
                Contact.email == email
            ).first()

        if not existing_contact:
            existing_contact = db.query(Contact).filter(
                Contact.company_id == company.id,
                Contact.first_name == first_name,
                Contact.last_name == last_name
            ).first()

        if not existing_contact:
            new_contact = Contact(
                company_id=company.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                title=title,
                linkedin_url=linkedin_url,
            )
            db.add(new_contact)
            processed_contacts.append(new_contact)
        else:
            if not existing_contact.email and email:
                existing_contact.email = email
            if not existing_contact.title and title:
                existing_contact.title = title
            if not existing_contact.linkedin_url and linkedin_url:
                existing_contact.linkedin_url = linkedin_url
            processed_contacts.append(existing_contact)

    db.flush()

    # Create or update Outreach record
    outreach = db.query(Outreach).filter(Outreach.company_id == company.id).first()
    primary_contact_id = (
        processed_contacts[0].id if processed_contacts else (company.contacts[0].id if company.contacts else None)
    )

    if not outreach:
        outreach = Outreach(
            company_id=company.id,
            contact_id=primary_contact_id,
            kanban_stage=KanbanStage.ENRICHED,
        )
        db.add(outreach)
    else:
        outreach.kanban_stage = KanbanStage.ENRICHED
        if not outreach.contact_id and primary_contact_id:
            outreach.contact_id = primary_contact_id
        outreach.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(outreach)
    db.refresh(company)

    # Fetch all current contacts for the company
    all_contacts = db.query(Contact).filter(Contact.company_id == company.id).all()

    return EnrichmentResultResponse(
        company_id=company.id,
        company_name=company.name,
        outreach_id=outreach.id,
        stage=outreach.kanban_stage.value,
        contacts_count=len(all_contacts),
        contacts=all_contacts,
        raw_data=res,
        message="Company successfully enriched with contacts and outreach initialized.",
    )


@router.get("/contacts/{company_id}", response_model=List[ContactResponse])
def get_contacts(company_id: int, db: Session = Depends(get_db)):
    """List all contacts associated with a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")

    contacts = db.query(Contact).filter(Contact.company_id == company_id).all()
    return contacts


@router.get("/mcp-status", response_model=MCPStatusResponse)
def get_mcp_status():
    """Returns whether the Enricho MCP service is properly configured."""
    api_key_present = bool(settings.ENRICHO_API_KEY and settings.ENRICHO_API_KEY.strip())
    server_url_set = bool(settings.ENRICHO_MCP_SERVER_URL and settings.ENRICHO_MCP_SERVER_URL.strip())

    configured = api_key_present and server_url_set

    # If service provides its own configuration check
    if mcp_enricho_service is not None and hasattr(mcp_enricho_service, "is_configured"):
        try:
            service_configured = mcp_enricho_service.is_configured()
            if isinstance(service_configured, bool):
                configured = service_configured
        except Exception:
            pass

    return MCPStatusResponse(
        configured=configured,
        api_key_present=api_key_present,
        server_url_set=server_url_set,
        server_url=settings.ENRICHO_MCP_SERVER_URL or None,
    )
