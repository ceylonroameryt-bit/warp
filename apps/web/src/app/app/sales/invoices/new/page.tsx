"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Save, CheckCircle, AlertCircle } from "lucide-react";
import Link from "next/link";
import DashboardLayout from "@/components/DashboardLayout";
import CustomerSelector from "@/components/CustomerSelector";
import InvoiceLineEditor, { LineItem, TaxRate } from "@/components/InvoiceLineEditor";
import InvoiceTotalsPanel from "@/components/InvoiceTotalsPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

function todayIso() {
  return new Date().toISOString().split("T")[0];
}
function inDaysIso(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

interface PaymentTerm {
  id: string;
  name: string;
  days: number;
}

export default function NewInvoicePage() {
  const router = useRouter();

  const [customer, setCustomer] = useState<any>(null);
  const [issueDate, setIssueDate] = useState(todayIso());
  const [dueDate, setDueDate] = useState(inDaysIso(30));
  const [currency, setCurrency] = useState("GBP");
  const [paymentTermId, setPaymentTermId] = useState("");
  const [customerRef, setCustomerRef] = useState("");
  const [poRef, setPoRef] = useState("");
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("");
  const [internalNotes, setInternalNotes] = useState("");
  const [lines, setLines] = useState<LineItem[]>([
    {
      description: "",
      quantity: "1",
      unit_price: "0.00",
      tax_rate_id: "",
      discount_type: "",
      discount_value: "0",
      position: 0,
    },
  ]);
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTerm[]>([]);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [successId, setSuccessId] = useState("");

  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  useEffect(() => {
    async function loadOrg() {
      try {
        const res = await fetch("/api/v1/organisations/", { credentials: "include" });
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0 && orgs[0].id) {
            setActiveOrgId(orgs[0].id);
          }
        }
      } catch {
        // fallback
      }
    }
    loadOrg();
  }, []);

  useEffect(() => {
    async function loadMeta() {
      if (!activeOrgId) return;
      try {
        const [taxRes, termsRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/organisations/${activeOrgId}/tax-rates`, {
            credentials: "include",
          }),
          fetch(`${API_BASE}/api/v1/organisations/${activeOrgId}/payment-terms`, {
            credentials: "include",
          }),
        ]);
        if (taxRes.ok) {
          const data = await taxRes.json();
          setTaxRates(data);
          // Pre-fill first line with first tax rate
          if (data.length > 0) {
            setLines((prev) =>
              prev.map((l) => ({ ...l, tax_rate_id: data[0].id }))
            );
          }
        }
        if (termsRes.ok) {
          const data = await termsRes.json();
          setPaymentTerms(data.items ?? data);
        }
      } catch {
        // ignore
      }
    }
    loadMeta();
  }, [activeOrgId]);

  // Auto-calculate due date when payment term changes
  function handleTermChange(termId: string) {
    setPaymentTermId(termId);
    const term = paymentTerms.find((t) => t.id === termId);
    if (term) {
      setDueDate(inDaysIso(term.days));
    }
  }

  function validate() {
    const errs: Record<string, string> = {};
    if (!customer) errs.customer = "Please select a customer.";
    if (!issueDate) errs.issueDate = "Issue date is required.";
    if (!dueDate) errs.dueDate = "Due date is required.";
    if (dueDate < issueDate) errs.dueDate = "Due date cannot be before issue date.";
    if (lines.length === 0) errs.lines = "Add at least one line item.";
    const invalidLine = lines.find(
      (l) => !l.description.trim() || parseFloat(l.quantity) <= 0 || parseFloat(l.unit_price) < 0
    );
    if (invalidLine) errs.lines = "Check all line items have a description, quantity, and price.";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSave(andApprove = false) {
    if (!validate()) return;
    setSaving(true);
    setError("");
    try {
      const payload = {
        customer_id: customer.id,
        issue_date: new Date(issueDate).toISOString(),
        due_date: new Date(dueDate).toISOString(),
        currency,
        payment_terms_id: paymentTermId || null,
        customer_reference: customerRef || null,
        purchase_order_reference: poRef || null,
        notes: notes || null,
        terms: terms || null,
        internal_notes: internalNotes || null,
        lines: lines.map((l, i) => ({
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          tax_rate_id: l.tax_rate_id || null,
          discount_type: l.discount_type || null,
          discount_value: parseFloat(l.discount_value) || 0,
          position: i,
        })),
      };

      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        setError(data?.detail || "Failed to create invoice.");
        return;
      }

      const created = await res.json();

      if (andApprove) {
        const approveRes = await fetch(
          `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${created.id}/approve`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({}),
          }
        );
        if (!approveRes.ok) {
          // Save succeeded, approval failed → redirect to invoice detail
          router.push(`/app/sales/invoices/${created.id}?notice=approval_failed`);
          return;
        }
      }

      router.push(`/app/sales/invoices/${created.id}?new=1`);
    } catch {
      setError("A network error occurred. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardLayout>
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        {/* Page Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/app/sales/invoices"
            className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900">New Invoice</h1>
            <p className="text-xs text-slate-500">Saved as draft until approved</p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-5 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-5">

            {/* Customer */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Bill To</h2>
              <CustomerSelector
                orgId={activeOrgId}
                value={customer}
                onChange={setCustomer}
                disabled={saving}
                error={fieldErrors.customer}
              />
            </div>

            {/* Dates & References */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-4">Invoice Details</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Issue Date *
                  </label>
                  <input
                    type="date"
                    value={issueDate}
                    onChange={(e) => setIssueDate(e.target.value)}
                    disabled={saving}
                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-sky-400 ${
                      fieldErrors.issueDate ? "border-red-300 bg-red-50" : "border-slate-200"
                    }`}
                  />
                  {fieldErrors.issueDate && (
                    <p className="text-xs text-red-500 mt-1">{fieldErrors.issueDate}</p>
                  )}
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Due Date *
                  </label>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    disabled={saving}
                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-sky-400 ${
                      fieldErrors.dueDate ? "border-red-300 bg-red-50" : "border-slate-200"
                    }`}
                  />
                  {fieldErrors.dueDate && (
                    <p className="text-xs text-red-500 mt-1">{fieldErrors.dueDate}</p>
                  )}
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Payment Terms
                  </label>
                  <select
                    value={paymentTermId}
                    onChange={(e) => handleTermChange(e.target.value)}
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white"
                  >
                    <option value="">Select terms…</option>
                    {paymentTerms.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">Currency</label>
                  <select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white"
                  >
                    <option value="GBP">GBP — British Pound</option>
                    <option value="EUR">EUR — Euro</option>
                    <option value="USD">USD — US Dollar</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Customer Reference
                  </label>
                  <input
                    type="text"
                    value={customerRef}
                    onChange={(e) => setCustomerRef(e.target.value)}
                    placeholder="Your ref…"
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">PO Number</label>
                  <input
                    type="text"
                    value={poRef}
                    onChange={(e) => setPoRef(e.target.value)}
                    placeholder="PO-…"
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
                  />
                </div>
              </div>
            </div>

            {/* Line Items */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-700">Line Items</h2>
                {fieldErrors.lines && (
                  <p className="text-xs text-red-500 mt-1">{fieldErrors.lines}</p>
                )}
              </div>
              <InvoiceLineEditor
                lines={lines}
                taxRates={taxRates}
                onChange={setLines}
                currency={currency}
                disabled={saving}
              />
            </div>

            {/* Notes */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-4">Notes</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Customer Notes{" "}
                    <span className="text-slate-400">(visible on invoice)</span>
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={3}
                    placeholder="Thank you for your business…"
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Payment Terms / Footer Text{" "}
                    <span className="text-slate-400">(visible on invoice)</span>
                  </label>
                  <textarea
                    value={terms}
                    onChange={(e) => setTerms(e.target.value)}
                    rows={2}
                    placeholder="Payment due within 30 days…"
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">
                    Internal Notes{" "}
                    <span className="text-slate-400">(not visible to customer)</span>
                  </label>
                  <textarea
                    value={internalNotes}
                    onChange={(e) => setInternalNotes(e.target.value)}
                    rows={2}
                    placeholder="Internal context…"
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none bg-amber-50 border-amber-200"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Totals */}
            <InvoiceTotalsPanel lines={lines} taxRates={taxRates} currency={currency} />

            {/* Actions */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
              <button
                type="button"
                onClick={() => handleSave(false)}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 text-white text-sm font-semibold rounded-lg hover:bg-slate-700 disabled:opacity-60 transition-colors"
              >
                <Save className="h-4 w-4" />
                {saving ? "Saving…" : "Save as Draft"}
              </button>
              <button
                type="button"
                onClick={() => handleSave(true)}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors"
              >
                <CheckCircle className="h-4 w-4" />
                {saving ? "Processing…" : "Save & Approve"}
              </button>
              <p className="text-[10px] text-slate-400 text-center leading-relaxed">
                Approving assigns an invoice number and locks the record.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
