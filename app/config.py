from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://idp:idp_secret@localhost:5432/idp_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Provider
    LLM_PROVIDER: str = Field(default="claude", pattern=r"^(claude|ollama)$")

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"

    # File Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50
    MAX_BATCH_SIZE: int = 20
    ALLOWED_EXTENSIONS: str = "pdf,docx,png,jpg,jpeg,tiff"

    # Storage Backend: "local" or "minio"
    STORAGE_BACKEND: str = Field(default="local", pattern=r"^(local|minio)$")

    # MinIO (required if STORAGE_BACKEND=minio)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "idp-documents"
    MINIO_SECURE: bool = False

    # Webhook
    WEBHOOK_TIMEOUT_SECONDS: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"

    # Sentry
    SENTRY_DSN: str = ""

    # App
    APP_VERSION: str = "0.1.0"

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")}

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
