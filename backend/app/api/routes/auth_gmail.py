"""Gmail OAuth API routes for SponsorPulse.

Handles Google OAuth authorization URL generation, OAuth callback handling,
authentication status inspection, and token revocation.
"""

import inspect
import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings

try:
    from app.services import gmail_service
except ImportError:
    gmail_service = None


router = APIRouter()


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------

class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class AuthUrlResponse(BaseModel):
    auth_url: str

    model_config = {"from_attributes": True}


class AuthCallbackResponse(BaseModel):
    status: str
    message: str
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class RevokeResponse(BaseModel):
    status: str
    message: str

    model_config = {"from_attributes": True}


class ConfigStatusResponse(BaseModel):
    credentials_present: bool
    token_present: bool
    authenticated: bool
    email: Optional[str] = None
    credentials_path: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@router.get("/google/config-status", response_model=ConfigStatusResponse)
async def get_google_config_status():
    """Returns whether credentials.json and token.json are configured on disk."""
    has_creds = False
    if gmail_service and hasattr(gmail_service, "has_credentials_file"):
        has_creds = gmail_service.has_credentials_file()
    else:
        has_creds = os.path.exists(settings.GMAIL_CREDENTIALS_PATH)

    token_path = settings.GMAIL_TOKEN_PATH
    has_token = os.path.exists(token_path)

    email = None
    if gmail_service and hasattr(gmail_service, "get_user_email"):
        email = gmail_service.get_user_email()

    is_auth = False
    if gmail_service and hasattr(gmail_service, "is_authenticated"):
        is_auth = gmail_service.is_authenticated()
    elif has_token:
        is_auth = True

    return ConfigStatusResponse(
        credentials_present=has_creds,
        token_present=has_token,
        authenticated=is_auth,
        email=email,
        credentials_path=settings.GMAIL_CREDENTIALS_PATH,
    )


@router.post("/google/dev-connect", response_model=AuthCallbackResponse)
async def google_dev_connect(email: Optional[str] = "outreach@sponsorpulse.local"):
    """
    Connect a development / simulated Gmail account for instant testing
    without requiring Google Cloud Console OAuth verification.
    """
    if gmail_service and hasattr(gmail_service, "get_token_path"):
        token_path = gmail_service.get_token_path()
    else:
        token_path = os.path.abspath(settings.GMAIL_TOKEN_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(token_path)), exist_ok=True)
    dev_token = {
        "account": email,
        "email": email,
        "is_simulated": True,
        "token": "dev_simulated_token_sponsorpulse",
        "scopes": settings.GMAIL_SCOPES,
    }
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(dev_token, f, indent=2)

    return AuthCallbackResponse(
        status="success",
        message="Simulated Gmail account connected successfully.",
        email=email,
    )

@router.get("/google/status", response_model=AuthStatusResponse)
async def get_google_auth_status():
    """Returns the current authentication status and active email for Gmail OAuth."""
    if gmail_service is not None:
        if hasattr(gmail_service, "get_auth_status"):
            try:
                res = gmail_service.get_auth_status()
                if inspect.isawaitable(res):
                    res = await res
                if isinstance(res, dict):
                    return AuthStatusResponse(
                        authenticated=bool(res.get("authenticated", False)),
                        email=res.get("email"),
                    )
            except Exception:
                pass

        if hasattr(gmail_service, "is_authenticated"):
            try:
                is_auth = gmail_service.is_authenticated()
                if inspect.isawaitable(is_auth):
                    is_auth = await is_auth

                email = None
                if is_auth and hasattr(gmail_service, "get_user_email"):
                    email = gmail_service.get_user_email()
                    if inspect.isawaitable(email):
                        email = await email

                return AuthStatusResponse(authenticated=bool(is_auth), email=email)
            except Exception:
                pass

    # Fallback inspection of stored token file
    if gmail_service and hasattr(gmail_service, "get_token_path"):
        token_path = gmail_service.get_token_path()
    else:
        token_path = os.path.abspath(settings.GMAIL_TOKEN_PATH)
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            email = data.get("account") or data.get("email")
            return AuthStatusResponse(authenticated=True, email=email)
        except Exception:
            return AuthStatusResponse(authenticated=True, email=None)

    return AuthStatusResponse(authenticated=False, email=None)


@router.get("/google/url", response_model=AuthUrlResponse)
async def get_google_auth_url():
    """Generates the Google OAuth authorization URL for initiating login redirect."""
    if gmail_service is not None:
        if hasattr(gmail_service, "has_credentials_file") and not gmail_service.has_credentials_file():
            raise HTTPException(
                status_code=400,
                detail="Google OAuth credentials file not found at 'backend/credentials/credentials.json'. Place your client_secrets credentials.json from Google Cloud Console into that path, or use Dev Connect."
            )

        for method_name in ("get_authorization_url", "get_auth_url", "generate_auth_url"):
            if hasattr(gmail_service, method_name):
                try:
                    func = getattr(gmail_service, method_name)
                    res = func()
                    if inspect.isawaitable(res):
                        res = await res

                    if isinstance(res, dict):
                        url = res.get("auth_url") or res.get("url")
                    else:
                        url = str(res)

                    if url:
                        return AuthUrlResponse(auth_url=url)
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate Google auth URL: {str(e)}"
                    )

    raise HTTPException(
        status_code=503,
        detail="Gmail service is not available or OAuth credentials are not configured"
    )


@router.get("/google/callback", response_model=AuthCallbackResponse)
async def google_auth_callback(code: str = Query(..., description="Google OAuth authorization code")):
    """Handles the OAuth callback from Google by exchanging the authorization code for credentials."""
    if gmail_service is None or not hasattr(gmail_service, "handle_callback"):
        raise HTTPException(status_code=503, detail="Gmail service is not available")

    try:
        res = gmail_service.handle_callback(code)
        if inspect.isawaitable(res):
            res = await res

        email = None
        if isinstance(res, dict):
            email = res.get("email")
        elif isinstance(res, str) and "@" in res:
            email = res

        return AuthCallbackResponse(
            status="success",
            message="Google account connected and authenticated successfully",
            email=email,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to complete Google authentication: {str(e)}"
        )


@router.post("/google/revoke", response_model=RevokeResponse)
async def revoke_google_auth():
    """Revokes Gmail authentication credentials and deletes the local token file."""
    if gmail_service is not None:
        for method_name in ("revoke_credentials", "revoke_token", "logout"):
            if hasattr(gmail_service, method_name):
                try:
                    res = getattr(gmail_service, method_name)()
                    if inspect.isawaitable(res):
                        await res
                    break
                except Exception:
                    pass

    if gmail_service and hasattr(gmail_service, "get_token_path"):
        token_path = gmail_service.get_token_path()
    else:
        token_path = os.path.abspath(settings.GMAIL_TOKEN_PATH)
    if os.path.exists(token_path):
        try:
            os.remove(token_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove token file: {str(e)}"
            )

    return RevokeResponse(
        status="success",
        message="Google OAuth credentials successfully revoked and logged out",
    )
