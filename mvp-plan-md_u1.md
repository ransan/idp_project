# AI-Powered Document Processing Pipeline — MVP Plan

> **Target clients:** Law firms, finance companies, logistics providers  
> **Developer:** Solo developer  
> **Timeline:** 8 weeks to beta  
> **Monthly cost:** ~$50–80 (VPS + Claude API)

---

## 1. User Stories

### 1.1 Core Personas

| Persona | Role | Pain Point |
|---|---|---|
| **Sarah** | Paralegal at a law firm | Manually reads 50+ contracts/week to extract key dates, clauses, and parties |
| **Raj** | Accounts payable analyst | Manually keys in invoice data from PDFs into the accounting system |
| **Lena** | Logistics operations manager | Tracks shipments across carriers by reading manifests and cross-referencing |
| **Admin (any vertical)** | IT admin / team lead | Needs to onboard the tool, manage API keys, and monitor usage |

### 1.2 User Stories — Document Upload & Processing

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-01 | User | Upload a single PDF/DOCX/image via the dashboard | The system processes it without manual steps | Must | 1 |
| US-02 | User | Upload up to 20 documents in a single batch | I can process a day's worth of paperwork at once | Must | 1 |
| US-03 | User | See a real-time status indicator (uploaded → parsing → processing → completed/failed) | I know exactly where my document is in the pipeline | Must | 2 |
| US-04 | User | Reprocess a failed document with one click | Transient errors don't require re-uploading | Should | 4 |
| US-05 | User | Receive a webhook notification when processing completes | My downstream systems can react automatically | Should | 6 |

### 1.3 User Stories — Classification & Extraction

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-06 | Paralegal (Sarah) | Have contracts auto-classified and key clauses extracted (parties, dates, governing law, termination conditions) | I skip 30 minutes of manual reading per contract | Must | 3 |
| US-07 | AP Analyst (Raj) | Have invoices auto-parsed into vendor, line items, totals, and due dates | I can import structured data directly into our accounting software | Must | 3 |
| US-08 | Logistics Manager (Lena) | Have shipping manifests parsed into shipper, consignee, origin, destination, items, and tracking numbers | I can cross-reference shipments without reading every manifest | Must | 3 |
| US-09 | User | See a confidence score for each classification | I can prioritize manual review for low-confidence results | Should | 3 |
| US-10 | User | Get a 2–4 sentence summary of any document | I can decide whether to read the full document | Must | 4 |

### 1.4 User Stories — Risk Flags & Entities

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-11 | Paralegal (Sarah) | Be alerted to contract deadlines within 30 days | I never miss a renewal or termination window | Must | 4 |
| US-12 | AP Analyst (Raj) | Be flagged when an invoice has missing fields (no PO number, no due date) | I can catch errors before they enter the payment system | Must | 4 |
| US-13 | User | See all extracted entities (people, organizations, dates, amounts, locations) in a structured view | I can quickly find who, what, when, and how much | Should | 4 |
| US-14 | Logistics Manager (Lena) | Be alerted to anomalies (weight mismatches, missing tracking numbers) | I can flag problems before shipment | Should | 4 |

### 1.5 User Stories — Dashboard & Search

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-15 | User | Filter documents by status (completed, failed, processing) | I can find what needs attention | Must | 5 |
| US-16 | User | Filter documents by category (invoice, contract, report, etc.) | I can review all documents of a specific type | Must | 5 |
| US-17 | User | Filter documents by client/project | I can scope results to a specific engagement | Should | 5 |
| US-18 | User | Export extracted data as CSV or JSON | I can import results into Excel, accounting software, or other tools | Should | 5 |
| US-19 | User | View a detailed breakdown of one document (summary, fields, entities, flags) | I get the full picture without opening the original file | Must | 5 |

### 1.6 User Stories — Multi-Tenancy & Admin

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-20 | Admin | Create and revoke API keys for my team or clients | Each user/system has scoped access | Must | 6 |
| US-21 | Admin | See usage stats (documents processed, by category, by client) | I can track adoption and plan for scale | Should | 6 |
| US-22 | Admin | Set rate limits per API key | No single client can overload the system | Should | 6 |
| US-23 | User | Only see documents belonging to my client_id | Data from other clients is never visible to me | Must | 6 |

