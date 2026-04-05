import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------- Health ----------
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


# ---------- Document Upload ----------
class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_name: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchUploadResponse(BaseModel):
    documents: list[DocumentUploadResponse]
    total: int


# ---------- Document Detail ----------
class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_name: str
    file_size: int | None = None
    mime_type: str | None = None
    status: str
    error_message: str | None = None
    page_count: int | None = None
    category: str | None = None
    confidence: float | None = None
    summary: str | None = None
    extracted_data: dict[str, Any] | None = None
    key_entities: dict[str, Any] | None = None
    flags: list[str] | None = None
    client_id: str | None = None
    tags: list[str] | None = None
    created_at: datetime
    processed_at: datetime | None = None
    processing_time_ms: int | None = None

    model_config = {"from_attributes": True}


# ---------- Document List ----------
class DocumentSummary(BaseModel):
    id: uuid.UUID
    original_name: str
    status: str
    category: str | None = None
    confidence: float | None = None
    client_id: str | None = None
    created_at: datetime
    processing_time_ms: int | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int
    page: int
    size: int


# ---------- Filter Params ----------
class DocumentFilterParams(BaseModel):
    status: str | None = None
    category: str | None = None
    client_id: str | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


# ---------- Stats ----------
class StatusCount(BaseModel):
    status: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class StatsResponse(BaseModel):
    total_documents: int
    by_status: list[StatusCount]
    by_category: list[CategoryCount]


# ---------- Reprocess ----------
class ReprocessResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str


# ---------- Webhook ----------
class WebhookConfigRequest(BaseModel):
    url: str = Field(..., max_length=2048)


class WebhookConfigResponse(BaseModel):
    id: uuid.UUID
    client_id: str
    url: str
    is_active: bool

    model_config = {"from_attributes": True}


# ---------- API Key Admin ----------
class APIKeyCreateRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=128)
    name: str | None = None
    rate_limit: int = Field(default=100, ge=1, le=10000)


class APIKeyCreateResponse(BaseModel):
    id: uuid.UUID
    client_id: str
    name: str | None
    raw_key: str  # only returned on creation
    rate_limit: int

    model_config = {"from_attributes": True}


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    client_id: str
    name: str | None
    is_active: bool
    rate_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- LLM Result (internal) ----------
class LLMResult(BaseModel):
    category: str = "unknown"
    confidence: float = 0.0
    summary: str = ""
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    key_entities: dict[str, Any] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)


# ---------- Parse Result (internal) ----------
class ParseResult(BaseModel):
    text: str
    page_count: int = 0
    method: str = ""
