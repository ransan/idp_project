import os
from unittest.mock import patch

import pytest


class TestSettings:
    def test_default_values(self):
        """Settings load with sensible defaults."""
        with patch.dict(os.environ, {}, clear=False):
            from app.config import Settings

            s = Settings(
                DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
                ANTHROPIC_API_KEY="test-key",
            )
            assert s.LLM_PROVIDER == "claude"
            assert s.MAX_FILE_SIZE_MB == 50
            assert s.MAX_BATCH_SIZE == 20
            assert s.UPLOAD_DIR == "./uploads"
            assert s.LOG_LEVEL == "INFO"
            assert s.APP_VERSION == "0.1.0"

    def test_allowed_extensions_set(self):
        """allowed_extensions_set parses CSV into a set."""
        from app.config import Settings

        s = Settings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            ALLOWED_EXTENSIONS="pdf,docx,png",
        )
        assert s.allowed_extensions_set == {"pdf", "docx", "png"}

    def test_max_file_size_bytes(self):
        """max_file_size_bytes converts MB to bytes."""
        from app.config import Settings

        s = Settings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            MAX_FILE_SIZE_MB=10,
        )
        assert s.max_file_size_bytes == 10 * 1024 * 1024

    def test_env_override(self):
        """Environment variables override defaults."""
        from app.config import Settings

        s = Settings(
            DATABASE_URL="postgresql+asyncpg://custom:custom@db/custom",
            LLM_PROVIDER="ollama",
            OLLAMA_MODEL="llama3",
            MAX_FILE_SIZE_MB=100,
        )
        assert s.LLM_PROVIDER == "ollama"
        assert s.OLLAMA_MODEL == "llama3"
        assert s.MAX_FILE_SIZE_MB == 100

    def test_invalid_llm_provider_rejected(self):
        """LLM_PROVIDER must be 'claude' or 'ollama'."""
        from pydantic import ValidationError
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(
                DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
                LLM_PROVIDER="gpt4",
            )
