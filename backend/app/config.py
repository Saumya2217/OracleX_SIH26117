from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ORACLEX"
    VERSION: str = "1.5.0"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "production"
    TESTING: bool = False
    DEMO_MODE: bool = False
    DEMO_SEED_ON_STARTUP: bool = False
    BOOTSTRAP_ENABLED: bool = False
    BOOTSTRAP_TOKEN: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database (SQLite is convenient for development; PostgreSQL is the deployment target.)
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'oraclex.db'}"
    
    # AI Engine & Local LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2:1b"
    OLLAMA_VISION_MODEL: str = "llava"
    SIMULATED_AI_FALLBACK: bool = False
    MODEL_REQUIRED_FOR_READINESS: bool = False
    WORKER_REQUIRED_FOR_READINESS: bool = False
    
    # Vector Storage & Ingestion
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chromadb")
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: int = 8000
    CHROMA_SSL: bool = False
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = ["pdf", "txt", "md", "csv", "xlsx"]
    MAX_DOCUMENT_PAGES: int = 1000
    MAX_TABULAR_ROWS: int = 10000
    INGESTION_LEASE_SECONDS: int = 120
    INGESTION_POLL_SECONDS: float = 2.0
    INGESTION_MAX_ATTEMPTS: int = 3
    INGESTION_RETRY_BASE_SECONDS: int = 5
    WORKER_HEARTBEAT_TTL_SECONDS: int = 30
    INGESTION_INLINE_FOR_TESTS: bool = False
    
    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @model_validator(mode="after")
    def validate_security_settings(self):
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters.")
        if "oraclex-sovereign-confidential" in self.SECRET_KEY:
            raise ValueError("The archived demonstration SECRET_KEY cannot be used.")
        if self.BOOTSTRAP_ENABLED and (not self.BOOTSTRAP_TOKEN or len(self.BOOTSTRAP_TOKEN) < 16):
            raise ValueError("BOOTSTRAP_TOKEN must contain at least 16 characters when bootstrap is enabled.")
        if "*" in self.ALLOWED_ORIGINS:
            raise ValueError("Wildcard CORS origins are not allowed.")
        if self.DEMO_SEED_ON_STARTUP and not self.DEMO_MODE:
            raise ValueError("DEMO_SEED_ON_STARTUP requires DEMO_MODE=true.")
        if not 1 <= self.CHROMA_PORT <= 65535:
            raise ValueError("CHROMA_PORT must be between 1 and 65535.")
        if not self.TESTING and self.ENVIRONMENT == "production" and not self.CHROMA_HOST:
            raise ValueError("Production requires CHROMA_HOST: API and worker must use one Chroma server.")
        return self

settings = Settings()

# Ensure required runtime directories exist
if not settings.CHROMA_HOST:
    Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

