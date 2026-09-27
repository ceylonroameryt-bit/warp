"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Save,
  FileClock,
  AlertCircle,
  AlertTriangle,
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  Receipt,
  ExternalLink,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import SupplierSelector, { Supplier } from "@/components/SupplierSelector";
import BillLineEditor, {
  BillLineItem,
  TaxRate,
  calcBillLine,
} from "@/components/BillLineEditor";

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

function fmt(v: number, currency = "GBP") {
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface PaymentTermOption {
  id: string;
  name: string;
  days: number;
}

interface DuplicateMatch {
  bill_id: string;
  internal_bill_number?: string;
  supplier_invoice_number: string;
  supplier_name?: string;
  bill_date: string;
  total: number;
  currency: string;
  status: string;
  match_type: string;
  confidence_score: number;
  reason: string;
}

export default function NewBillPage() {
  const router = useRouter();

  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [supplierInvoiceNumber, setSupplierInvoiceNumber] = useState("");
  const [billDate, setBillDate] = useState(todayIso());
  const [dueDate, setDueDate] = useState(inDaysIso(30));
  const [currency, setCurrency] = useState("GBP");
  const [paymentTermId, setPaymentTermId] = useState("");
  const [supplierRef, setSupplierRef] = useState("");
  const [poRef, setPoRef] = useState("");
  const [notes, setNotes] = useState("");
  const [internalNotes, setInternalNotes] = useState("");

  const [lines, setLines] = useState<BillLineItem[]>([
    {
      description: "",
      purchase_category: "General Expense",
      quantity: "1",
      unit_price: "0.00",
      tax_rate_id: "",
      discount_type: "",
      discount_value: "0",
      position: 0,
    },
  ]);

  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTermOption[]>([]);

  // Attached File State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Duplicate Check State
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateMatch[] | null>(null);
  const [duplicateSeverity, setDuplicateSeverity] = useState<string>("NONE");
  const [duplicateOverrideReason, setDuplicateOverrideReason] = useState("");
  const [showOverrideInput, setShowOverrideInput] = useState(false);

  // UI state
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  // Load Tax Rates and Payment Terms with Dynamic Org Resolution
  useEffect(() => {
    async function init() {
      let org = ORG_ID;
      try {
        const res = await fetch("/api/v1/organisations/", { credentials: "include" });
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) {
            org = orgs[0].id;
            setActiveOrgId(org);
          }
        }
      } catch {
        // Fallback
      }

      if (!org) return;

      Promise.all([
        fetch(`${API_BASE}/api/v1/organisations/${org}/tax-rates`, { credentials: "include" })
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => []),
        fetch(`${API_BASE}/api/v1/organisations/${org}/payment-terms`, { credentials: "include" })
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => []),
      ]).then(([taxes, terms]) => {
        setTaxRates(taxes);
        if (taxes.length > 0) {
          setLines((prev) => prev.map((l) => ({ ...l, tax_rate_id: taxes[0].id })));
        }
        setPaymentTerms(Array.isArray(terms) ? terms : terms.items || []);
      });
    }

    init();
  }, []);

  const orgId = activeOrgId || ORG_ID;

  // Update payment terms when supplier is selected
  useEffect(() => {
    if (supplier?.payment_terms_id) {
      setPaymentTermId(supplier.payment_terms_id);
      const pt = paymentTerms.find((t) => t.id === supplier.payment_terms_id);
      if (pt) setDueDate(inDaysIso(pt.days));
    }
  }, [supplier, paymentTerms]);

  // Handle manual payment term change
  const handleTermChange = (termId: string) => {
    setPaymentTermId(termId);
    const pt = paymentTerms.find((t) => t.id === termId);
    if (pt) setDueDate(inDaysIso(pt.days));
  };

  // Live duplicate check on invoice number blur or supplier change
  useEffect(() => {
    if (!supplier || !supplierInvoiceNumber.trim() || !orgId) {
      setDuplicateWarning(null);
      setDuplicateSeverity("NONE");
      return;
    }

    const delay = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/check-duplicate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            supplier_id: supplier.id,
            supplier_invoice_number: supplierInvoiceNumber.trim(),
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.is_duplicate) {
            setDuplicateWarning(data.matches);
            setDuplicateSeverity(data.severity);
          } else {
            setDuplicateWarning(null);
            setDuplicateSeverity("NONE");
          }
        }
      } catch {
        // ignore network error
      }
    }, 400);

    return () => clearTimeout(delay);
  }, [supplier, supplierInvoiceNumber]);

  // Aggregate Totals
  const totals = lines.reduce(
    (acc, l) => {
      const { net, tax, gross } = calcBillLine(l, taxRates);
      return {
        subtotal: acc.subtotal + net,
        tax: acc.tax + tax,
        total: acc.total + gross,
      };
    },
    { subtotal: 0, tax: 0, total: 0 }
  );

  // Validation
  const validateForm = () => {
    const errs: Record<string, string> = {};
    if (!supplier) errs.supplier = "Supplier is required.";
    if (!supplierInvoiceNumber.trim()) errs.invoiceNumber = "Supplier invoice number is required.";
    if (!billDate) errs.billDate = "Bill date is required.";
    if (!dueDate) errs.dueDate = "Due date is required.";

    const hasValidLine = lines.some((l) => l.description.trim() && parseFloat(l.unit_price) >= 0);
    if (!hasValidLine) errs.lines = "At least one line item with a description is required.";

    if (duplicateSeverity === "BLOCK" && !duplicateOverrideReason.trim()) {
      errs.duplicate = "A duplicate invoice was detected. Please provide an override reason to continue.";
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // Submit handler (Draft or Direct Submit)
  const handleSave = async (submitForApproval = false) => {
    if (!validateForm()) {
      setError("Please fix the highlighted errors before continuing.");
      return;
    }

    if (submitForApproval) setSubmitting(true);
    else setSaving(true);
    setError("");

    try {
      const payload: any = {
        supplier_id: supplier!.id,
        supplier_invoice_number: supplierInvoiceNumber.trim(),
        bill_date: new Date(billDate).toISOString(),
        due_date: new Date(dueDate).toISOString(),
        currency,
        supplier_reference: supplierRef.trim() || undefined,
        purchase_order_reference: poRef.trim() || undefined,
        payment_terms_id: paymentTermId || undefined,
        notes: notes.trim() || undefined,
        internal_notes: internalNotes.trim() || undefined,
        duplicate_override_reason: duplicateOverrideReason.trim() || undefined,
        lines: lines.map((l, i) => ({
          description: l.description.trim() || "Item",
          purchase_category: l.purchase_category || "General Expense",
          quantity: l.quantity,
          unit_price: l.unit_price,
          tax_rate_id: l.tax_rate_id || undefined,
          discount_type: l.discount_type || undefined,
          discount_value: l.discount_value || "0",
          position: i,
        })),
      };

      // 1. Create Bill
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || "Failed to create supplier bill");
      }

      const createdBill = await res.json();
      const billId = createdBill.id;

      // 2. Upload file if selected
      if (selectedFile) {
        const formData = new FormData();
        formData.append("upload", selectedFile);
        formData.append("document_type", "ORIGINAL_INVOICE");

        await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/documents`, {
          method: "POST",
          credentials: "include",
          body: formData,
        });
      }

      // 3. If "Submit for Approval" clicked, transition status
      if (submitForApproval) {
        const subRes = await fetch(
          `${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/submit`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ comment: "Submitted on creation" }),
          }
        );
        if (!subRes.ok) {
          const subErr = await subRes.json().catch(() => ({}));
          throw new Error(subErr.message || "Saved as draft, but failed to submit for approval");
        }
      }

      router.push(`/app/purchases/bills/${billId}`);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred while saving the bill.");
    } finally {
      setSaving(false);
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-6">
        {/* ── Top Bar ── */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <Link
              href="/app/purchases/bills"
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors"
              title="Back to bills"
            >
              <ChevronLeft className="h-4 w-4" />
            </Link>
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Purchases / Bills
              </span>
              <h1 className="text-xl font-bold text-slate-900 leading-tight">Create Supplier Bill</h1>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              disabled={saving || submitting}
              onClick={() => handleSave(false)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs transition-colors disabled:opacity-50"
            >
              <Save className="h-4 w-4 text-slate-500" />
              {saving ? "Saving..." : "Save as Draft"}
            </button>
            <button
              type="button"
              disabled={saving || submitting}
              onClick={() => handleSave(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-sky-600 rounded-lg hover:bg-sky-500 shadow-sm transition-colors disabled:opacity-50"
            >
              <FileClock className="h-4 w-4" />
              {submitting ? "Submitting..." : "Submit for Approval"}
            </button>
          </div>
        </div>

        {/* ── Global Error Alert ── */}
        {error && (
          <div className="mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-rose-800 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
            <div className="flex-1">{error}</div>
            <button onClick={() => setError("")} className="text-rose-400 hover:text-rose-600">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* ── Duplicate Bill Warning Alert Banner ── */}
        {duplicateWarning && duplicateWarning.length > 0 && (
          <div
            className={`mt-4 p-4 rounded-xl border flex flex-col gap-3 ${
              duplicateSeverity === "BLOCK"
                ? "bg-amber-50/90 border-amber-300 text-amber-900"
                : "bg-sky-50 border-sky-200 text-sky-900"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <AlertTriangle
                  className={`h-5 w-5 shrink-0 mt-0.5 ${
                    duplicateSeverity === "BLOCK" ? "text-amber-600" : "text-sky-600"
                  }`}
                />
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wide">
                    {duplicateSeverity === "BLOCK"
                      ? "Possible Duplicate Bill Detected"
                      : "Similar Bill Detected"}
                  </h4>
                  <p className="text-xs mt-0.5">
                    An existing supplier bill matches invoice number{" "}
                    <span className="font-mono font-bold">{supplierInvoiceNumber}</span>.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white/80 rounded-lg border border-amber-200/60 p-3 text-xs divide-y divide-slate-100">
              {duplicateWarning.map((m) => (
                <div key={m.bill_id} className="py-1.5 first:pt-0 last:pb-0 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-800">{m.internal_bill_number}</span>
                    <span className="text-slate-400 mx-2">·</span>
                    <span>Invoice #{m.supplier_invoice_number}</span>
                    <span className="text-slate-400 mx-2">·</span>
                    <span className="font-bold">{fmt(m.total, m.currency)}</span>
                    <span className="text-slate-400 mx-2">·</span>
                    <span className="text-[11px] px-1.5 py-0.2 rounded bg-slate-100 border text-slate-600">
                      {m.status}
                    </span>
                  </div>
                  <Link
                    href={`/app/purchases/bills/${m.bill_id}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 font-semibold text-sky-600 hover:text-sky-700"
                  >
                    View Existing <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              ))}
            </div>

            {/* Override Option */}
            <div className="pt-2 border-t border-amber-200/60 flex flex-col gap-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium">
                <input
                  type="checkbox"
                  checked={showOverrideInput}
                  onChange={(e) => setShowOverrideInput(e.target.checked)}
                  className="rounded border-amber-300 text-sky-600 focus:ring-sky-400"
                />
                <span>I understand this is a duplicate number, continue anyway</span>
              </label>

              {showOverrideInput && (
                <div className="mt-1">
                  <input
                    type="text"
                    required
                    placeholder="Enter reason for duplicate override (required)..."
                    value={duplicateOverrideReason}
                    onChange={(e) => setDuplicateOverrideReason(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-amber-300 bg-white placeholder-slate-400 focus:outline-none focus:border-amber-500"
                  />
                  {fieldErrors.duplicate && (
                    <p className="mt-1 text-[11px] text-rose-600">{fieldErrors.duplicate}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Main Form Layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left 2 Cols: Core Metadata & Lines */}
          <div className="lg:col-span-2 space-y-6">
            {/* Metadata Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Supplier */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Supplier <span className="text-rose-500">*</span>
                  </label>
                  <SupplierSelector
                    orgId={ORG_ID}
                    value={supplier}
                    onChange={setSupplier}
                    error={fieldErrors.supplier}
                  />
                </div>

                {/* Supplier Invoice # */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Supplier Invoice # <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. MS-882931"
                    value={supplierInvoiceNumber}
                    onChange={(e) => setSupplierInvoiceNumber(e.target.value)}
                    className={`w-full px-3 py-2 text-xs rounded-lg border bg-white focus:outline-none ${
                      fieldErrors.invoiceNumber
                        ? "border-rose-400 focus:ring-2 focus:ring-rose-100"
                        : "border-slate-300 focus:border-sky-500"
                    }`}
                  />
                  {fieldErrors.invoiceNumber && (
                    <p className="mt-1 text-[11px] text-rose-500">{fieldErrors.invoiceNumber}</p>
                  )}
                </div>
              </div>

              {/* Dates & Payment Terms */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Bill Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={billDate}
                    onChange={(e) => setBillDate(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Payment Terms
                  </label>
                  <select
                    value={paymentTermId}
                    onChange={(e) => handleTermChange(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-slate-700 focus:outline-none focus:border-sky-500"
                  >
                    <option value="">Custom / Default (30 Days)</option>
                    {paymentTerms.map((pt) => (
                      <option key={pt.id} value={pt.id}>
                        {pt.name} ({pt.days} days)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Due Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              {/* References */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Supplier Reference
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Account Ref / Project ID"
                    value={supplierRef}
                    onChange={(e) => setSupplierRef(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Purchase Order (PO) Number
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. PO-2026-0044"
                    value={poRef}
                    onChange={(e) => setPoRef(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>
            </div>

            {/* Line Items Editor */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Purchase Line Items
                </h3>
              </div>
              <BillLineEditor
                lines={lines}
                taxRates={taxRates}
                onChange={setLines}
                currency={currency}
              />
              {fieldErrors.lines && (
                <p className="mt-1.5 text-[11px] text-rose-500">{fieldErrors.lines}</p>
              )}
            </div>

            {/* Notes */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Internal Finance Notes (Finance Team Only)
                </label>
                <textarea
                  rows={2}
                  placeholder="Notes about approvals, budget allocations, or payment instructions..."
                  value={internalNotes}
                  onChange={(e) => setInternalNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500 text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* Right Col: Totals & Document Upload */}
          <div className="space-y-6">
            {/* Financial Summary Box */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 pb-3 border-b border-slate-100">
                Bill Summary
              </h3>

              <div className="space-y-2.5 mt-4 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Net Subtotal</span>
                  <span className="font-mono font-medium">{fmt(totals.subtotal, currency)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>VAT / Tax Total</span>
                  <span className="font-mono font-medium">{fmt(totals.tax, currency)}</span>
                </div>
                <div className="pt-3 border-t border-slate-200 flex justify-between items-baseline">
                  <span className="text-sm font-bold text-slate-900">Total Payable</span>
                  <span className="text-xl font-black text-slate-900 font-mono">
                    {fmt(totals.total, currency)}
                  </span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex flex-col gap-2">
                <button
                  type="button"
                  disabled={saving || submitting}
                  onClick={() => handleSave(true)}
                  className="w-full py-2.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  <FileClock className="h-4 w-4" />
                  {submitting ? "Submitting..." : "Submit for Approval"}
                </button>
                <button
                  type="button"
                  disabled={saving || submitting}
                  onClick={() => handleSave(false)}
                  className="w-full py-2 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save as Draft"}
                </button>
              </div>
            </div>

            {/* Attach Original Supplier Invoice */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 pb-3 border-b border-slate-100 flex items-center justify-between">
                <span>Original Invoice Document</span>
                <span className="text-[10px] font-normal text-slate-400">PDF, JPG, PNG</span>
              </h3>

              <div className="mt-4">
                {selectedFile ? (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="h-9 w-9 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center shrink-0">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-800 truncate">
                          {selectedFile.name}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          {(selectedFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedFile(null)}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-sky-400 rounded-xl p-6 cursor-pointer bg-slate-50/50 hover:bg-sky-50/30 transition-colors">
                    <UploadCloud className="h-8 w-8 text-slate-400 mb-2" />
                    <span className="text-xs font-semibold text-slate-700">
                      Upload original supplier invoice
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5">
                      Drag & drop or browse from computer
                    </span>
                    <input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png,.heic"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setSelectedFile(e.target.files[0]);
                        }
                      }}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
                Supporting documents are verified with SHA-256 integrity checksums to protect
                against duplicate uploads.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
