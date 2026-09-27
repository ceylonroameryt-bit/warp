# Product Requirements Document (PRD)

## Product Name: Warp Ladger
**Tagline**: Commercial Smart Accounting SaaS — Intelligent, Document-First, Human-Controlled AI Accounting.

---

## 1. Executive Summary & Core Product Vision

Warp Ladger is an original, commercial-grade, multi-tenant accounting platform designed for small-to-medium businesses (SMBs), accounting practices, and fast-growing enterprises.

Traditional accounting platforms are built around manual data entry followed by reconciliations. Warp Ladger flips this paradigm with a **Document-First Accounting** architecture:
1. Every business transaction originates from or binds to primary source evidence (PDF, image, scan, e-invoice, bank record).
2. Intelligent document capture (OCR + AI extraction) extracts key accounting fields with calibrated confidence scores.
3. Strict human-in-the-loop controls enforce that AI suggestions never silently modify books or execute financial submissions without explicit approval.
4. An immutable, double-entry ledger forms the bedrock of all reporting, ensuring compliance with UK GAAP, IFRS, and HMRC Making Tax Digital (MTD).

---

## 2. Strategic Objectives & Differentiators

| Strategic Pillar | Commercial Differentiator |
|---|---|
| **Document-First Workflow** | Invoices, bills, and receipts are captured, classified, and verified at ingestion. Accounting lines flow seamlessly from validated source documents. |
| **Human-Controlled AI** | AI reads, parses, classifies, and suggests matches, but **never independently approves journals, transfers funds, or submits tax returns**. |
| **Strict Multi-Tenancy & RBAC** | Absolute tenant isolation with 8 fine-grained canonical roles (`Owner`, `Administrator`, `Accountant`, `Bookkeeper`, `Approver`, `Employee`, `Auditor`, `Viewer`). |
| **Immutable Accounting Integrity** | Double-entry journals strictly maintain $\sum \text{Debits} = \sum \text{Credits}$. No silent row updates on posted financial periods; all corrections occur via audited reversal entries. |
| **Decimal Precision** | Monetary values use fixed-point `Decimal` (Python) and `NUMERIC(18, 4)` (PostgreSQL) to avoid any floating-point truncation errors. |

---

## 3. High-Level System Workflow

```text
Create Business
        ↓
Manage Team (8 Roles RBAC)
        ↓
Customers & Suppliers
        ↓
Sales Invoices (Money In)
        ↓
Supplier Bills (Money Out)
        ↓
Smart Document Capture (OCR + AI)
        ↓
Payments & Multi-Allocations
        ↓
Double-Entry Accounting Ledger
        ↓
Financial Reports (P&L, Balance Sheet, Trial Balance)
        ↓
Bank Accounts & Statement Import
        ↓
Bank Reconciliation Engine
        ↓
VAT / Tax Engine (MTD Ready)
        ↓
Automation & Rules Engine
        ↓
Integrations & Ecosystem
```

---

## 4. Complete 32-Phase Commercial Roadmap

- **Phase 0**: Product Discovery & Commercial Foundation *(This Phase)*
- **Phase 1**: Platform Foundation, Authentication & Multi-Tenancy *(This Phase)*
- **Phase 2**: Customers, Suppliers & Contact Management
- **Phase 3**: Sales Invoicing / Money In
- **Phase 4**: Supplier Bills / Money Out
- **Phase 5**: Smart Invoice & Receipt Capture
- **Phase 6**: Payments & Allocations
- **Phase 7**: Double-Entry Accounting Ledger
- **Phase 8**: Financial Reporting
- **Phase 9**: Bank Accounts & Statement Import
- **Phase 10**: Bank Reconciliation
- **Phase 11**: Credit Notes, Refunds & Financial Adjustments
- **Phase 12**: VAT / Tax Engine
- **Phase 13**: Products, Services & Item Catalogue
- **Phase 14**: Quotes & Sales Workflow
- **Phase 15**: Purchase Orders & Procurement
- **Phase 16**: Advanced Accounting Controls
- **Phase 17**: Automation & Recurring Transactions
- **Phase 18**: Commercial SaaS Plans, Billing & Entitlements
- **Phase 19**: Security, Privacy & Production Hardening
- **Phase 20**: Private Beta & Commercial Launch
- **Phase 21**: Open Banking
- **Phase 22**: HMRC / Making Tax Digital Integration
- **Phase 23**: Mobile Application
- **Phase 24**: Accountant / Bookkeeper Portal
- **Phase 25**: Public API, Webhooks & Integration Platform
- **Phase 26**: Advanced AI Financial Assistant
- **Phase 27**: Employee Expenses
- **Phase 28**: Inventory Management
- **Phase 29**: Projects & Time Tracking
- **Phase 30**: Multi-Currency & International Expansion
- **Phase 31**: Advanced Analytics & Cash-Flow Forecasting
- **Phase 32**: Operations, Support, Disaster Recovery & Scaling

---

## 5. Non-Negotiable Engineering Principles

1. **Financial Precision**: Never use IEEE 754 floating-point numbers. All monetary calculations are performed with exact decimal arithmetic.
2. **Multi-Tenancy Isolation**: Every database query on business resources must be tenant-scoped by `organisation_id`. Cross-tenant data leakage is a zero-tolerance failure.
3. **Backend Authority**: The backend must independently recalculate all totals, taxes, discounts, and balances. Frontend data is never inherently trusted.
4. **Auditability**: Every mutation to state or sensitive configuration writes an immutable, timestamped audit log.
5. **Idempotency & Concurrency Control**: Sequence numbers (invoice numbers, bill numbers, journal entry numbers) and payment allocations require pessimistic or optimistic locking to prevent race conditions.
