# Testing Strategy & QA Standards

## 1. Testing Hierarchy

To maintain high confidence in financial and security operations, Warp Ladger implements a multi-tiered testing strategy:

```text
               ┌──────────────────────────┐
               │    E2E & User Journey    │
               │   (Full Platform Flows)  │
               ├──────────────────────────┤
               │ Integration & Isolation  │
               │ (RBAC, Tenancy, DB ACIDs)│
               ├──────────────────────────┤
               │   Unit & Domain Logic    │
               │ (Decimals, Hashing, Auth)│
               └──────────────────────────┘
```

## 2. Test Requirements by Phase

### Phase 1 Foundations
- **Authentication**: Registration, password complexity, Argon2id hashing, login/logout, refresh rotation, email verification, password reset.
- **Tenant Isolation**: Direct attempts by User B in Org B to read, update, or delete Org A's records must always yield 403 or 404.
- **RBAC Matrix**: All 8 canonical roles (`Owner`, `Administrator`, `Accountant`, `Bookkeeper`, `Approver`, `Employee`, `Auditor`, `Viewer`) must be tested against permitted and prohibited operations.
- **File Ingestion**: File type whitelist (`pdf`, `jpeg`, `png`, `heic`), rejection of disallowed types, size limit checks, presigned URL access.
- **Audit Logging**: Verification that state-changing operations trigger audit events with proper metadata.
- **Phase 1 Result E2E**:
  $$\text{Register} \longrightarrow \text{Create Business} \longrightarrow \text{Invite Team} \longrightarrow \text{Assign Role} \longrightarrow \text{Upload File} \longrightarrow \text{Audit Event}$$

### Financial Phases (Phases 3+)
- **Decimal Invariance**: Zero float representations. Validated against currency math test suites with rounding tests.
- **Concurrency & Idempotency**: Duplicate payment and invoice submission prevention under concurrent load.