### 1.7 User Stories — Integration & API

| ID | As a... | I want to... | So that... | Priority | Week |
|---|---|---|---|---|---|
| US-24 | Developer | Access all features via a REST API with Swagger docs | I can integrate document processing into my own systems | Must | 1 |
| US-25 | Developer | Send a document via API and poll for results | I can build automated ingestion pipelines | Must | 2 |
| US-26 | Developer | Receive structured JSON responses with consistent schemas | Parsing results is predictable and reliable | Must | 3 |
| US-27 | Developer | Configure a webhook URL to receive completion callbacks | My pipeline doesn't need to poll | Should | 6 |

### 1.8 Acceptance Criteria Summary

| Metric | Target |
|---|---|
| Classification accuracy | ≥ 90% across all 6 document types |
| Field extraction accuracy | ≥ 85% for key fields (amounts, dates, parties) |
| Processing time (single doc) | < 15 seconds for a 10-page PDF |
| Upload-to-result (batch of 20) | < 5 minutes |
| System uptime | ≥ 99% during beta |
| Supported formats | PDF, DOCX, PNG, JPG, JPEG, TIFF |

### 1.9 User Story Map (by sprint)

```
            Week 1–2          Week 3–4             Week 5–6           Week 7–8
           Foundation        AI Pipeline           UI & Auth          Ship & Beta
          ┌───────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐
Must Have │ US-01,02   │    │ US-06,07,08  │    │ US-15,16,19  │    │ Deploy     │
          │ US-03,24   │    │ US-10,11,12  │    │ US-20,23     │    │ Onboard    │
          │ US-25      │    │ US-26        │    │              │    │ pilots     │
          ├───────────┤    ├──────────────┤    ├──────────────┤    ├────────────┤
Should    │            │    │ US-09,13,14  │    │ US-17,18     │    │ Feedback   │
Have      │            │    │ US-04        │    │ US-21,22     │    │ loop       │
          │            │    │              │    │ US-05,27     │    │            │
          └───────────┘    └──────────────┘    └──────────────┘    └────────────┘
```

---

## 2. Tech Stack

| Layer | Choice | Why | Cost |
|---|---|---|---|
| **Backend** | FastAPI (Python 3.12) | Async, auto-docs, massive ML ecosystem | Free |
| **LLM** | Claude API (Sonnet) | Best price-to-quality for document understanding | ~$3/1M input tokens |
| **LLM (dev/test)** | Ollama + Mistral 7B | Local inference to save API costs during development | Free |
| **Document Parsing** | PyMuPDF, python-docx, pytesseract | PDF, Word, scanned image support — all open source | Free |
| **Database** | PostgreSQL 16 + pgvector | Relational + vector search in one DB | Free |
| **Task Queue** | Celery + Redis | Async document processing, retries, rate limiting | Free |
| **Frontend** | React + Vite + Tailwind | Lightweight dashboard for upload and results | Free |
| **File Storage** | Local → MinIO (S3-compatible) | Self-hosted, easy migration to AWS S3 later | Free |
| **Deployment** | Docker Compose → Hetzner VPS | Single-command deploy, €5–10/mo for CX22 | ~$10/mo |
| **CI/CD** | GitHub Actions | Auto-test + deploy on push to main | Free tier |
| **Monitoring** | Sentry (free tier) + structured logging | Error tracking without infrastructure overhead | Free |

### Why this stack over alternatives

- **FastAPI over Django/Flask:** Async-native means file uploads don't block other requests. Auto-generated OpenAPI docs let clients integrate without you writing documentation.
- **Claude Sonnet over GPT-4o:** Superior structured output compliance for the extraction prompts, and native PDF/image understanding in case you need it later. Competitive pricing.
- **PostgreSQL over MongoDB:** Your data is inherently relational (documents belong to clients, have statuses, categories). pgvector adds similarity search without a second database.
- **Celery over background threads:** Proper retry logic, dead-letter queues, and you can scale workers independently from the API server.

---

