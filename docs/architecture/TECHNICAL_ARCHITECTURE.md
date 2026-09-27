# Technical Architecture

## 1. System Topology

```text
[ Browser / Client ]
        │
        │ HTTPS (TLS 1.3)
        ▼
[ Next.js 15 Web Frontend ] (React 19, Server & Client Components, Tailwind CSS)
        │
        │ API Requests with HttpOnly Secure Cookies
        ▼
[ FastAPI Async Backend Service ] (Python 3.11+, SQLAlchemy 2 Async Engine)
        ├── Security & Auth Middleware (SecurityHeaders, RequestID, Timing, RateLimit)
        ├── Central Router Matrix (/api/v1/auth, /organisations, /members, /files, /audit)
        ├── RBAC Enforcement Layer (8 Canonical Roles, Permission Checks)
        └── Domain Services (Auth, Organisations, Memberships, Files, Audit)
        │                 │                 │
        ▼                 ▼                 ▼
 [ PostgreSQL 16 ]   [ Redis 7 ]    [ MinIO / S3 ]
  Primary Relational  Cache, Sessions Private Encrypted
  ACID Data Store     Rate Limiting   Object Storage
```

## 2. Component Stack

- **Frontend App**: Next.js 15 (App Router), TypeScript, Tailwind CSS, Lucide icons.
- **Backend Framework**: FastAPI (high-throughput async ASGI).
- **ORM & Database Driver**: SQLAlchemy 2.0 with `asyncpg` for async PostgreSQL connectivity and `aiosqlite` for fast in-memory testing.
- **Database Migrations**: Alembic.
- **Serialization & Validation**: Pydantic v2.
- **Password Security**: Argon2id via `argon2-cffi`.
- **Token Infrastructure**: `python-jose` for JWT creation and signature verification.
- **Background Tasks**: Redis worker queue for asynchronous email delivery, file virus scanning, and future AI document OCR processing.
