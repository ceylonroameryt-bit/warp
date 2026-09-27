"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  CreditCard,
  ArrowLeft,
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  Calendar,
  CheckCircle2,
  AlertCircle,
  FileText,
  Receipt,
  Sparkles,
  Info,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface Contact {
  id: string;
  business_name: string;
  contact_type: string;
}

interface BankAccount {
  id: string;
  account_name: string;
  currency: string;
  current_balance: number | string;
  is_default: boolean;
}

interface OpenDocument {
  id: string;
  document_number: string;
  date: string;
  due_date: string;
  total: number;
  amount_due: number;
  currency: string;
}

function fmt(n: number | string | undefined, curr = "GBP") {
  const num = typeof n === "string" ? parseFloat(n) : n || 0;
  return `£${num.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function RecordPaymentContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL query pre-fills
  const initialType = searchParams.get("type") === "OUTGOING" ? "OUTGOING" : "INCOMING";
  const initialContactId = searchParams.get("contact_id") || "";
  const initialInvoiceId = searchParams.get("invoice_id") || "";
  const initialBillId = searchParams.get("bill_id") || "";

  const [paymentType, setPaymentType] = useState<"INCOMING" | "OUTGOING">(initialType);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [openDocuments, setOpenDocuments] = useState<OpenDocument[]>([]);

  // Form state
  const [contactId, setContactId] = useState(initialContactId);
  const [bankAccountId, setBankAccountId] = useState("");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split("T")[0]);
  const [paymentMethod, setPaymentMethod] = useState("BANK_TRANSFER");
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState<number>(0);
  const [notes, setNotes] = useState("");

  // Map of documentId -> allocatedAmount
  const [allocations, setAllocations] = useState<Record<string, number>>({});

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // 1. Fetch Contacts & Bank Accounts
  useEffect(() => {
    async function loadInitialData() {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        // Fetch contacts
        const contactTypeFilter = paymentType === "INCOMING" ? "CUSTOMER" : "SUPPLIER";
        const cRes = await fetch(
          `${API_BASE}/api/v1/organisations/${ORG_ID}/contacts?contact_type=${contactTypeFilter}&limit=100`,
          { headers }
        );
        if (cRes.ok) {
          const cData = await cRes.json();
          setContacts(cData.items || []);
        }

        // Fetch bank accounts
        const bRes = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/bank-accounts`, { headers });
        if (bRes.ok) {
          const bData = await bRes.json();
          setBankAccounts(bData || []);
          const def = bData.find((b: BankAccount) => b.is_default);
          if (def && !bankAccountId) setBankAccountId(def.id);
        }
      } catch (err) {
        console.error("Initial load error:", err);
      }
    }
    loadInitialData();
  }, [paymentType]);

  // 2. Fetch Open Invoices/Bills when Contact changes
  useEffect(() => {
    if (!contactId) {
      setOpenDocuments([]);
      setAllocations({});
      return;
    }

    async function loadOpenDocuments() {
      setLoading(true);
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        if (paymentType === "INCOMING") {
          const res = await fetch(
            `${API_BASE}/api/v1/organisations/${ORG_ID}/invoices?customer_id=${contactId}&status=APPROVED,AWAITING_PAYMENT,PARTIALLY_PAID&limit=50`,
            { headers }
          );
          if (res.ok) {
            const data = await res.json();
            const docs: OpenDocument[] = (data.items || []).map((inv: any) => ({
              id: inv.id,
              document_number: inv.invoice_number,
              date: inv.issue_date,
              due_date: inv.due_date,
              total: parseFloat(inv.total),
              amount_due: parseFloat(inv.amount_due),
              currency: inv.currency || "GBP",
            }));
            setOpenDocuments(docs);

            // Pre-allocate if initialInvoiceId specified
            if (initialInvoiceId) {
              const target = docs.find((d) => d.id === initialInvoiceId);
              if (target) {
                setAllocations({ [target.id]: target.amount_due });
                setAmount(target.amount_due);
              }
            }
          }
        } else {
          const res = await fetch(
            `${API_BASE}/api/v1/organisations/${ORG_ID}/bills?supplier_id=${contactId}&status=APPROVED,PARTIALLY_PAID&limit=50`,
            { headers }
          );
          if (res.ok) {
            const data = await res.json();
            const docs: OpenDocument[] = (data.items || []).map((bill: any) => ({
              id: bill.id,
              document_number: bill.internal_bill_number || bill.supplier_invoice_number,
              date: bill.bill_date,
              due_date: bill.due_date,
              total: parseFloat(bill.total),
              amount_due: parseFloat(bill.amount_due),
              currency: bill.currency || "GBP",
            }));
            setOpenDocuments(docs);

            // Pre-allocate if initialBillId specified
            if (initialBillId) {
              const target = docs.find((d) => d.id === initialBillId);
              if (target) {
                setAllocations({ [target.id]: target.amount_due });
                setAmount(target.amount_due);
              }
            }
          }
        }
      } catch (err) {
        console.error("Failed to load open documents:", err);
      } finally {
        setLoading(false);
      }
    }

    loadOpenDocuments();
  }, [contactId, paymentType, initialInvoiceId, initialBillId]);

  // Handle single allocation change
  const handleAllocationChange = (docId: string, val: string, maxDue: number) => {
    const num = Math.min(Math.max(parseFloat(val) || 0, 0), maxDue);
    setAllocations((prev) => ({
      ...prev,
      [docId]: num,
    }));
  };

  // Auto-allocate across oldest documents first
  const handleAutoAllocate = () => {
    let remaining = amount;
    const newAllocs: Record<string, number> = {};

    for (const doc of openDocuments) {
      if (remaining <= 0) break;
      const allocAmt = Math.min(remaining, doc.amount_due);
      newAllocs[doc.id] = allocAmt;
      remaining -= allocAmt;
    }

    setAllocations(newAllocs);
  };

  const totalAllocated = Object.values(allocations).reduce((acc, val) => acc + (val || 0), 0);
  const unallocatedAmount = Math.max(0, amount - totalAllocated);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (amount <= 0) {
      setError("Payment amount must be greater than zero.");
      return;
    }
    if (totalAllocated > amount) {
      setError("Total allocated amount cannot exceed total payment amount.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // Format allocations payload
      const allocPayload = Object.entries(allocations)
        .filter(([_, amt]) => amt > 0)
        .map(([docId, amt]) => {
          if (paymentType === "INCOMING") {
            return { target_type: "INVOICE", invoice_id: docId, amount: amt };
          } else {
            return { target_type: "BILL", bill_id: docId, amount: amt };
          }
        });

      const payload = {
        payment_type: paymentType,
        contact_id: contactId || null,
        bank_account_id: bankAccountId || null,
        payment_date: paymentDate,
        amount: amount,
        currency: "GBP",
        payment_method: paymentMethod,
        reference: reference.trim() || null,
        notes: notes.trim() || null,
        allocations: allocPayload,
      };

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/payments`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to record payment");
      }

      router.push("/app/payments");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred while saving payment.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Back Link */}
        <Link
          href="/app/payments"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Payments
        </Link>

        {/* Page Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Record Payment & Settlement</h1>
            <p className="text-xs text-slate-500 mt-1">
              Capture funds received from customers or disbursements paid to suppliers with atomic allocation.
            </p>
          </div>

          {/* Type Toggle */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => {
                setPaymentType("INCOMING");
                setContactId("");
                setAllocations({});
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                paymentType === "INCOMING"
                  ? "bg-white text-teal-800 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <ArrowDownLeft className="w-3.5 h-3.5 text-teal-600" />
              Customer Receipt (Inflow)
            </button>
            <button
              type="button"
              onClick={() => {
                setPaymentType("OUTGOING");
                setContactId("");
                setAllocations({});
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                paymentType === "OUTGOING"
                  ? "bg-white text-indigo-800 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <ArrowUpRight className="w-3.5 h-3.5 text-indigo-600" />
              Supplier Payment (Outflow)
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-50 text-rose-800 text-xs rounded-xl border border-rose-200 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ── SECTION 1: PAYMENT DETAILS ── */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-[#0073B7]" />
              Payment Information
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* Contact Picker */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  {paymentType === "INCOMING" ? "Customer *" : "Supplier *"}
                </label>
                <select
                  required
                  value={contactId}
                  onChange={(e) => setContactId(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500 font-medium text-slate-800"
                >
                  <option value="">-- Select Contact --</option>
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.business_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Bank Account */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Deposit / Paid From Bank Account
                </label>
                <select
                  value={bankAccountId}
                  onChange={(e) => setBankAccountId(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500 text-slate-800"
                >
                  <option value="">Direct Cash / External Clearing</option>
                  {bankAccounts.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.account_name} ({fmt(b.current_balance, b.currency)})
                    </option>
                  ))}
                </select>
              </div>

              {/* Payment Date */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">Payment Date *</label>
                <input
                  type="date"
                  required
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              {/* Payment Method */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">Payment Method *</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="BANK_TRANSFER">Bank Transfer / Faster Payments</option>
                  <option value="CREDIT_CARD">Credit Card</option>
                  <option value="DEBIT_CARD">Debit Card</option>
                  <option value="DIRECT_DEBIT">Direct Debit</option>
                  <option value="CHEQUE">Cheque</option>
                  <option value="CASH">Cash</option>
                </select>
              </div>

              {/* Payment Total Amount */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Total Payment Amount (£) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  value={amount || ""}
                  onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                  placeholder="0.00"
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-base font-bold text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              {/* Reference */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">Reference / Memo</label>
                <input
                  type="text"
                  placeholder="e.g. BACS-88219 / Cheque #104"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  className="w-full p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>
            </div>
          </div>

          {/* ── SECTION 2: DOCUMENT ALLOCATIONS ── */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#0073B7]" />
                  Allocate Payment to Open Documents
                </h2>
                <p className="text-xs text-slate-500">
                  Select which invoices or bills to settle. Any excess remains as unallocated credit.
                </p>
              </div>

              {openDocuments.length > 0 && amount > 0 && (
                <button
                  type="button"
                  onClick={handleAutoAllocate}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 rounded-lg transition border border-sky-200"
                >
                  <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                  Auto-Allocate Oldest First
                </button>
              )}
            </div>

            {!contactId ? (
              <div className="py-8 text-center text-xs text-slate-400 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
                Please select a contact above to view outstanding invoices or bills.
              </div>
            ) : loading ? (
              <div className="py-8 text-center text-xs text-slate-400">Loading open documents...</div>
            ) : openDocuments.length === 0 ? (
              <div className="py-6 px-4 bg-slate-50 rounded-lg text-xs text-slate-600 flex items-center gap-3">
                <Info className="w-5 h-5 text-slate-400 shrink-0" />
                <span>
                  No outstanding documents found for this contact. This payment will be recorded as an{" "}
                  <strong>Unallocated Prepayment / Advance Credit</strong>.
                </span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-600 font-semibold uppercase tracking-wider">
                      <th className="py-2.5 px-3">Document #</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Due Date</th>
                      <th className="py-2.5 px-3 text-right">Total</th>
                      <th className="py-2.5 px-3 text-right">Amount Due</th>
                      <th className="py-2.5 px-3 text-right w-44">Allocate (£)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {openDocuments.map((doc) => {
                      const currentAlloc = allocations[doc.id] || 0;
                      return (
                        <tr key={doc.id} className="hover:bg-slate-50/60 transition">
                          <td className="py-2.5 px-3 font-semibold font-mono text-slate-900">
                            {doc.document_number}
                          </td>
                          <td className="py-2.5 px-3 text-slate-500">{doc.date?.split("T")[0]}</td>
                          <td className="py-2.5 px-3 text-slate-500">{doc.due_date?.split("T")[0]}</td>
                          <td className="py-2.5 px-3 text-right">{fmt(doc.total, doc.currency)}</td>
                          <td className="py-2.5 px-3 text-right font-semibold text-rose-600">
                            {fmt(doc.amount_due, doc.currency)}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                max={doc.amount_due}
                                value={currentAlloc || ""}
                                onChange={(e) =>
                                  handleAllocationChange(doc.id, e.target.value, doc.amount_due)
                                }
                                placeholder="0.00"
                                className="w-24 text-right p-1.5 border border-slate-300 rounded font-semibold text-slate-900 focus:outline-none focus:ring-1 focus:ring-sky-500"
                              />
                              <button
                                type="button"
                                onClick={() =>
                                  handleAllocationChange(doc.id, String(doc.amount_due), doc.amount_due)
                                }
                                className="px-1.5 py-1 text-[11px] font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 rounded border border-sky-200"
                              >
                                Full
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── ALLOCATION SUMMARY BREAKDOWN ── */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex justify-between items-center text-slate-600">
                <span>Total Payment Amount:</span>
                <span className="font-bold text-slate-900 text-sm">{fmt(amount)}</span>
              </div>
              <div className="flex justify-between items-center text-slate-600">
                <span>Total Allocated to Documents:</span>
                <span className="font-semibold text-emerald-700">{fmt(totalAllocated)}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-slate-200">
                <span className="font-medium text-slate-700">Remaining Unallocated (Customer Credit / Advance):</span>
                <span
                  className={`font-bold ${
                    unallocatedAmount > 0 ? "text-amber-700" : "text-slate-400"
                  }`}
                >
                  {fmt(unallocatedAmount)}
                </span>
              </div>
            </div>
          </div>

          {/* ── ACTION BUTTONS ── */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              href="/app/payments"
              className="px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting || amount <= 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-[#0A2540] hover:bg-[#081d33] rounded-lg shadow-sm transition disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              {submitting ? "Processing..." : "Record & Post Payment"}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}

export default function RecordPaymentPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading form...</div>}>
      <RecordPaymentContent />
    </Suspense>
  );
}