## 3. System Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│   React UI   │────▶│   FastAPI (API)   │────▶│   Redis     │
│  Dashboard   │◀────│   /api/v1/...     │     │   (broker)  │
└──────────────┘     └──────────────────┘     └──────┬──────┘
                              │                       │
                              ▼                       ▼
                     ┌──────────────────┐     ┌─────────────┐
                     │   PostgreSQL     │     │   Celery     │
                     │   + pgvector     │◀────│   Worker     │
                     └──────────────────┘     └──────┬──────┘
                                                     │
                              ┌───────────────────────┤
                              ▼                       ▼
                     ┌──────────────────┐     ┌─────────────┐
                     │  Document Parser │     │  Claude API  │
                     │  PDF/DOCX/OCR    │     │  (Sonnet)    │
                     └──────────────────┘     └─────────────┘
```

### Request flow

1. Client uploads a file via `POST /api/v1/documents/upload`
2. FastAPI validates, stores the file, creates a DB record with status `uploaded`
3. A Celery task is dispatched to Redis
4. The worker picks up the task:
   - **Parse:** Extract raw text (PyMuPDF for PDF, python-docx for Word, Tesseract for scanned images)
   - **Process:** Send text to Claude API with a structured prompt
   - **Store:** Save classification, extracted data, summary, entities, and flags to PostgreSQL
5. Client polls `GET /api/v1/documents/{id}` or receives a webhook callback

---

## 4. Project Structure

```
docpipeline/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, middleware, router registration
│   ├── config.py               # Pydantic settings from .env
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── models.py               # Document model (status, category, extracted_data)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── tasks.py                # Celery task definitions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parser.py           # PDF, DOCX, OCR text extraction
│   │   ├── llm.py              # Claude API integration + prompt
│   │   └── pipeline.py         # Orchestrates parse → LLM → store
│   └── routers/
│       ├── __init__.py
│       ├── documents.py        # Upload, list, get, reprocess endpoints
│       └── webhooks.py         # Callback notification endpoints
├── frontend/                   # React dashboard (Week 5)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadZone.jsx
│   │   │   ├── DocumentList.jsx
│   │   │   └── DocumentDetail.jsx
│   │   └── api.js
│   └── package.json
├── tests/
│   ├── test_parser.py
│   ├── test_llm.py
│   ├── test_pipeline.py
│   └── test_api.py
├── alembic/                    # DB migrations
│   ├── env.py
│   └── versions/
├── sample_docs/                # Test corpus (invoices, contracts, etc.)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Database Schema

```sql
CREATE TYPE doc_status AS ENUM (
    'uploaded', 'parsing', 'processing', 'completed', 'failed'
);

CREATE TYPE doc_category AS ENUM (
    'invoice', 'contract', 'report', 'legal_brief',
    'financial_statement', 'shipping_manifest', 'unknown'
);

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(512) NOT NULL,
    original_name   VARCHAR(512) NOT NULL,
    file_size       INTEGER,
    mime_type       VARCHAR(128),
    storage_path    VARCHAR(1024) NOT NULL,

    -- Processing state
    status          doc_status DEFAULT 'uploaded',
    error_message   TEXT,

    -- Extracted content
    raw_text        TEXT,
    page_count      INTEGER,

    -- LLM results
    category        doc_category,
    confidence      FLOAT,
    summary         TEXT,
    extracted_data  JSONB,          -- structured fields per doc type
    key_entities    JSONB,          -- people, orgs, dates, amounts
    flags           JSONB,          -- anomalies, risks, deadlines

    -- Multi-tenancy
    client_id       VARCHAR(128),
    tags            JSONB DEFAULT '[]',

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    processing_time_ms INTEGER
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_client ON documents(client_id);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
```

---

## 6. API Endpoints

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload single document |
| `POST` | `/api/v1/documents/upload/batch` | Upload up to 20 documents |
| `GET` | `/api/v1/documents/{id}` | Get document + results |
| `GET` | `/api/v1/documents/` | List with filters (status, category, client_id, pagination) |
| `POST` | `/api/v1/documents/{id}/reprocess` | Re-run pipeline on a document |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + file |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Auto-generated Swagger UI |
| `GET` | `/api/v1/stats` | Processing stats (counts by status/category) |

