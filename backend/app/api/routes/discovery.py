"""Discovery API routes for SponsorPulse.

Handles syncing funding feeds and querying discovered companies.
"""

from datetime import datetime
import inspect
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Company, Contact, Outreach

try:
    from app.services import scraper_service
except ImportError:
    scraper_service = None


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


class OutreachSummaryResponse(BaseModel):
    id: int
    company_id: int
    contact_id: Optional[int] = None
    kanban_stage: str
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    last_reply_snippet: Optional[str] = None
    sent_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompanyResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    funding_amount: Optional[str] = None
    funding_date: Optional[datetime] = None
    source_url: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompanyDetailResponse(CompanyResponse):
    contacts: List[ContactResponse] = Field(default_factory=list)
    outreaches: List[OutreachSummaryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------

def parse_iso_date(date_str: str) -> datetime:
    """Parse ISO formatted date string safely."""
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(date_str)
    except ImportError:
        clean_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.post("/sync", response_model=List[CompanyResponse])
async def sync_funding(db: Session = Depends(get_db)):
    """Triggers scraper_service.sync_funding_feeds(db) and returns list of newly discovered companies."""
    if scraper_service is None or not hasattr(scraper_service, "sync_funding_feeds"):
        raise HTTPException(status_code=503, detail="Scraper service is not available")

    try:
        result = scraper_service.sync_funding_feeds(db)
        if inspect.isawaitable(result):
            result = await result
        return result or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync funding feeds: {str(e)}")


@router.get("/companies", response_model=List[CompanyResponse])
def list_companies(
    search: Optional[str] = Query(None, description="Filter by company name"),
    min_date: Optional[str] = Query(None, description="Filter funding date on or after this ISO date"),
    date_from: Optional[str] = Query(None, description="Alias for min_date"),
    funding_keyword: Optional[str] = Query(None, description="Search filter within funding_amount"),
    min_funding: Optional[str] = Query(None, description="Alias for funding_keyword"),
    skip: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Max items to return"),
    db: Session = Depends(get_db),
):
    """List all discovered companies with optional search, min_date, and funding keyword filters."""
    query = db.query(Company)

    if search:
        query = query.filter(Company.name.ilike(f"%{search.strip()}%"))

    effective_date = date_from or min_date
    if effective_date:
        try:
            parsed_date = parse_iso_date(effective_date)
            query = query.filter(Company.funding_date >= parsed_date)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Please use ISO 8601 format (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ')."
            )

    effective_funding = min_funding or funding_keyword
    if effective_funding:
        query = query.filter(Company.funding_amount.ilike(f"%{effective_funding.strip()}%"))

    companies = (
        query.order_by(Company.created_at.desc(), Company.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return companies


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get single company with its contacts and outreach records."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
    return company
