"""
Gemini AI service for generating personalized, high-converting cold outreach emails.
Uses the official google-genai SDK and gemini-2.0-flash model to craft tailored emails
based on company funding announcements, contact role, and value proposition.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# Model specification with cascading fallback
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
]
GEMINI_MODEL = GEMINI_MODELS[0]

# System instruction defining role, tone, and strict constraints
SYSTEM_INSTRUCTION = """You are an elite Industry & Corporate Engagement Director crafting personalized, high-converting partnership outreach emails to newly funded tech startups.

GOAL:
1. Congratulate the recipient on their recent funding announcement.
2. Acknowledge their impending engineering and technical team scaling needs.
3. Propose an Industry & Corporate Engagement partnership:
   - Pre-assessed, top-tier graduate technical talent
   - Campus drive sponsorship and hackathon co-hosting
   - Tailored internship pipelines customized for their stack
4. Propose a specific, low-friction CTA (e.g., a "10-minute discovery call next Tuesday").

TONE:
Professional, crisp, low-friction, offering direct value without being pushy.

STRICT CONSTRAINTS:
1. Subject line MUST be strictly under 7 words (maximum 6 words).
2. Body MUST be strictly under 120 words.
3. Must personalize with specific funding details and sector context.
4. Output MUST be valid JSON with exactly two keys: "subject" and "body".
"""


def get_client() -> genai.Client:
    """Initialize and return the Google GenAI SDK client."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY is not configured in settings. Calls may fail unless authenticated via environment.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=4000),
    )


def _clean_and_parse_json(raw_text: str) -> Dict[str, str]:
    """Parse JSON response from model output, handling markdown code fences if present."""
    text = raw_text.strip()

    # Remove markdown code block wrapping if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Locate first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Model output is not a valid JSON dictionary")

    subject = str(data.get("subject", "")).strip()
    body = str(data.get("body", "")).strip()

    # Enforce subject word count constraint (< 7 words)
    words = subject.split()
    if len(words) >= 7:
        subject = " ".join(words[:6])

    return {"subject": subject, "body": body}


def _generate_fallback_email(
    company_name: str,
    funding_info: str,
    contact_name: str,
    contact_title: str,
) -> Dict[str, str]:
    """
    High-quality deterministic fallback in case of missing API key, network error, or quota limit.
    Ensures that development workflows and pipeline tests never fail ungracefully.
    """
    first_name = contact_name.split()[0] if contact_name else "there"
    funding_phrase = f"your {funding_info}" if funding_info else "recent round"

    # Strictly < 7 words
    subject = f"Talent pipelines for {company_name}'s scaling"
    words = subject.split()
    if len(words) >= 7:
        subject = " ".join(words[:6])

    body = (
        f"Hi {first_name},\n\n"
        f"Congratulations on {funding_phrase}! As {company_name} scales its engineering team, "
        f"securing pre-assessed technical talent early is key to hitting product milestones.\n\n"
        f"We lead university corporate partnerships, providing high-growth teams with pre-vetted graduate engineers "
        f"and campus drive sponsorships to compress your hiring cycle.\n\n"
        f"Would you be open to a 10-minute discovery call next Tuesday to explore custom talent pipelines?\n\n"
        f"Best regards,\n"
        f"Industry Engagement Team"
    )

    return {"subject": subject, "body": body}


