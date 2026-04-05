import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DocStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocCategory(str, enum.Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    REPORT = "report"
    LEGAL_BRIEF = "legal_brief"
    FINANCIAL_STATEMENT = "financial_statement"
    SHIPPING_MANIFEST = "shipping_manifest"
    UNKNOWN = "unknown"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(512), nullable=False)
    original_name = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(128), nullable=True)
    storage_path = Column(String(1024), nullable=False)

    # Processing state
    status = Column(
        Enum(DocStatus, name="doc_status", values_callable=lambda x: [e.value for e in x]),
        default=DocStatus.UPLOADED,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    # Extracted content
    raw_text = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)

    # LLM results
    category = Column(
        Enum(DocCategory, name="doc_category", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    key_entities = Column(JSONB, nullable=True)
    flags = Column(JSONB, nullable=True)

    # Multi-tenancy
    client_id = Column(String(128), nullable=True)
    tags = Column(JSONB, default=list)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_category", "category"),
        Index("idx_documents_client", "client_id"),
        Index("idx_documents_created", "created_at"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash = Column(String(256), nullable=False, unique=True)
    client_id = Column(String(128), nullable=False)
    name = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit = Column(Integer, default=100)  # requests per minute
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(128), nullable=False, unique=True)
    url = Column(String(2048), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
