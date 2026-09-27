# Warp Ladger 🔷

**Commercial Smart Accounting SaaS Platform**

A production-ready, multi-tenant accounting platform built with FastAPI, Next.js, PostgreSQL, and Redis.

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- [Make](https://www.gnu.org/software/make/) (optional but recommended)

### 1. Clone and configure
```bash
git clone <repo-url>
cd Ladger
cp .env.example .env
# Edit .env and set SECRET_KEY and passwords
```

### 2. Start everything
```bash
make dev
# OR without Make:
docker-compose up --build -d
```

### 3. Run migrations and seed
```bash
make migrate
make seed
```

### 4. Open services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| API Docs (ReDoc) | http://localhost:8000/api/redoc |
| MailHog | http://localhost:8025 |
| MinIO Console | http://localhost:9001 |

---

## Architecture

```
Warp Ladger Monorepo
├── apps/web/              Next.js 15 frontend
├── backend/               FastAPI Python backend
│   ├── app/
│   │   ├── auth/          Authentication & sessions
│   │   ├── users/         User profile management
│   │   ├── organisations/ Multi-tenant organisation management
│   │   ├── memberships/   Org ↔ User relationships
│   │   ├── roles/         Role management
│   │   ├── permissions/   Fine-grained permissions
│   │   ├── invitations/   Email-based org invitations
│   │   ├── audit/         Audit log
│   │   ├── files/         File storage abstraction
│   │   ├── settings/      Org & user settings
│   │   ├── security/      Rate limiting, CSRF, headers
│   │   ├── database/      SQLAlchemy async engine
│   │   └── core/          Config, dependencies, logging
│   ├── migrations/        Alembic migrations
│   └── tests/             Pytest test suite
├── packages/
│   └── shared-types/      Shared TypeScript types
├── infrastructure/
│   ├── docker/            Dockerfiles
│   └── scripts/           Seed scripts
└── docs/                  Architecture & security docs
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2, Pydantic v2 |
| Database | PostgreSQL 16 |
| Cache / Sessions | Redis 7 |
| File Storage | MinIO (dev), S3 / Cloudflare R2 (prod) |
| Auth | JWT (HttpOnly cookies), Argon2id |
| Migrations | Alembic |
| Local Email | MailHog |
| Container | Docker & Docker Compose |

## Security

- Passwords hashed with **Argon2id**
- JWT access tokens (15 min) + rotating refresh tokens (7 days)
- All tokens stored in **HttpOnly, Secure, SameSite=Strict** cookies
- Refresh tokens hashed in database (revocable)
- **Multi-tenant isolation**: every resource carries `organisation_id`; every request validates membership + role + permission
- Rate limiting (Redis sliding window) on auth and API endpoints
- CSRF protection for cookie-authenticated endpoints
- Security headers (HSTS, X-Frame-Options, CSP)
- Structured audit log for all mutations

## Development Commands

```bash
make help           # Show all commands
make dev            # Start stack
make migrate        # Run migrations
make seed           # Seed roles, permissions, super-admin
make test           # Run test suite
make lint           # Lint all code
make fmt            # Format code
make shell-backend  # Shell into backend
make shell-db       # PostgreSQL shell
make clean          # Remove all containers + volumes
```

## Environment Variables

See [`.env.example`](.env.example) for all configuration options.

---

## Phase Roadmap

- **Phase 1** ✅ Foundation (auth, multi-tenancy, RBAC, audit, file storage)
- **Phase 2** — Invoicing (sales invoices, PDF generation)
- **Phase 3** — Expenses (supplier bills, purchase orders)
- **Phase 4** — Banking (bank feeds, reconciliation)
- **Phase 5** — Reporting (P&L, balance sheet, cash flow)
- **Phase 6** — Tax (VAT returns, MTD)
- **Phase 7** — Payroll

---

## License

Proprietary — © Warp Ladger. All rights reserved.
