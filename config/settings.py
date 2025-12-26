"""Application settings and environment configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from a .env file if present
load_dotenv()


class Settings(BaseSettings):
    """Centralized application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    environment: str = Field("development", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")

    # Twilio
    twilio_account_sid: Optional[str] = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(None, alias="TWILIO_PHONE_NUMBER")
    public_base_url: Optional[str] = Field(None, alias="PUBLIC_BASE_URL")

    # Google Cloud / Gemini
    google_application_credentials: Optional[str] = Field(None, alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_project_id: Optional[str] = Field(None, alias="GOOGLE_PROJECT_ID")
    gemini_api_key: Optional[str] = Field(None, alias="GEMINI_API_KEY")

    # Data layer
    database_url: str = Field("sqlite:///./voice_bot.db", alias="DATABASE_URL")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")

    @property
    def credentials_path(self) -> Optional[Path]:
        """Return Path to Google credentials if configured."""
        if not self.google_application_credentials:
            return None
        return Path(self.google_application_credentials).expanduser()

    @property
    def websocket_stream_url(self) -> str:
        """Compute WebSocket stream URL Twilio should connect to."""
        base = self.public_base_url or f"http://{self.host}:{self.port}"
        # Twilio expects secure websocket when using https
        if base.startswith("https://"):
            return base.replace("https://", "wss://") + "/ws/audio-stream"
        if base.startswith("http://"):
            return base.replace("http://", "ws://") + "/ws/audio-stream"
        return f"wss://{base}/ws/audio-stream"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
