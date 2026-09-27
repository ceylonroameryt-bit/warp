# Data Architecture & Multi-Tenancy Design

## 1. Multi-Tenancy Partitioning Model

Warp Ladger employs a **Shared Database, Row-Level Isolation (Discriminator Column)** strategy.

### Discriminator Invariant
Every tenant-owned entity in the relational schema incorporates a mandatory foreign key:
```sql
organisation_id UUID NOT NULL REFERENCES organisations(id) ON DELETE CASCADE
```

Composite indexes are systematically defined to ensure query efficiency and enforce tenant uniqueness:
```sql
CREATE INDEX ix_entity_org_id ON entity_table (organisation_id);
CREATE UNIQUE INDEX uq_entity_natural_key ON entity_table (organisation_id, natural_code);
```

### Architectural Safeguard
Application repository and service layers enforce tenant isolation at three distinct checkpoints:
1. **URL & Route Parameter Validation**: `org_id` in `/api/v1/organisations/{org_id}/...` is validated against the authenticated user's active memberships.
2. **Permission Guard (`require_permission`)**: Resolves the user's role specifically within `{org_id}` and checks the assigned permissions.
3. **ORM Scoping (`TenantMixin`)**: All queries strictly filter by `Model.organisation_id == org_id`.

---

## 2. Core Entity Relationship Diagram (Phase 1 Foundation)

```text
       ┌──────────┐
       │   User   │
       └────┬─────┘
            │ 1
            │
            │ *
 ┌──────────┴────────────┐          ┌────────────────┐
 │      Membership       ├──────────┤      Role      │
 └──────────┬────────────┘ *      1 └───────┬────────┘
            │ *                             │ *
            │                               │
            │ 1                             │ *
 ┌──────────┴────────────┐          ┌───────┴────────┐
 │     Organisation      │          │   Permission   │
 └────┬──────────────┬───┘          └────────────────┘
      │ 1            │ 1
      │              │
      │ *            │ *
┌─────┴──────┐ ┌─────┴──────┐
│    File    │ │  AuditLog  │
└────────────┘ └────────────┘
```

---

## 3. Immutability & Audit Standards

1. **Soft Deletion**: Records employ `is_deleted` and `deleted_at` timestamps. Financial records are never hard-deleted.
2. **Audit Trails**: The `audit_logs` table is strictly append-only. There is no update or delete route exposed in the API or granted in the database role.
