"""
Service for scraping funding news from TechCrunch Startups and VentureBeat RSS feeds.
Parses articles, extracts company names, funding amounts, rounds, and metadata,
deduplicates against the database, and creates Company & Outreach records.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Company, KanbanStage, Outreach

logger = logging.getLogger(__name__)

# Target RSS Feeds
FEEDS = [
    {
        "name": "TechCrunch Startups",
        "url": "https://techcrunch.com/category/startups/feed/",
    },
    {
        "name": "VentureBeat Business",
        "url": "https://venturebeat.com/category/business/feed/",
    },
]

# HTTP client configuration
HTTP_TIMEOUT = 20.0
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 SponsorPulse/1.0"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# Regex for funding amounts (e.g. $5M, $10.5 million, $1.2B, 50 million dollars)
FUNDING_AMOUNT_REGEX = re.compile(
    r'(?:'
    r'[\$€£]\s*\d+(?:\.\d+)?\s*(?:[BMKbmk]|billion|million|thousand)?\b|'
    r'\b\d+(?:\.\d+)?\s*(?:million|billion)\s*(?:dollars|usd|eur|pounds)?\b'
    r')',
    re.IGNORECASE,
)

# Regex for funding rounds (e.g. Series A, Pre-seed, Seed, Series B-1, Growth)
FUNDING_ROUND_REGEX = re.compile(
    r'\b('
    r'pre[- ]?seed|seed(?: round)?|'
    r'series\s+[a-j](?:[- ]?\d+)?|'
    r'growth round|debt financing|extension round|convertible note'
    r')\b',
    re.IGNORECASE,
)

# Action verbs commonly following company names in funding headlines
FUNDING_VERBS = [
    r'raises', r'raised',
    r'secures', r'secured',
    r'bags', r'bagged',
    r'closes', r'closed',
    r'lands', r'landed',
    r'scores', r'scored',
    r'snags', r'snagged',
    r'nabs', r'nabbed',
    r'pulls in', r'hauls in', r'rakes in',
    r'gets', r'clinches', r'attracts',
]

# Verb pattern matching: Company raises ...
VERB_PATTERN = re.compile(
    r'\b(?:' + '|'.join(FUNDING_VERBS) + r')\b',
    re.IGNORECASE,
)

# Noise descriptor prefixes to strip out before the company name
DESCRIPTOR_PREFIXES = [
    r'ai(?:-powered)?',
    r'generative ai',
    r'crypto',
    r'fintech',
    r'healthtech',
    r'edtech',
    r'biotech',
    r'robotics',
    r'cybersecurity',
    r'autonomous',
    r'enterprise',
    r'cloud',
    r'saas',
    r'b2b',
    r'french',
    r'german',
    r'uk',
    r'us',
    r'european',
    r'israeli',
    r'indian',
    r'japanese',
    r'startup',
    r'firm',
    r'platform',
    r'maker',
    r'company',
    r'app',
    r'service',
    r'developer',
    r'provider',
    r'creator',
    r'scaleup',
    r'unicorn',
    r'specialist',
]

DESCRIPTOR_REGEX = re.compile(
    r'^(?:(?:an?|the)\s+)?(?:(?:' + '|'.join(DESCRIPTOR_PREFIXES) + r')[\s\-]+)+',
    re.IGNORECASE,
)


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def extract_funding_info(title: str, summary: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract funding amount and round from headline and article summary.
    Returns (funding_amount_str, funding_round_str).
    """
    combined_text = f"{title}. {summary}"

    # Extract funding amount
    amount_match = FUNDING_AMOUNT_REGEX.search(title)
    if not amount_match:
        amount_match = FUNDING_AMOUNT_REGEX.search(summary)
    funding_amount = amount_match.group(0).strip() if amount_match else None

    # Extract funding round
    round_match = FUNDING_ROUND_REGEX.search(title)
    if not round_match:
        round_match = FUNDING_ROUND_REGEX.search(summary)
    funding_round = round_match.group(0).strip().title() if round_match else None

    # Build formatted representation e.g. "$15M (Series A)" or "$10M" or "Series A"
    formatted_funding = None
    if funding_amount and funding_round:
        formatted_funding = f"{funding_amount} ({funding_round})"
    elif funding_amount:
        formatted_funding = funding_amount
    elif funding_round:
        formatted_funding = funding_round

    return formatted_funding, funding_round


