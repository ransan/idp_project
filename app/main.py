from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import dispose_engine, get_db
from app.models import Document
from app.routers import documents, webhooks
from app.routers.admin import router as admin_router
from app.routers.auth_router import router as auth_router
from app.schemas import (
    CategoryCount,
    HealthResponse,
    StatsResponse,
    StatusCount,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(
    title="AI Document Processing Pipeline",
    description="Intelligent document classification, extraction, and analysis API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter state
app.state.limiter = limiter

# Register routers
app.include_router(documents.router)
app.include_router(webhooks.router)
app.include_router(admin_router)
app.include_router(auth_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    return HealthResponse(status="ok", version=settings.APP_VERSION)


@app.get("/api/v1/stats", tags=["system"], response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Count by status
    status_result = await db.execute(
        select(Document.status, func.count()).group_by(Document.status)
    )
    by_status = [
        StatusCount(
            status=row[0].value if hasattr(row[0], "value") else str(row[0]),
            count=row[1],
        )
        for row in status_result.all()
    ]

    # Count by category
    cat_result = await db.execute(
        select(Document.category, func.count())
        .where(Document.category.isnot(None))
        .group_by(Document.category)
    )
    by_category = [
        CategoryCount(
            category=row[0].value if hasattr(row[0], "value") else str(row[0]),
            count=row[1],
        )
        for row in cat_result.all()
    ]

    total = sum(s.count for s in by_status)

    return StatsResponse(
        total_documents=total,
        by_status=by_status,
        by_category=by_category,
    )
