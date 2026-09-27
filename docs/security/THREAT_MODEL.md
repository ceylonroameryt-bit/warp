# Threat Model & Vulnerability Mitigations (STRIDE)

## 1. Threat Analysis

| STRIDE Category | Potential Vector | Warp Ladger Architectural Mitigation |
|---|---|---|
| **Spoofing** | Credential stuffing, session hijacking, JWT forgery | Argon2id hashing, short-lived (15 min) access tokens, rotating hashed refresh tokens, HttpOnly/Strict cookies, secret key rotation. |
| **Tampering** | Modifying parameters to access another tenant's files or accounting records | Invariable `organisation_id` checks on all DB queries, SQLAlchemy query scoping, immutable audit trails. |
| **Repudiation** | Denying an unauthorized financial posting or member invitation | Centralized, append-only audit log capturing user ID, action, timestamp, IP address, and payload delta. |
| **Information Disclosure** | Cross-tenant data leakage via search or enumeration | UUIDv4 primary keys (non-enumerable), multi-tenant foreign keys, strict 404 responses for cross-tenant entities (preventing existence leakage). |
| **Denial of Service** | Large file uploads, excessive login requests, query exhaustion | 25 MB file size limit, Redis sliding-window rate limiting, pagination with maximum limit caps. |
| **Elevation of Privilege** | Normal user elevating their role to Owner or Admin | Backend permission check (`require_permission("member", "update")`), safeguards preventing demotion/removal of the last owner. |
