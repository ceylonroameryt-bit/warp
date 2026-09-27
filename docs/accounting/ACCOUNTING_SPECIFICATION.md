# Accounting Specification & Ledger Principles

## 1. Professional Validation Rule
All accounting and tax business rules must adhere to qualified finance and accounting standards (UK GAAP, IFRS, HMRC guidelines) rather than speculative software conventions.

---

## 2. Fundamental Ledger Invariants

### 2.1 Double-Entry Equation
Every financial event produces a Journal Entry consisting of two or more Journal Lines such that:

$$\sum \text{Debits} = \sum \text{Credits}$$

A transaction where $\sum \text{Debits} \neq \sum \text{Credits}$ is structurally invalid and must be rejected atomically at the database constraint layer.

### 2.2 Numerical Precision (No Floating-Point)
- All monetary arithmetic is conducted using `Decimal` (Python) and `NUMERIC(18, 4)` / `NUMERIC(18, 2)` (PostgreSQL).
- Rounding mode: **Round Half To Even** (Banker's Rounding) as per ISO standard, applied only at the final invoice/tax line presentation stage.

### 2.3 Non-Negotiable Immutability of Posted Records
- Once a journal entry is posted to the ledger, it is **never silently updated or deleted**.
- Corrections must be enacted by creating a **Reversal Journal Entry** linked to the original entry, followed by a new adjusting entry.
- Accounting periods that have passed their lock date (`lock_date`) are strictly closed to new entries or adjustments.

---

## 3. Chart of Accounts (COA) Architecture

Accounts are organized into five fundamental classes:

| Class Code Range | Account Class | Normal Balance | Description |
|---|---|---|---|
| **1000 — 1999** | **Assets** | Debit (Dr) | Cash, Bank Accounts, Accounts Receivable, Inventory, Equipment |
| **2000 — 2999** | **Liabilities** | Credit (Cr) | Accounts Payable, VAT Output Tax, Payroll Liabilities, Loans |
| **3000 — 3999** | **Equity** | Credit (Cr) | Share Capital, Retained Earnings, Owner's Drawings |
| **4000 — 4999** | **Revenue** | Credit (Cr) | Sales Revenue, Consulting Income, Interest Income |
| **5000 — 9999** | **Expenses** | Debit (Dr) | Cost of Goods Sold (COGS), Rent, Utilities, Software, VAT Input Tax |

---

## 4. Standard Transaction Postings

### Sales Invoice Example (£1,000 Net + £200 VAT = £1,200 Gross)
```text
Dr Accounts Receivable (1200)      £1,200.00
   Cr Sales Revenue (4000)                      £1,000.00
   Cr VAT Payable / Output Tax (2200)             £200.00
```

### Invoice Payment Received (£1,200)
```text
Dr Current Bank Account (1000)      £1,200.00
   Cr Accounts Receivable (1200)                 £1,200.00
```

### Supplier Bill Example (£500 Net + £100 VAT = £600 Gross)
```text
Dr Office Supplies Expense (5100)    £500.00
Dr VAT Recoverable / Input Tax (2210) £100.00
   Cr Accounts Payable (2000)                     £600.00
```

### Supplier Bill Payment (£600)
```text
Dr Accounts Payable (2000)           £600.00
   Cr Current Bank Account (1000)                 £600.00
```
