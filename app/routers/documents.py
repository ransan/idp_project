import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_client
from app.config import settings
from app.database import get_db
from app.models import APIKey, DocCategory, DocStatus, Document
from app.schemas import (
    BatchUploadResponse,
    CategoryCount,
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    DocumentUploadResponse,
    ReprocessResponse,
    StatsResponse,
    StatusCount,
)
from app.services.storage import storage
from app.tasks import process_batch_task, process_document_task

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _validate_file(file: UploadFile) -> None:
    # Check extension
    if file.filename:
        ext = Path(file.filename).suffix.lower().lstrip(".")
        if ext not in settings.allowed_extensions_set:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: .{ext}. Allowed: {settings.ALLOWED_EXTENSIONS}",
            )
    # Content-type based check as fallback
    if file.content_type and "octet-stream" not in file.content_type:
        allowed_mimes = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/tiff",
        }
        if file.content_type not in allowed_mimes:
            raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")


async def _save_file(file: UploadFile) -> tuple[str, str, int]:
    """Save uploaded file to storage backend. Returns (original_ext_name, storage_key, file_size)."""
    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    filename = file.filename or f"{uuid.uuid4()}"
    storage_key = storage.save(content, filename)

    return filename, storage_key, file_size


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    client_id: str | None = Query(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    _validate_file(file)
    original_name, storage_key, file_size = await _save_file(file)

    # Use authenticated client_id if available, else query param
    resolved_client_id = getattr(request.state, "client_id", None) or client_id

    doc = Document(
        filename=original_name,
        original_name=file.filename or original_name,
        file_size=file_size,
        mime_type=file.content_type,
        storage_path=storage_key,
        client_id=resolved_client_id,
    )
    db.add(doc)
    await db.flush()

    # Dispatch async processing
    process_document_task.delay(str(doc.id))

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        original_name=doc.original_name,
        status=doc.status.value if isinstance(doc.status, DocStatus) else doc.status,
        created_at=doc.created_at,
    )


@router.post("/upload/batch", response_model=BatchUploadResponse, status_code=201)
async def upload_batch(
    files: list[UploadFile] = File(...),
    client_id: str | None = Query(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum batch size: {settings.MAX_BATCH_SIZE}",
        )

    resolved_client_id = getattr(request.state, "client_id", None) or client_id
    documents = []

    for file in files:
        _validate_file(file)
        original_name, storage_key, file_size = await _save_file(file)

        doc = Document(
            filename=original_name,
            original_name=file.filename or original_name,
            file_size=file_size,
            mime_type=file.content_type,
            storage_path=storage_key,
            client_id=resolved_client_id,
        )
        db.add(doc)
        await db.flush()
        documents.append(doc)

    doc_ids = [str(doc.id) for doc in documents]
    process_batch_task.delay(doc_ids)

    return BatchUploadResponse(
        documents=[
            DocumentUploadResponse(
                id=doc.id,
                filename=doc.filename,
                original_name=doc.original_name,
                status=doc.status.value if isinstance(doc.status, DocStatus) else doc.status,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    query = select(Document).where(Document.id == document_id)

    # Scope by client if authenticated
    auth_client_id = getattr(request.state, "client_id", None) if request else None
    if auth_client_id:
        query = query.where(Document.client_id == auth_client_id)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return _doc_to_response(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    query = select(Document)

    # Scope by authenticated client_id
    auth_client_id = getattr(request.state, "client_id", None) if request else None
    if auth_client_id:
        query = query.where(Document.client_id == auth_client_id)
    elif client_id:
        query = query.where(Document.client_id == client_id)

    if status:
        query = query.where(Document.status == status)
    if category:
        query = query.where(Document.category == category)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentSummary(
                id=doc.id,
                original_name=doc.original_name,
                status=doc.status.value if isinstance(doc.status, DocStatus) else doc.status,
                category=doc.category.value if doc.category and hasattr(doc.category, "value") else doc.category,
                confidence=doc.confidence,
                client_id=doc.client_id,
                created_at=doc.created_at,
                processing_time_ms=doc.processing_time_ms,
            )
            for doc in docs
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_document(
    document_id: uuid.UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    query = select(Document).where(Document.id == document_id)
    auth_client_id = getattr(request.state, "client_id", None) if request else None
    if auth_client_id:
        query = query.where(Document.client_id == auth_client_id)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Reset state
    doc.status = DocStatus.UPLOADED
    doc.error_message = None
    doc.raw_text = None
    doc.page_count = None
    doc.category = None
    doc.confidence = None
    doc.summary = None
    doc.extracted_data = None
    doc.key_entities = None
    doc.flags = None
    doc.processed_at = None
    doc.processing_time_ms = None
    await db.flush()

    process_document_task.delay(str(doc.id))

    return ReprocessResponse(
        id=doc.id,
        status="uploaded",
        message="Document queued for reprocessing",
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    _auth: APIKey | None = Depends(get_optional_client),
):
    query = select(Document).where(Document.id == document_id)
    auth_client_id = getattr(request.state, "client_id", None) if request else None
    if auth_client_id:
        query = query.where(Document.client_id == auth_client_id)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from storage backend
    if doc.storage_path:
        try:
            storage.delete(doc.storage_path)
        except Exception:
            pass  # Don't fail deletion if storage cleanup fails

    await db.execute(sa_delete(Document).where(Document.id == document_id))


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_name=doc.original_name,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status.value if isinstance(doc.status, DocStatus) else doc.status,
        error_message=doc.error_message,
        page_count=doc.page_count,
        category=doc.category.value if doc.category and hasattr(doc.category, "value") else doc.category,
        confidence=doc.confidence,
        summary=doc.summary,
        extracted_data=doc.extracted_data,
        key_entities=doc.key_entities,
        flags=doc.flags,
        client_id=doc.client_id,
        tags=doc.tags,
        created_at=doc.created_at,
        processed_at=doc.processed_at,
        processing_time_ms=doc.processing_time_ms,
    )
