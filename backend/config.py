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

    # Email Configuration
    RESEND_API_KEY: Optional[str] = None  # Resend - Recommended (excellent deliverability)
    BREVO_API_KEY: Optional[str] = None   # Brevo - Alternative
    EMAIL_RECIPIENT: str = "moneshralapalli@gmail.com"

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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Camera Configuration
    CAMERA_FPS: float = 0.033  # 0.033 FPS = 1 frame every 30 seconds = 2 calls/min (within free tier rate limit)
    MAX_CAMERAS: int = 4
    VIDEO_RESOLUTION_WIDTH: int = 640  # Reduced for faster processing
    VIDEO_RESOLUTION_HEIGHT: int = 480  # Reduced for faster processing

    # Alert Thresholds
    CRITICAL_THRESHOLD: int = 80
    WARNING_THRESHOLD: int = 50
    IMMEDIATE_ALERT_THRESHOLD: int = 60  # Threshold for immediate action required alerts
    ACTIVITY_DETECTION_THRESHOLD: int = 40  # Lower threshold for activity/state changes (emergency mode)

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


# Global settings instance
settings = Settings()
