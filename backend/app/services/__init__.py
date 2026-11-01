"""SponsorPulse backend services."""

from app.services.scraper_service import (
    sync_funding_feeds,
    sync_funding_feeds_async,
    async_sync_funding_feeds,
)
from app.services.mcp_enricho_service import (
    enrich_company,
    EnrichoMCPClient,
)
from app.services.gemini_service import (
    generate_cold_email,
    regenerate_cold_email,
)
from app.services.gmail_service import (
    get_auth_url,
    handle_callback,
    get_gmail_service,
    is_authenticated,
    send_email,
    check_thread_replies,
)

__all__ = [
    "sync_funding_feeds",
    "sync_funding_feeds_async",
    "async_sync_funding_feeds",
    "enrich_company",
    "EnrichoMCPClient",
    "generate_cold_email",
    "regenerate_cold_email",
    "get_auth_url",
    "handle_callback",
    "get_gmail_service",
    "is_authenticated",
    "send_email",
    "check_thread_replies",
]