### Example response for `GET /api/v1/documents/{id}`

```json
{
  "id": "a1b2c3d4-...",
  "original_name": "invoice_2024_march.pdf",
  "status": "completed",
  "category": "invoice",
  "confidence": 0.97,
  "summary": "Invoice #INV-2024-0342 from Acme Corp to Wayne Enterprises for $14,500 in consulting services, due April 15, 2024. Net-30 payment terms.",
  "extracted_data": {
    "vendor": "Acme Corp",
    "buyer": "Wayne Enterprises",
    "invoice_number": "INV-2024-0342",
    "date": "2024-03-15",
    "due_date": "2024-04-15",
    "total_amount": 14500.00,
    "currency": "USD",
    "payment_terms": "Net 30",
    "line_items": [
      { "description": "Strategy consulting", "quantity": 40, "unit_price": 250, "total": 10000 },
      { "description": "Market analysis report", "quantity": 1, "unit_price": 4500, "total": 4500 }
    ]
  },
  "key_entities": {
    "people": ["John Smith"],
    "organizations": ["Acme Corp", "Wayne Enterprises"],
    "dates": ["2024-03-15", "2024-04-15"],
    "monetary_amounts": ["$14,500", "$10,000", "$4,500"],
    "locations": ["New York, NY"],
    "reference_numbers": ["INV-2024-0342"]
  },
  "flags": ["Due date is within 30 days"],
  "page_count": 2,
  "processing_time_ms": 3420,
  "created_at": "2024-03-20T10:30:00Z",
  "processed_at": "2024-03-20T10:30:03Z"
}
```

---

## 7. LLM Prompt Strategy

The core of the product is a single, well-engineered system prompt that handles classification, extraction, summarization, and risk flagging in one Claude API call.

### System prompt (condensed)

```
You are an expert document analyst for professional services.
Given raw document text, return ONLY valid JSON with:

1. CLASSIFY into: invoice | contract | report | legal_brief |
   financial_statement | shipping_manifest | unknown

2. EXTRACT structured fields per document type:
   - Invoice: vendor, buyer, invoice_number, date, due_date,
     line_items, total_amount, currency, payment_terms
   - Contract: parties, effective_date, expiration_date,
     contract_type, governing_law, key_clauses
   - Report: title, author, date, key_findings, recommendations
   - Legal Brief: case_name, court, parties, key_arguments
   - Financial Statement: entity, period, key_figures, auditor
   - Shipping Manifest: shipper, consignee, origin, destination, items

3. IDENTIFY entities: people, organizations, dates,
   monetary_amounts, locations, reference_numbers

4. SUMMARIZE in 2-4 sentences.

5. FLAG: anomalies, risks, deadlines within 30 days,
   missing information, compliance concerns.
```

### Cost estimation per document

- Average document: ~2,000–5,000 tokens input + ~500–1,000 tokens output
- Claude Sonnet cost: ~$0.003–0.01 per document
- At 1,000 docs/month: ~$3–10/month in API costs

### Prompt optimization tips

- Keep the JSON schema explicit — Claude follows it precisely
- Use the "beginning + end" truncation strategy for long documents (legal contracts can be 50+ pages, but key terms are in the first and last sections)
- Cache the system prompt (Anthropic prompt caching reduces cost by ~90% for repeated system prompts)

---

## 8. Development Plan (8 Weeks)

### Week 1 — Foundation
**User stories covered:** US-01, US-02, US-24

**Goal:** Upload a file and see it in the database.

- [ ] Initialize git repo, Python 3.12 virtual environment
- [ ] Create `docker-compose.yml` (PostgreSQL, Redis, API, Worker)
- [ ] Set up FastAPI app skeleton with health check
- [ ] Define SQLAlchemy models + Alembic migrations
- [ ] Implement `POST /upload` endpoint (validate, store file, create DB record)
- [ ] Implement `GET /documents/{id}` and `GET /documents/` (list with pagination)
- [ ] Write first tests (upload a file, verify DB record)