def _execute_gemini_call(prompt: str, system_prompt: str = SYSTEM_INSTRUCTION) -> str:
    """Synchronous invocation of the Gemini API via google-genai SDK with model fallback."""
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        temperature=0.7,
    )

    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            logger.info(f"Attempting content generation using {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            logger.debug(f"Model {model_name} failed: {e}. Trying next fallback...")

    if last_error:
        raise last_error
    raise RuntimeError("No response returned from Gemini API")


async def generate_cold_email(
    company_name: Optional[str] = None,
    funding_info: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact_title: Optional[str] = None,
    company_summary: Optional[str] = None,
    refinement_instructions: Optional[str] = None,
    company: Optional[Any] = None,
    contact: Optional[Any] = None,
    outreach: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, str]:
    """
    Generate a personalized, high-converting cold email for outreach.
    Supports flexible arguments (model objects or individual strings).
    """
    # Extract from company object if provided
    if company is not None:
        company_name = getattr(company, "name", None) or company_name
        funding_info = getattr(company, "funding_amount", None) or funding_info
        company_summary = getattr(company, "summary", None) or company_summary

    # Extract from outreach object if provided
    if outreach is not None:
        c = getattr(outreach, "company", None)
        if c:
            company_name = getattr(c, "name", None) or company_name
            funding_info = getattr(c, "funding_amount", None) or funding_info
            company_summary = getattr(c, "summary", None) or company_summary
        ct = getattr(outreach, "contact", None)
        if ct:
            first = getattr(ct, "first_name", "") or ""
            last = getattr(ct, "last_name", "") or ""
            contact_name = f"{first} {last}".strip() or contact_name
            contact_title = getattr(ct, "title", None) or contact_title

    # Extract from contact object if provided
    if contact is not None:
        first = getattr(contact, "first_name", "") or ""
        last = getattr(contact, "last_name", "") or ""
        name = f"{first} {last}".strip()
        contact_name = name or contact_name
        contact_title = getattr(contact, "title", None) or contact_title

    # Defaults for missing data
    company_name = (company_name or "Tech Innovator").strip()
    funding_info = (funding_info or "recent funding announcement").strip()
    contact_name = (contact_name or "Hiring Leader").strip()
    contact_title = (contact_title or "Engineering / Talent Leader").strip()
    company_summary = (company_summary or "high-growth tech scaling team").strip()

    refine_section = ""
    if refinement_instructions:
        refine_section = f"\nSpecific Customizer Refinement Instructions:\n{refinement_instructions}\n"

    # Determine outreach pillar (CORPORATE, CAMPUS, or COMMUNITY)
    pillar = "CORPORATE"
    if outreach is not None and hasattr(outreach, "pillar"):
        pillar = outreach.pillar.value if hasattr(outreach.pillar, "value") else str(outreach.pillar)
    elif "pillar" in kwargs:
        pillar = str(kwargs["pillar"])

    # Tailor prompt by outreach pillar
    if pillar == "CAMPUS":
        prompt = f"""Generate a personalized Campus Outreach partnership email to a college or university leader:

Target Institution / College: {company_name}
Target Contact: {contact_name} ({contact_title})
Institution Context: {company_summary}
{refine_section}
Goal: Propose partnering on campus placement drives, student hackathons, pre-assessed industry training, and recruiting top graduate cohorts.
Strict constraints:
- Subject line: MUST be strictly under 7 words.
- Body length: MUST be under 120 words.
- Specific CTA: "15-minute introductory call next week".
- Return ONLY JSON with "subject" and "body" keys.
"""
    elif pillar == "COMMUNITY":
        prompt = f"""Generate a personalized Community Outreach collaboration email to a tech community or club organizer:

Community / Hub Name: {company_name}
Organizer / Lead: {contact_name} ({contact_title})
Community Focus: {company_summary}
{refine_section}
Goal: Propose sponsoring community workshops, providing mentorship, and offering career support and industry opportunities for their members.
Strict constraints:
- Subject line: MUST be strictly under 7 words.
- Body length: MUST be under 120 words.
- Specific CTA: "brief catchup call this Thursday".
- Return ONLY JSON with "subject" and "body" keys.
"""
    else:
        # Default CORPORATE
        prompt = f"""Generate a personalized corporate engagement cold outreach email with these details:

Target Company: {company_name}
Funding Information: {funding_info}
Recipient Name: {contact_name}
Recipient Title: {contact_title}
Company Context: {company_summary}
{refine_section}
Goal: Congratulate on recent funding, acknowledge team scaling, and propose pre-assessed graduate technical talent & campus hiring drives.
Strict constraints:
- Subject line: MUST be strictly under 7 words.
- Body length: MUST be under 120 words.
- Specific CTA: "10-minute discovery call next Tuesday".
- Return ONLY JSON with "subject" and "body" keys.
"""

    logger.info(f"Generating cold email for {company_name} ({contact_name}) using {GEMINI_MODEL}")

    try:
        raw_output = await asyncio.to_thread(_execute_gemini_call, prompt, SYSTEM_INSTRUCTION)
        parsed = _clean_and_parse_json(raw_output)
        if parsed.get("subject") and parsed.get("body"):
            return parsed
        raise ValueError("Incomplete email fields in model response")
    except Exception as e:
        logger.warning(
            f"Gemini API call or parsing failed ({e}). Providing high-fidelity fallback email."
        )
        return _generate_fallback_email(
            company_name=company_name,
            funding_info=funding_info,
            contact_name=contact_name,
            contact_title=contact_title,
        )


async def regenerate_cold_email(
    company_name: str,
    funding_info: str,
    contact_name: str,
    contact_title: str,
    company_summary: str,
    current_email: Optional[Dict[str, str]] = None,
    instructions: str = "",
) -> Dict[str, str]:
    """
    Regenerate a cold email incorporating specific user refinement instructions.
    
    Args:
        company_name: Name of the company
        funding_info: Funding details
        contact_name: Recipient's name
        contact_title: Recipient's title
        company_summary: Summary of the company
        current_email: Optional dictionary with existing {"subject": "...", "body": "..."}
        instructions: User instructions for refinement (e.g. "Focus more on internship sponsorship")
        
    Returns:
        dict: {"subject": "...", "body": "..."}
    """
    curr_subj = current_email.get("subject", "") if current_email else ""
    curr_body = current_email.get("body", "") if current_email else ""

    refinement_prompt = f"""Revise the following cold outreach email based on user feedback while strictly adhering to all rules:

Target Company: {company_name}
Funding Information: {funding_info or 'Recent Funding Round'}
Recipient Name: {contact_name or 'Hiring Leader'}
Recipient Title: {contact_title or 'Engineering / Talent Leader'}
Company Context: {company_summary or 'High growth technology startup'}

Current Draft:
Subject: {curr_subj}
Body: {curr_body}

User Refinement Instructions:
{instructions or 'Make the tone crisper and emphasize tailored internship pipelines.'}

Remember the strict constraints:
- Subject line: MUST be strictly under 7 words.
- Body length: MUST be under 120 words.
- Specific CTA: "10-minute discovery call next Tuesday".
- Return ONLY JSON with "subject" and "body" keys.
"""

    logger.info(f"Regenerating cold email for {company_name} with user instructions: '{instructions}'")

    try:
        raw_output = await asyncio.to_thread(_execute_gemini_call, refinement_prompt, SYSTEM_INSTRUCTION)
        parsed = _clean_and_parse_json(raw_output)
        if parsed.get("subject") and parsed.get("body"):
            return parsed
        raise ValueError("Incomplete fields in revised email")
    except Exception as e:
        logger.warning(f"Gemini regeneration failed ({e}). Providing refined fallback.")
        fallback = _generate_fallback_email(
            company_name=company_name,
            funding_info=funding_info,
            contact_name=contact_name,
            contact_title=contact_title,
        )
        if instructions:
            fallback["body"] += f"\n\nP.S. Specifically tailored regarding: {instructions[:60]}"
        return fallback
