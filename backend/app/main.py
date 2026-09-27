"""
Warp Ladger — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    TimingMiddleware,
    TrailingSlashMiddleware,
)
from app.database.base import close_db, init_db

# ─── Module routers ──────────────────────────────────────────
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.organisations.router import router as organisations_router
from app.memberships.router import router as memberships_router
from app.roles.router import router as roles_router
from app.permissions.router import router as permissions_router
from app.invitations.router import router as invitations_router, public_router as public_invitations_router
from app.audit.router import router as audit_router
from app.files.router import router as files_router
from app.settings.router import router as settings_router
from app.contacts.router import router as contacts_router
from app.payment_terms.router import router as payment_terms_router
from app.invoices.router import router as invoices_router, tax_router as tax_rates_router
from app.bills.router import router as bills_router
from app.documents.router import router as documents_router
from app.payments.router import bank_accounts_router, payments_router
from app.ledger.router import (
    accounting_settings_router,
    accounts_router,
    journals_router,
    ledger_reports_router,
)
from app.reports.router import reports_router

log = structlog.get_logger(__name__)


# ─── Lifespan ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("warp_ladger_starting", version=settings.APP_VERSION, env=settings.APP_ENV)
    await init_db()
    yield
    await close_db()
    log.info("warp_ladger_shutdown")


# ─── App factory ─────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Warp Ladger API",
        description="Commercial Smart Accounting SaaS Platform — Phase 1 API",
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
        openapi_url="/api/openapi.json" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost first) ──────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TrailingSlashMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.APP_ENV == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # ── Exception handlers ───────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────
    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
    app.include_router(users_router, prefix=f"{api_prefix}/users", tags=["Users"])
    app.include_router(
        organisations_router, prefix=f"{api_prefix}/organisations", tags=["Organisations"]
    )
    app.include_router(
        memberships_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/members",
        tags=["Memberships"],
    )
    app.include_router(
        roles_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/roles",
        tags=["Roles"],
    )
    app.include_router(
        permissions_router, prefix=f"{api_prefix}/permissions", tags=["Permissions"]
    )
    app.include_router(
        invitations_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/invitations",
        tags=["Invitations"],
    )
    app.include_router(
        public_invitations_router,
        prefix=f"{api_prefix}/invitations",
        tags=["Invitations"],
    )
    app.include_router(
        audit_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/audit",
        tags=["Audit Log"],
    )
    app.include_router(files_router, prefix=f"{api_prefix}/files", tags=["Files"])
    app.include_router(settings_router, prefix=f"{api_prefix}/settings", tags=["Settings"])
    app.include_router(
        contacts_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/contacts",
        tags=["Contacts"],
    )
    app.include_router(
        payment_terms_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/payment-terms",
        tags=["Payment Terms"],
    )
    app.include_router(
        invoices_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/invoices",
        tags=["Sales Invoices"],
    )
    app.include_router(
        tax_rates_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/tax-rates",
        tags=["Tax Rates"],
    )
    app.include_router(
        bills_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/bills",
        tags=["Supplier Bills"],
    )
    app.include_router(
        documents_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/documents",
        tags=["Smart Document Capture"],
    )
    app.include_router(
        payments_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/payments",
        tags=["Payments & Allocations"],
    )
    app.include_router(
        bank_accounts_router,
        prefix=f"{api_prefix}/organisations/{{org_id}}/bank-accounts",
        tags=["Bank Accounts"],
    )
    app.include_router(accounts_router)
    app.include_router(journals_router)
    app.include_router(ledger_reports_router)
    app.include_router(accounting_settings_router)
    app.include_router(reports_router)


    # ── Health check ─────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


app = create_app()