**Deliverable:** `docker-compose up` → upload a PDF via Swagger UI → see it in the DB.

---

### Week 2 — Document Parsing
**User stories covered:** US-03, US-25

**Goal:** Extract clean text from any supported document type.

- [ ] Build `DocumentParser` class with PDF, DOCX, and image handlers
- [ ] Integrate Tesseract OCR for scanned PDFs (fallback when text extraction yields < 50 chars)
- [ ] Extract tables from DOCX files
- [ ] Set up Celery worker + Redis broker
- [ ] Wire upload endpoint to dispatch Celery tasks
- [ ] Add status tracking (uploaded → parsing → completed/failed)
- [ ] Test with 5+ real documents (mix of PDF types, Word, scanned images)

**Deliverable:** Upload a scanned invoice → worker extracts text → raw_text stored in DB.

---

### Week 3 — LLM Pipeline (Classification + Extraction)
**User stories covered:** US-06, US-07, US-08, US-09, US-26

**Goal:** Documents are automatically classified and structured data is extracted.

- [ ] Build `LLMService` class with Claude API integration
- [ ] Craft and iterate the system prompt (test against 10+ sample docs)
- [ ] Implement JSON response parsing with error handling
- [ ] Add retry logic with exponential backoff (tenacity)
- [ ] Handle long documents (truncation with beginning + end preservation)
- [ ] Build `Pipeline` orchestrator (parse → LLM → store)
- [ ] Update status flow (uploaded → parsing → processing → completed)

**Deliverable:** Upload an invoice → get back category, confidence, extracted line items, and entities.

---

### Week 4 — Summarization, Flags & Testing
**User stories covered:** US-04, US-10, US-11, US-12, US-13, US-14

**Goal:** Full pipeline produces complete, reliable results.

- [ ] Validate summarization quality across all document types
- [ ] Test flag detection (deadlines, missing info, anomalies)
- [ ] Tune prompts for each document category (contracts need different emphasis than invoices)
- [ ] Add processing time tracking
- [ ] Build the reprocess endpoint for failed documents
- [ ] Create a test corpus: 3+ documents per category (18+ total)
- [ ] Run full pipeline on entire corpus, fix edge cases
- [ ] Add structured logging throughout the pipeline

**Deliverable:** All 6 document types process correctly with >90% field accuracy.

---

### Week 5 — Dashboard UI
**User stories covered:** US-15, US-16, US-17, US-18, US-19

**Goal:** Non-technical users can upload documents and view results.

- [ ] Scaffold React app with Vite + Tailwind
- [ ] Build drag-and-drop upload zone (single + batch)
- [ ] Build document list view with status badges and filters
- [ ] Build document detail view (summary, extracted data, entities, flags)
- [ ] Add auto-refresh polling for processing status
- [ ] Add CSV/JSON export for extracted data
- [ ] Wire up CORS between frontend and API

**Deliverable:** Upload 5 invoices via browser → see them process in real-time → view extracted data.

---

### Week 6 — Multi-Tenancy & Auth
**User stories covered:** US-05, US-20, US-21, US-22, US-23, US-27

**Goal:** Multiple clients can use the system with data isolation.

- [ ] Implement API key authentication middleware
- [ ] Add `client_id` scoping to all queries (data isolation)
- [ ] Build simple admin endpoint for creating API keys
- [ ] Add rate limiting per client (slowapi or custom middleware)
- [ ] Add per-client usage tracking (documents processed, API calls)
- [ ] Add webhook callback system (notify client when processing completes)
- [ ] Write integration tests for multi-tenant scenarios

**Deliverable:** Two different API keys upload docs → each only sees their own data.

---

### Week 7 — Deploy & Harden
**User stories covered:** Non-functional (reliability, security, performance)

**Goal:** Production-ready system running on a server.

- [ ] Provision Hetzner CX22 VPS (2 vCPU, 4GB RAM, ~€5/mo)
- [ ] Set up Docker Compose for production (no `--reload`, proper logging)
- [ ] Configure nginx reverse proxy with Let's Encrypt HTTPS
- [ ] Set up PostgreSQL backups (pg_dump cron to S3/MinIO)
- [ ] Add Sentry for error tracking (free tier)
- [ ] Configure file size limits and request throttling
- [ ] Add health check endpoint monitoring (UptimeRobot, free)
- [ ] Security hardening (CORS lockdown, input sanitization, file type validation)
- [ ] Load test with 50 concurrent document uploads

