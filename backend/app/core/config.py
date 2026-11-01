"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Central configuration for SponsorPulse backend."""

    # Database
    DATABASE_URL: str = "sqlite:///./sponsorpulse.db"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:5173"]'

    # Gemini
    GEMINI_API_KEY: str = ""

    # Enricho MCP
    ENRICHO_API_KEY: str = ""
    ENRICHO_MCP_SERVER_URL: str = "https://mcp.enricho.co/mcp"

    # Gmail OAuth
    GMAIL_CREDENTIALS_PATH: str = "credentials/credentials.json"
    GMAIL_TOKEN_PATH: str = "credentials/token.json"
    GMAIL_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

