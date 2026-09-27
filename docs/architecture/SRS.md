# Software Requirements Specification (SRS)

## 1. Scope & Purpose
This document specifies the software engineering requirements for the Warp Ladger commercial SaaS accounting platform.

## 2. Functional Requirements (Phase 1 Focus)

### FR-01: Authentication & Identity Management
- **FR-01.1**: User registration with unique email, full name, and minimum 8-character password.
- **FR-01.2**: Password hashing using Argon2id with salt and memory-hard tuning.
- **FR-01.3**: Cryptographic email verification tokens with single-use invalidation and 24-hour expiration.
- **FR-01.4**: Single-use password reset tokens with 1-hour expiration.
- **FR-01.5**: Rotating refresh tokens hashed in the database; issuing short-lived JWT access tokens (15 minutes).
- **FR-01.6**: Tokens transmitted exclusively via `HttpOnly`, `SameSite=Strict`, `Secure` (production) cookies.
- **FR-01.7**: Rate limiting on authentication endpoints (5 requests/minute per IP) to mitigate brute-force attacks.

### FR-02: Multi-Tenancy & Organisations
- **FR-02.1**: A user can create one or more Organisations.
- **FR-02.2**: The creating user is automatically assigned the `Owner` role for that organisation.
- **FR-02.3**: Every organisation has a primary currency (default `GBP`), timezone, and business identity attributes.
- **FR-02.4**: Strict tenant boundary: API requests must include target `organisation_id` in path or context; backend strictly verifies active membership.

### FR-03: Team Management & 8-Role RBAC
- **FR-03.1**: Support exactly 8 canonical roles:
  1. `Owner`
  2. `Administrator`
  3. `Accountant`
  4. `Bookkeeper`
  5. `Approver`
  6. `Employee`
  7. `Auditor`
  8. `Viewer`
- **FR-03.2**: Email-based invitations with secure tokens, role specification, and 7-day expiration.
- **FR-03.3**: Membership state management: `active`, `invited`, `suspended`.
- **FR-03.4**: Guard: An organisation must always possess at least one active `Owner`. Self-removal or demotion of the last owner is rejected.

### FR-04: Secure Private File Storage
- **FR-04.1**: Store business files in private object storage (MinIO for dev, S3/R2 for prod).
- **FR-04.2**: Allow MIME types: `application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `image/heif`. Disallow executable or script formats.
- **FR-04.3**: Enforce 25 MB per-file size limit.
- **FR-04.4**: Access via time-limited presigned URLs (15 minutes).

### FR-05: Centralized Audit Logging
- **FR-05.1**: Append-only audit logs for all security and tenant events: `auth.login`, `auth.logout`, `auth.register`, `org.created`, `org.updated`, `member.invited`, `member.joined`, `member.role_changed`, `member.suspended`, `member.removed`, `file.uploaded`, `file.deleted`.
- **FR-05.2**: Audit records must capture `organisation_id`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `created_at`.

---

## 3. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| **NFR-01** | Availability | 99.9% uptime SLA for core API and ledger services. |
| **NFR-02** | Latency | API response time $< 150\text{ms}$ at 95th percentile for read/write queries. |
| **NFR-03** | Data Precision | Zero floating-point arithmetic. Strict `Decimal` with 4 decimal places for internal unit costs/quantities and 2 decimal places for financial totals. |
| **NFR-04** | Security | TLS 1.3 in transit, AES-256 at rest, strict tenant scoping on every SQL query. |
| **NFR-05** | Auditability | Audit records must be immutable (no update or delete permissions on audit table). |
