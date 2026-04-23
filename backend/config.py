"""
Configuration management for ThirdEye Intelligent Monitoring System
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    GEMINI_API_KEY: str
    CLAUDE_API_KEY: str  # Anthropic Claude API key for reasoning agent
    GOOGLE_PROJECT_ID: Optional[str] = None

    # Email Configuration (Gmail SMTP — legacy, unused)
    GMAIL_USER: str = "moneshrallapalli@gmail.com"
    GMAIL_APP_PASSWORD: str = ""

    # Email Configuration (Resend — used for verification/welcome mail)
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "ThirdEye <onboarding@resend.dev>"
    EMAIL_RECIPIENT: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sentintinel_db"
    POSTGRES_USER: str = "sentintinel_user"
    POSTGRES_PASSWORD: str

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # ChromaDB Configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIRECTORY: str = "./chromadb_data"

    # Application Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Camera Configuration
    # 1.0 FPS gives the model a fresh frame every second so short events
    # (e.g. someone drinking from a water bottle) actually land in a frame.
    # The analysis loop deduplicates + throttles Claude calls on top of this
    # so the upstream rate limit is respected regardless of capture FPS.
    CAMERA_FPS: float = 1.0
    MAX_CAMERAS: int = 4
    VIDEO_RESOLUTION_WIDTH: int = 640  # Reduced for faster processing
    VIDEO_RESOLUTION_HEIGHT: int = 480  # Reduced for faster processing

    # Minimum seconds between Claude vision calls per camera. The analysis
    # loop also skips any frame it has already analysed, so in practice
    # Claude is called at most once per unique frame per interval.
    ANALYSIS_MIN_INTERVAL_SECONDS: float = 3.0

    # Alert Thresholds
    CRITICAL_THRESHOLD: int = 80
    WARNING_THRESHOLD: int = 50
    IMMEDIATE_ALERT_THRESHOLD: int = 60  # Threshold for immediate action required alerts
    ACTIVITY_DETECTION_THRESHOLD: int = 40  # Lower threshold for activity/state changes (emergency mode)

    # Display / localisation — controls timezone used in emails & logs.
    # Use an IANA name (e.g. "America/Los_Angeles", "Asia/Kolkata").
    # Leave empty to use the server's local timezone.
    DISPLAY_TIMEZONE: str = ""

    # Public URL of the web app. Used in email CTAs (e.g. "Open ThirdEye →").
    # Override in .env with APP_PUBLIC_URL=https://thirdeye.example.com
    APP_PUBLIC_URL: str = "http://localhost:3000"

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL database URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Construct Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
