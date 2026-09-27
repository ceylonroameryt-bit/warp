# User Personas and Journeys

## 1. User Personas

### Persona 1: Sarah — Business Owner (`Owner`)
- **Profile**: Founder and managing director of a growing services agency.
- **Goals**: Real-time cash flow clarity, accurate tax preparation, delegation of day-to-day operations to bookkeepers and employees without losing financial control.
- **Pain Points**: Complicated accounting jargon, surprise tax liabilities, fear of unauthorized payments or changes to financial history.

### Persona 2: David — Platform Administrator (`Administrator`)
- **Profile**: Operations Manager responsible for onboarding staff, managing permissions, setting up integrations, and auditing system access.
- **Goals**: Fast team onboarding, role-based security, ensuring team members only access what they need.

### Persona 3: Elena — Certified Accountant (`Accountant`)
- **Profile**: External chartered accountant or internal finance lead.
- **Goals**: Double-entry rigor, accurate Chart of Accounts, period closing and lock dates, tax adjustment journals, audit trails, and financial statements (P&L, Balance Sheet).
- **Needs**: Inflexible audit logs, debit-credit balance enforcement, strict reversal policies.

### Persona 4: Marcus — Bookkeeper (`Bookkeeper`)
- **Profile**: Daily transactional specialist entering bills, issuing invoices, capturing receipts, and matching bank feed transactions.
- **Goals**: High-speed data entry, automated duplicate detection, intelligent document extraction.

### Persona 5: Chloe — Bill Approver (`Approver`)
- **Profile**: Department head or budget holder.
- **Goals**: Review supplier bills submitted by employees or bookkeepers, verify deliverables, and authorize payment scheduling.

### Persona 6: Tom — Employee (`Employee`)
- **Profile**: Field consultant or general staff member.
- **Goals**: Upload receipts/documents from phone or desktop, track submission status, enter billable time or quotes.

### Persona 7: Arthur — External Auditor (`Auditor`)
- **Profile**: Regulatory auditor or financial examiner.
- **Goals**: Read-only verification of transaction provenance, immutable audit trails, journal lines, and supporting document attachments.

### Persona 8: Priya — Stakeholder (`Viewer`)
- **Profile**: Board member or non-executive director.
- **Goals**: Read-only dashboard view of high-level business performance metrics without ability to mutate records.

---

## 2. Core User Journey: Phase 1 SaaS Onboarding

```text
[1. User Registration]
    │  User inputs Email, Full Name, Strong Password
    ▼
[2. Verification & Session]
    │  Activation email received -> Token verified -> Secure HttpOnly cookie session issued
    ▼
[3. Organisation Provisioning]
    │  Create Company Profile (Name, Registration #, VAT #, Default Currency: GBP)
    │  Creator assigned immutable 'Owner' role
    ▼
[4. Team Invitation]
    │  Invite Accountant, Bookkeeper, Approver, Employee, Auditor
    │  Assign fine-grained roles with system permissions
    ▼
[5. File Storage & Evidence]
    │  Upload initial documents (incorporation certificate, VAT letters, logo)
    │  Supported: PDF, JPG, PNG, HEIC
    ▼
[6. Traceable Audit Trail]
    │  All steps logged to immutable central audit ledger
```
