"""
Gmail API service for Desktop OAuth (RFC 8252 loopback flow), sending outreach emails,
and tracking thread replies.
"""

import asyncio
import base64
import logging
import os
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default loopback redirect URI for RFC 8252 desktop OAuth
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/auth/google/callback"


def _resolve_path(path_str: str) -> str:
    """Resolve relative credential/token paths against the backend root directory."""
    if os.path.isabs(path_str):
        return path_str
    # Resolve relative to backend root (two levels up from this file)
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.normpath(os.path.join(backend_root, path_str))


def get_credentials_path() -> str:
    """Return the absolute path to credentials.json."""
    return _resolve_path(settings.GMAIL_CREDENTIALS_PATH)


def get_token_path() -> str:
    """Return the absolute path to token.json."""
    return _resolve_path(settings.GMAIL_TOKEN_PATH)


def has_credentials_file() -> bool:
    """Check if credentials.json is present on disk."""
    return os.path.exists(get_credentials_path())


def get_token_data() -> Optional[Dict[str, Any]]:
    """Read stored token data dictionary if present."""
    token_path = get_token_path()
    if not os.path.exists(token_path):
        return None
    try:
        import json
        with open(token_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_auth_url(redirect_uri: Optional[str] = None) -> str:
    """
    Generate the OAuth 2.0 authorization URL for RFC 8252 desktop / web flow.
    
    Args:
        redirect_uri: Custom redirect URI or default loopback callback.
        
    Returns:
        str: Google OAuth consent URL.
    """
    cred_path = get_credentials_path()
    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            f"Google OAuth credentials file not found at '{cred_path}'. "
            "Download client_secrets from Google Cloud Console and place it at that path."
        )

    effective_redirect = redirect_uri or DEFAULT_REDIRECT_URI
    flow = InstalledAppFlow.from_client_secrets_file(
        cred_path,
        scopes=settings.GMAIL_SCOPES,
        redirect_uri=effective_redirect,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    logger.info(f"Generated OAuth authorization URL with redirect: {effective_redirect}")
    return auth_url


def handle_callback(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchange the authorization code for access and refresh tokens, saving them to token.json.
    
    Args:
        code: Authorization code from OAuth redirect.
        redirect_uri: Redirect URI used during auth URL generation.
        
    Returns:
        dict: Status confirmation and token file path.
    """
    cred_path = get_credentials_path()
    token_path = get_token_path()

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"OAuth credentials file not found at '{cred_path}'")

    effective_redirect = redirect_uri or DEFAULT_REDIRECT_URI
    flow = InstalledAppFlow.from_client_secrets_file(
        cred_path,
        scopes=settings.GMAIL_SCOPES,
        redirect_uri=effective_redirect,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Ensure credentials directory exists
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    logger.info(f"Gmail credentials successfully stored at: {token_path}")
    return {
        "status": "authenticated",
        "token_path": token_path,
    }


def is_authenticated() -> bool:
    """
    Check if a valid, usable Gmail API token exists (refreshing if expired).
    Supports both real Google OAuth tokens and simulated dev tokens.
    
    Returns:
        bool: True if authenticated and token is valid, False otherwise.
    """
    token_path = get_token_path()
    if not os.path.exists(token_path):
        return False

    token_data = get_token_data()
    if token_data and token_data.get("is_simulated"):
        return True

    try:
        creds = Credentials.from_authorized_user_file(token_path, settings.GMAIL_SCOPES)
        if not creds:
            return False

        if creds.valid:
            return True

        if creds.expired and creds.refresh_token:
            logger.info("Gmail access token expired; refreshing with refresh_token...")
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds.valid

        return False
    except Exception as e:
        logger.warning(f"Failed to validate Gmail credentials from {token_path}: {e}")
        return False


def get_user_email() -> Optional[str]:
    """Retrieve the connected email address from token or Google profile."""
    token_data = get_token_data()
    if token_data:
        email = token_data.get("account") or token_data.get("email")
        if email:
            return email

    if not is_authenticated():
        return None

    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception:
        return None


def get_gmail_service():
    """
    Return an authenticated Google API client resource for the Gmail v1 API.
    Raises RuntimeError if not authenticated.
    """
    token_path = get_token_path()
    if not os.path.exists(token_path):
        raise RuntimeError(
            "Gmail account is not connected. Please click 'Connect Gmail' in the top bar to connect your Google account or start Instant Test Mode."
        )

    creds = Credentials.from_authorized_user_file(token_path, settings.GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError("Gmail credentials are expired or invalid. Re-authentication required.")

    return build("gmail", "v1", credentials=creds)


async def send_email(
    to: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compose and send an RFC 2822 email message using the Gmail API.
    Supports simulated dispatch for offline/development test environments.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body
        thread_id: Optional Gmail thread ID to send as a reply
        
    Returns:
        dict: {"message_id": "...", "thread_id": "..."}
    """
    token_data = get_token_data()
    if token_data and token_data.get("is_simulated"):
        import uuid
        msg_id = f"sim_msg_{uuid.uuid4().hex[:12]}"
        th_id = thread_id or f"sim_th_{uuid.uuid4().hex[:12]}"
        logger.info(f"[SIMULATED GMAIL] Email dispatched to {to}: Subject: '{subject}' (msg_id={msg_id})")
        return {"message_id": msg_id, "thread_id": th_id}

    def _execute_send() -> Dict[str, Any]:
        service = get_gmail_service()

        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject

        if thread_id:
            message["In-Reply-To"] = thread_id
            message["References"] = thread_id

        raw_bytes = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_payload: Dict[str, Any] = {"raw": raw_bytes}
        if thread_id:
            send_payload["threadId"] = thread_id

        result = service.users().messages().send(userId="me", body=send_payload).execute()
        logger.info(f"Email sent successfully: message_id={result.get('id')}, thread_id={result.get('threadId')}")
        return {
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
        }

    return await asyncio.to_thread(_execute_send)


async def check_thread_replies(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Check if a Gmail thread has received any replies from an external sender.
    
    Args:
        thread_id: The Gmail thread ID to inspect.
        
    Returns:
        dict with latest reply snippet and metadata, or None if no external replies.
    """
    token_data = get_token_data()
    if token_data and token_data.get("is_simulated"):
        import uuid
        # Return a simulated reply for testing
        return {
            "reply_message_id": f"sim_rep_{uuid.uuid4().hex[:8]}",
            "thread_id": thread_id,
            "snippet": "Thanks for reaching out! We'd love to schedule a 10-minute discovery call next Tuesday to discuss your engineering student placement pipeline.",
            "from": "talent-scaling@company.com",
            "date": "Today, 10:30 AM",
            "subject": "Re: Industry & Corporate Engagement Partnership",
            "total_messages": 2,
        }

    def _execute_check() -> Optional[Dict[str, Any]]:
        service = get_gmail_service()

        # Identify the authenticated user's own email address
        user_email = ""
        try:
            profile = service.users().getProfile(userId="me").execute()
            user_email = (profile.get("emailAddress") or "").lower()
        except Exception as e:
            logger.debug(f"Could not retrieve user profile email: {e}")

        thread = service.users().threads().get(userId="me", id=thread_id, format="metadata").execute()
        messages = thread.get("messages", [])

        if len(messages) <= 1:
            return None

        # Filter messages not sent by authenticated user
        external_messages = []
        for msg in messages:
            headers = msg.get("payload", {}).get("headers", [])
            from_header = next(
                (h["value"] for h in headers if h["name"].lower() == "from"), ""
            )

            if user_email and user_email not in from_header.lower():
                external_messages.append((msg, from_header, headers))
            elif not user_email and msg != messages[0]:
                # If profile email is unavailable, any subsequent message in thread is considered a reply
                external_messages.append((msg, from_header, headers))

        if not external_messages:
            return None

        latest_msg, from_sender, headers = external_messages[-1]
        date_str = next((h["value"] for h in headers if h["name"].lower() == "date"), None)
        subject_str = next((h["value"] for h in headers if h["name"].lower() == "subject"), None)

        return {
            "reply_message_id": latest_msg.get("id"),
            "thread_id": thread_id,
            "snippet": latest_msg.get("snippet", ""),
            "from": from_sender,
            "date": date_str,
            "subject": subject_str,
            "total_messages": len(messages),
        }

    return await asyncio.to_thread(_execute_check)
