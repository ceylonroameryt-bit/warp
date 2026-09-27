# Security Architecture

## 1. Principles of Defense-in-Depth

Security is designed into every layer of Warp Ladger:

1. **Authentication Layer**:
   - Passwords hashed using Argon2id (`time_cost=3`, `memory_cost=65536`, `parallelism=4`, salt length 16 bytes).
   - Rotating refresh tokens (7 days lifetime) stored as SHA-256 hashes in the database with explicit revocation.
   - Access tokens (15 minutes lifetime) stored strictly in `HttpOnly`, `SameSite=Strict`, `Secure` cookies.
   - Brute-force rate limiting using a Redis sliding-window algorithm on all authentication routes.

2. **Authorization & RBAC Layer**:
   - Fine-grained resource:action RBAC checked on every non-public endpoint.
   - 8 canonical roles: `Owner`, `Administrator`, `Accountant`, `Bookkeeper`, `Approver`, `Employee`, `Auditor`, `Viewer`.
   - Explicit tenant membership verification before permission resolution.

3. **Transport & Network Layer**:
   - Mandatory TLS 1.3 in production.
   - Strict HTTP Security Headers:
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Content-Security-Policy: default-src 'self'; ...`
     - `Referrer-Policy: strict-origin-when-cross-origin`
     - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

4. **File Ingestion Security**:
   - Strict MIME type filtering: `application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `image/heif`.
   - Magic byte validation to prevent MIME-type spoofing.
   - 25 MB file size limit to prevent resource exhaustion attacks.
   - Storage isolation: files stored in tenant-partitioned private object storage with signed, time-limited presigned URLs.

5. **Data Protection at Rest & in Transit**:
   - AES-256 encryption at rest for database and object storage.
   - Structured audit logging for all security-sensitive events.
