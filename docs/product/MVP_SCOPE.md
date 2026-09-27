# Commercial MVP Scope Specification

## 1. Commercial MVP Definition

The target of the initial commercial MVP is to deliver a complete, trustworthy accounting core that businesses can immediately rely upon for day-to-day statutory operations.

### Included in MVP Core (Phases 1 — 12, 19, 20)
1. **Phase 1: Foundation**: Secure auth, multi-tenant isolation, 8-role RBAC, invitations, secure file storage, and audit logs.
2. **Phase 2: Contacts**: Customers, suppliers, addresses, payment terms, and contact snapshotting.
3. **Phase 3: Sales Invoices**: Draft, approve, send, PDF generation, overdue tracking, and decimal math.
4. **Phase 4: Supplier Bills**: Payables lifecycle, line items, approvals, and duplicate detection.
5. **Phase 5: Smart Capture**: Ingestion of PDF, JPG, PNG, HEIC, OCR extraction, field confidence, human review.
6. **Phase 6: Payments & Allocations**: Partial payments, overpayments, multi-invoice allocations, and payment reversals.
7. **Phase 7: Double-Entry Ledger**: Chart of accounts, journal posting, debit/credit invariant, and period locking.
8. **Phase 8: Financial Reporting**: Profit & Loss, Balance Sheet, Trial Balance, Aged Payables/Receivables.
9. **Phase 9: Bank Accounts & Statement Import**: CSV statement mapping, transaction storage, and deduplication.
10. **Phase 10: Bank Reconciliation**: Matching transactions to bills/invoices with smart suggestions.
11. **Phase 11: Credit Notes & Adjustments**: Refunds, write-offs, and allocations.
12. **Phase 12: VAT & Tax Engine**: Tax rates, VAT period calculation, and audit summaries.
13. **Phase 19 & 20: Hardening & Beta Launch**: Penetration testing, rate limiting, and controlled customer trials.

### Explicitly Excluded from Initial MVP (Post-MVP Roadmap)
- Complex multi-currency FX revaluation (Phase 30).
- Payroll processing and auto-enrolment pensions.
- Multi-warehouse inventory valuation (Phase 28).
- Direct Open Banking API payment initiation (Phase 21).
- Unsupervised autonomous AI accounting bots.
- Crypto/digital asset accounting.