def extract_company_name(title: str, summary: str) -> Optional[str]:
    """
    Heuristically extract the company name from an RSS headline or summary.
    """
    # Clean up standard feed title prefixes/suffixes
    clean_title = re.sub(r'\s*[\-\|]\s*(?:TechCrunch|VentureBeat).*$', '', title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r'^(?:Funding Alert|Exclusive|Breaking|Report|Venture):\s*', '', clean_title, flags=re.IGNORECASE).strip()

    candidate = None

    # Pattern 1: Check for "How/Why [Company] raised..."
    how_why_match = re.match(r'^(?:How|Why)\s+([A-Z0-9][A-Za-z0-9\.\'\-&]+(?:\s+[A-Z0-9][A-Za-z0-9\.\'\-&]+){0,2})\s+(?:raised|secured|landed)', clean_title, re.IGNORECASE)
    if how_why_match:
        candidate = how_why_match.group(1).strip()

    # Pattern 2: Search for action verb split
    if not candidate:
        verb_match = VERB_PATTERN.search(clean_title)
        if verb_match:
            # Everything before the verb
            prefix = clean_title[:verb_match.start()].strip()
            # Remove trailing commas or colons
            prefix = prefix.rstrip(":, ")
            if prefix:
                candidate = prefix

    # Pattern 3: Look for "[Company] Scores/Bags/Lands..." with colon/dash prefix
    if not candidate and ":" in clean_title:
        parts = clean_title.split(":", 1)
        if len(parts) == 2 and VERB_PATTERN.search(parts[1]):
            candidate = parts[0].strip()

    if not candidate:
        # Fallback: check first capitalized word/words before first comma or dollar sign
        fallback_match = re.match(r'^([A-Z0-9][A-Za-z0-9\.\'\-&]+(?:\s+[A-Z0-9][A-Za-z0-9\.\'\-&]+){0,2})', clean_title)
        if fallback_match:
            candidate = fallback_match.group(1).strip()

    if not candidate:
        return None

    # Clean candidate: remove descriptors and leading articles
    candidate = DESCRIPTOR_REGEX.sub('', candidate).strip()
    # Strip leading "an ", "a ", "the "
    candidate = re.sub(r'^(?:an?|the)\s+', '', candidate, flags=re.IGNORECASE).strip()
    # Strip any trailing punctuation
    candidate = re.sub(r'[\'\",\.\:\;]+$', '', candidate).strip()

    # Validate candidate name quality
    invalid_names = {
        "how", "why", "what", "who", "when", "this", "that", "these", "those",
        "startup", "startups", "exclusive", "report", "techcrunch", "venturebeat",
        "funding", "round", "series", "venture", "investors", "seed",
    }
    if candidate.lower() in invalid_names or len(candidate) < 2 or len(candidate) > 60:
        return None

    return candidate


def parse_published_date(entry: dict) -> datetime:
    """Extract and parse published date into a UTC datetime."""
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            return datetime(
                year=published_parsed.tm_year,
                month=published_parsed.tm_mon,
                day=published_parsed.tm_mday,
                hour=published_parsed.tm_hour,
                minute=published_parsed.tm_min,
                second=published_parsed.tm_sec,
                tzinfo=timezone.utc,
            )
        except Exception as e:
            logger.debug(f"Could not convert parsed time tuple: {e}")

    # Fallback: current UTC time
    return datetime.now(timezone.utc)


def extract_domain_from_text(name: str, summary: str, url: str) -> Optional[str]:
    """Extract or hypothesize domain for the company."""
    # Look for domain patterns in summary (e.g. acme.com, acme.ai, acme.io)
    name_clean = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    if name_clean:
        domain_match = re.search(
            r'\b(' + re.escape(name_clean) + r'\.(?:com|ai|io|co|net|org|tech|dev))\b',
            summary,
            re.IGNORECASE,
        )
        if domain_match:
            return domain_match.group(1).lower()

    # Fallback: standard candidate domain
    if len(name_clean) >= 2:
        return f"{name_clean}.com"
    return None


