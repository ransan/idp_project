# AI-Powered Document Processing Pipeline

Intelligent document classification, extraction, and analysis API for law firms, finance companies, and logistics providers.

Upload PDFs, DOCX files, or scanned images — the system automatically classifies the document type, extracts structured data, identifies entities, generates summaries, and flags risks.

## Supported Document Types

| Type | Extracted Fields |
|---|---|
| Invoice | vendor, buyer, line items, totals, due date, payment terms |
| Contract | parties, dates, governing law, key clauses, termination |
| Report | title, author, findings, recommendations |
| Legal Brief | case name, court, parties, arguments |
| Financial Statement | entity, period, revenue, expenses, figures |
| Shipping Manifest | shipper, consignee, origin, destination, items |

## Tech Stack

- **Backend:** FastAPI (Python 3.13), async
- **LLM:** Claude API (Sonnet) + Ollama/Mistral for local dev
- **Database:** PostgreSQL 16 + pgvector
- **Task Queue:** Celery + Redis
- **Document Parsing:** PyMuPDF, python-docx, Tesseract OCR
- **Auth:** API key-based with multi-tenancy
- **Storage:** Local filesystem, MinIO, or Backblaze B2

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose (for PostgreSQL and Redis)
- Tesseract OCR (`brew install tesseract` on macOS)

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd IDP-Project
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY (or set LLM_PROVIDER=ollama for local dev)
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Start infrastructure (PostgreSQL + Redis)

```bash
docker compose up postgres redis -d
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Start the Celery worker (separate terminal)

```bash
celery -A app.celery_app:celery_app worker --loglevel=info
```

### 7. Open Swagger docs

Visit [http://localhost:8000/docs](http://localhost:8000/docs)

## Running with Docker Compose (full stack)

```bash
docker compose up --build
```

This starts the API, Celery worker, PostgreSQL, and Redis together.

## Storage Backends

The project supports three storage backends, configured via the `STORAGE_BACKEND` environment variable.

### Local (default)

Files are stored on the local filesystem under `UPLOAD_DIR`.

```env
STORAGE_BACKEND=local
```

### MinIO (S3-compatible)

Stores files in a local or remote MinIO instance.

```env
STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=idp-documents
MINIO_SECURE=false
```

### Backblaze B2

Stores files in a Backblaze B2 cloud bucket using the S3-compatible API.

**Setup:**

1. Create a bucket in the [Backblaze B2 Console](https://secure.backblaze.com/b2_buckets.htm) (e.g., `DP-B01`)
2. Create an **Application Key** scoped to that bucket under *App Keys*
3. Note the **keyID** and **applicationKey**
4. Find your S3 endpoint in the bucket details (e.g., `s3.us-east-005.backblazeb2.com`)

```env
STORAGE_BACKEND=b2
B2_KEY_ID=your-key-id
B2_APPLICATION_KEY=your-application-key
B2_BUCKET=DP-B01
B2_ENDPOINT=s3.us-east-005.backblazeb2.com
B2_SECURE=true
```

## API Usage

### Upload a document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample_docs/invoice.pdf" \
  -F "client_id=test"
```

### Check results

```bash
curl http://localhost:8000/api/v1/documents/<document-id>
```

### List documents with filters

```bash
curl "http://localhost:8000/api/v1/documents/?status=completed&category=invoice&page=1&size=20"
```

### Batch upload (up to 20 files)

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload/batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_parser.py -v
```

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings from .env
├── database.py          # Async SQLAlchemy engine
├── models.py            # Document, APIKey, WebhookConfig models
├── schemas.py           # Request/response Pydantic schemas
├── auth.py              # API key authentication
├── celery_app.py        # Celery configuration
├── tasks.py             # Async task definitions
├── services/
│   ├── parser.py        # PDF, DOCX, OCR text extraction
│   ├── llm.py           # Claude + Ollama integration
│   └── pipeline.py      # Parse → LLM → store orchestrator
└── routers/
    ├── documents.py     # Document CRUD + upload endpoints
    ├── webhooks.py      # Webhook configuration
    └── admin.py         # API key management
tests/                   # 112 unit tests (82% coverage)
```

## Environment Variables

See [.env.example](.env.example) for all available configuration. Key variables:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://idp:idp_secret@localhost:5432/idp_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | `claude` or `ollama` | `claude` |
| `ANTHROPIC_API_KEY` | Claude API key | — |
| `OLLAMA_MODEL` | Local model name | `mistral` |
| `MAX_FILE_SIZE_MB` | Upload size limit | `50` |
| `MAX_BATCH_SIZE` | Max files per batch | `20` |
| `STORAGE_BACKEND` | `local`, `minio`, or `b2` | `local` |

## License

MIT