**Deliverable:** `https://api.yourdomain.com/docs` is live with HTTPS.

---

### Week 8 — Beta Launch
**User stories covered:** Validation of all Must-have stories with real users

**Goal:** Real users processing real documents.

- [ ] Onboard 2–3 pilot clients (ideally one from each vertical: law, finance, logistics)
- [ ] Create onboarding guide (API key, upload flow, webhook setup)
- [ ] Add a simple landing page explaining the product
- [ ] Set up feedback collection (Typeform or simple Google Form)
- [ ] Monitor first 100 real documents for accuracy issues
- [ ] Hot-fix prompt or parsing bugs based on real-world data
- [ ] Document API with examples for each document type
- [ ] Set up billing tracking (count docs per client for future invoicing)

**Deliverable:** Pilot clients are uploading real documents and getting useful results.

---

## 9. Post-MVP Roadmap (Months 3–6)

Once the beta is stable and you have client feedback:

- **Semantic search** — Use pgvector embeddings to let clients search across documents by meaning ("find all contracts mentioning liability caps over $1M")
- **Custom extraction templates** — Let clients define their own fields to extract per document type
- **Batch analytics dashboard** — Charts showing document volume, category distribution, flagged items over time
- **Email/S3 ingestion** — Auto-process documents sent to an email address or dropped in an S3 bucket
- **Comparison mode** — Compare two versions of a contract and highlight differences
- **SOC 2 / compliance** — Required for enterprise law firm and finance clients
- **Usage-based billing** — Stripe integration, charge per document processed

---

## 10. Cost Breakdown

### Monthly operating costs (MVP)

| Item | Cost |
|---|---|
| Hetzner CX22 VPS (2 vCPU, 4GB RAM, 40GB SSD) | ~$10 |
| Domain name | ~$1 |
| Claude API (~500 docs/month) | ~$5–15 |
| Sentry (free tier) | $0 |
| UptimeRobot (free tier) | $0 |
| GitHub (free tier) | $0 |
| **Total** | **~$16–26/month** |

### At scale (1,000+ docs/month)

| Item | Cost |
|---|---|
| Hetzner CX32 VPS (4 vCPU, 8GB RAM) | ~$18 |
| Claude API (~2,000 docs/month) | ~$20–40 |
| S3 storage (50GB) | ~$1 |
| **Total** | **~$40–60/month** |

### Pricing suggestion for clients

- Charge $0.10–0.50 per document depending on complexity
- At 2,000 docs/month with $0.25/doc = $500/month revenue vs ~$50 cost = **90% margin**

---

## 11. Key Files Reference

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app entry point, middleware, router registration |
| `app/config.py` | Environment variable management via Pydantic Settings |
| `app/models.py` | SQLAlchemy document model with status/category enums |
| `app/schemas.py` | Request/response Pydantic models |
| `app/database.py` | Async SQLAlchemy engine and session factory |
| `app/services/parser.py` | PDF, DOCX, and OCR text extraction |
| `app/services/llm.py` | Claude API integration with structured prompt |
| `app/services/pipeline.py` | Orchestrates parse → LLM → store with error handling |
| `app/tasks.py` | Celery async task definitions |
| `app/routers/documents.py` | All document CRUD and upload endpoints |
| `docker-compose.yml` | Full stack: API, worker, PostgreSQL, Redis |
| `Dockerfile` | Python 3.12 + Tesseract OCR |

---

## Quick Start

```bash
# 1. Clone and configure
git clone <your-repo>
cd docpipeline
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 2. Start everything
docker-compose up --build

# 3. Open Swagger UI
open http://localhost:8000/docs

# 4. Upload your first document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample_docs/invoice.pdf" \
  -F "client_id=test"

# 5. Check results
curl http://localhost:8000/api/v1/documents/<doc-id>
```