def fetch_feed_content(url: str) -> Optional[str]:
    """Fetch raw feed XML via httpx with proper User-Agent header."""
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, headers=HTTP_HEADERS, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.warning(f"Failed to fetch feed at {url} with httpx: {e}")
        return None


def sync_funding_feeds(db: Session) -> List[Company]:
    """
    Synchronously fetch and process funding RSS feeds.
    
    1. Fetches TechCrunch Startups and VentureBeat Business RSS feeds.
    2. Parses articles, extracts company names, funding amounts, rounds, and summaries.
    3. De-duplicates against existing companies in SQLite (case-insensitive name check).
    4. Creates new Company records and corresponding Outreach records in DISCOVERED stage.
    5. Returns the list of newly created Company objects.
    """
    logger.info("Starting sync_funding_feeds...")
    new_companies: List[Company] = []
    seen_in_batch = set()

    for feed_info in FEEDS:
        feed_name = feed_info["name"]
        feed_url = feed_info["url"]
        logger.info(f"Processing feed: {feed_name} ({feed_url})")

        content = fetch_feed_content(feed_url)
        if content:
            parsed_feed = feedparser.parse(content)
        else:
            # Fallback to feedparser direct fetch
            logger.info(f"Attempting direct feedparser fetch for {feed_url}")
            parsed_feed = feedparser.parse(feed_url)

        entries = getattr(parsed_feed, "entries", [])
        logger.info(f"Retrieved {len(entries)} entries from {feed_name}")

        for entry in entries:
            title = entry.get("title", "").strip()
            article_url = entry.get("link") or entry.get("id") or ""

            # Extract raw summary or content
            raw_summary = ""
            if "summary" in entry:
                raw_summary = entry.get("summary", "")
            elif "content" in entry and len(entry["content"]) > 0:
                raw_summary = entry["content"][0].get("value", "")
            elif "description" in entry:
                raw_summary = entry.get("description", "")

            cleaned_summary = clean_html(raw_summary)

            # Extract company name
            company_name = extract_company_name(title, cleaned_summary)
            if not company_name:
                continue

            normalized_name = company_name.lower().strip()

            # Skip if seen in this batch
            if normalized_name in seen_in_batch:
                continue
            seen_in_batch.add(normalized_name)

            # Check if company already exists in DB (case-insensitive)
            existing = (
                db.query(Company)
                .filter(func.lower(Company.name) == normalized_name)
                .first()
            )
            if existing:
                logger.debug(f"Skipping existing company: {company_name}")
                continue

            # Extract funding amount and round
            funding_amount, _ = extract_funding_info(title, cleaned_summary)
            published_date = parse_published_date(entry)
            domain = extract_domain_from_text(company_name, cleaned_summary, article_url)

            # Create new Company record
            company = Company(
                name=company_name,
                domain=domain,
                funding_amount=funding_amount,
                funding_date=published_date,
                source_url=article_url,
                summary=cleaned_summary[:2000] if cleaned_summary else None,
            )
            db.add(company)
            db.flush()  # populate company.id

            # Create associated Outreach in DISCOVERED stage
            outreach = Outreach(
                company_id=company.id,
                kanban_stage=KanbanStage.DISCOVERED,
            )
            db.add(outreach)
            db.commit()
            db.refresh(company)

            logger.info(
                f"Discovered new company: {company.name} | Funding: {company.funding_amount} | Source: {company.source_url}"
            )
            new_companies.append(company)

    logger.info(f"sync_funding_feeds complete. Discovered {len(new_companies)} new companies.")
    return new_companies


async def sync_funding_feeds_async(db: Session) -> List[Company]:
    """Async wrapper for sync_funding_feeds using asyncio.to_thread."""
    return await asyncio.to_thread(sync_funding_feeds, db)


# Alias for compatibility with both naming styles
async_sync_funding_feeds = sync_funding_feeds_async
