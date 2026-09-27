"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Save,
  Send,
  AlertCircle,
  AlertTriangle,
  FileText,
  X,
  CheckCircle2,
  Receipt,
  ExternalLink,
  ArrowLeft,
  ShieldAlert,
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

function fmt(v: number, currency = "GBP") {
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function EditBillPage() {
  const router = useRouter();
  const params = useParams();
  const billId = params?.id as string;

  const [loadingBill, setLoadingBill] = useState(true);
  const [billStatus, setBillStatus] = useState<string>("");
  const [internalBillNumber, setInternalBillNumber] = useState<string>("");
  const [version, setVersion] = useState<number>(1);

  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [supplierInvoiceNumber, setSupplierInvoiceNumber] = useState("");
  const [billDate, setBillDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [currency, setCurrency] = useState("GBP");
  const [paymentTermId, setPaymentTermId] = useState("");
  const [supplierRef, setSupplierRef] = useState("");
  const [poRef, setPoRef] = useState("");
  const [notes, setNotes] = useState("");
  const [internalNotes, setInternalNotes] = useState("");

  const [lines, setLines] = useState<BillLineItem[]>([]);
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTermOption[]>([]);

  // Duplicate Check State
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateMatch[] | null>(null);
  const [duplicateSeverity, setDuplicateSeverity] = useState<string>("NONE");
  const [overrideReason, setOverrideReason] = useState("");
  const [showOverrideModal, setShowOverrideModal] = useState(false);

  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  useEffect(() => {
    async function resolveOrg() {
      try {
        const res = await fetch("/api/v1/organisations/", { credentials: "include" });
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) {
            setActiveOrgId(orgs[0].id);
          }
        }
      } catch {
        // Fallback
      }
    }
    resolveOrg();
  }, []);

  const orgId = activeOrgId || ORG_ID;

  // 1. Fetch Tax Rates & Payment Terms
  useEffect(() => {
    if (!orgId) return;
    async function loadConfig() {
      try {
        const [taxesRes, termsRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/organisations/${orgId}/tax-rates`, { credentials: "include" }),
          fetch(`${API_BASE}/api/v1/organisations/${orgId}/payment-terms`, { credentials: "include" }),
        ]);

        if (taxesRes.ok) {
          const t = await taxesRes.json();
          setTaxRates(t.items || t || []);
        }
        if (termsRes.ok) {
          const pt = await termsRes.json();
          setPaymentTerms(pt.items || pt || []);
        }
      } catch {
        // Fallback gracefully
      }
    }
    loadConfig();
  }, [orgId]);

  // 2. Fetch Existing Bill
  useEffect(() => {
    if (!billId || !orgId) return;
    async function loadBill() {
      setLoadingBill(true);
      try {
        const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}`, {
          credentials: "include",
        });
        if (!res.ok) {
          throw new Error("Failed to load bill");
        }
        const data = await res.json();

        setBillStatus(data.status);
        setInternalBillNumber(data.internal_bill_number || "");
        setVersion(data.version || 1);

        setSupplier({
          id: data.supplier_id,
          business_name: data.supplier_name_snapshot || "Supplier",
          email: data.supplier_email_snapshot || "",
          vat_number: data.supplier_vat_number_snapshot || "",
          contact_type: "SUPPLIER",
        });

        setSupplierInvoiceNumber(data.supplier_invoice_number || "");
        setBillDate(data.bill_date ? data.bill_date.split("T")[0] : "");
        setDueDate(data.due_date ? data.due_date.split("T")[0] : "");
        setCurrency(data.currency || "GBP");
        setPaymentTermId(data.payment_terms_id || "");
        setSupplierRef(data.supplier_reference || "");
        setPoRef(data.purchase_order_reference || "");
        setNotes(data.notes || "");
        setInternalNotes(data.internal_notes || "");

        // Map lines
        if (data.lines && data.lines.length > 0) {
          setLines(
            data.lines.map((l: any, idx: number) => ({
              description: l.description,
              purchase_category: l.purchase_category || "General Expense",
              quantity: String(l.quantity),
              unit_price: String(l.unit_price),
              tax_rate_id: l.tax_rate_id || "",
              discount_type: l.discount_type || "",
              discount_value: String(l.discount_value || "0"),
              position: idx,
            }))
          );
        } else {
          setLines([
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
        }
      } catch (err: any) {
        setError(err.message || "Could not retrieve bill details.");
      } finally {
        setLoadingBill(false);
      }
    }
    loadBill();
  }, [billId]);

  // Handle Payment Term Change
  const handlePaymentTermChange = (termId: string) => {
    setPaymentTermId(termId);
    if (!termId || !billDate) return;
    const term = paymentTerms.find((t) => t.id === termId);
    if (term) {
      const d = new Date(billDate);
      d.setDate(d.getDate() + term.days);
      setDueDate(d.toISOString().split("T")[0]);
    }
  };

  // Calculate live totals
  const subtotal = lines.reduce((acc, l) => acc + calcBillLine(l, taxRates).net, 0);
  const taxTotal = lines.reduce((acc, l) => acc + calcBillLine(l, taxRates).tax, 0);
  const total = subtotal + taxTotal;

  // 3. Live Duplicate Check
  const checkDuplicates = async () => {
    if (!supplier || !supplierInvoiceNumber.trim()) {
      setDuplicateWarning(null);
      setDuplicateSeverity("NONE");
      return null;
    }

    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/check-duplicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          supplier_id: supplier.id,
          supplier_invoice_number: supplierInvoiceNumber.trim(),
          bill_date: billDate || null,
          total: total > 0 ? total : null,
          exclude_bill_id: billId,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.is_duplicate) {
          setDuplicateWarning(data.matches);
          setDuplicateSeverity(data.severity);
          return data;
        } else {
          setDuplicateWarning(null);
          setDuplicateSeverity("NONE");
          return null;
        }
      }
    } catch {
      // Ignore background check failure
    }
    return null;
  };

  const handleSave = async (submitAfterSave = false) => {
    setError("");

    if (!supplier) {
      setError("Please select a supplier.");
      return;
    }
    if (!supplierInvoiceNumber.trim()) {
      setError("Supplier invoice number is required.");
      return;
    }
    if (!billDate) {
      setError("Bill date is required.");
      return;
    }
    if (!dueDate) {
      setError("Due date is required.");
      return;
    }
    if (lines.length === 0 || !lines.some((l) => l.description.trim())) {
      setError("Please add at least one line item with a description.");
      return;
    }

    // Check duplicate if not overridden
    if (!overrideReason) {
      const dup = await checkDuplicates();
      if (dup && dup.is_duplicate) {
        setShowOverrideModal(true);
        return;
      }
    }

    submitAfterSave ? setSubmitting(true) : setSaving(true);

    try {
      const payload = {
        version: version,
        supplier_id: supplier.id,
        supplier_invoice_number: supplierInvoiceNumber.trim(),
        bill_date: billDate,
        due_date: dueDate,
        currency,
        payment_terms_id: paymentTermId || null,
        supplier_reference: supplierRef || null,
        purchase_order_reference: poRef || null,
        notes: notes || null,
        internal_notes: internalNotes || null,
        duplicate_override_reason: overrideReason || null,
        lines: lines
          .filter((l) => l.description.trim())
          .map((l, idx) => ({
            description: l.description.trim(),
            purchase_category: l.purchase_category || "General Expense",
            quantity: parseFloat(l.quantity) || 1,
            unit_price: parseFloat(l.unit_price) || 0,
            tax_rate_id: l.tax_rate_id || null,
            discount_type: l.discount_type || null,
            discount_value: parseFloat(l.discount_value) || 0,
            position: idx,
          })),
      };

      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || errData.message || "Failed to update bill.");
      }

      if (submitAfterSave) {
        // Submit for approval
        const subRes = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ comment: "Updated and submitted from bill editor." }),
        });
        if (!subRes.ok) {
          const subErr = await subRes.json();
          alert(`Saved bill, but submission failed: ${subErr.detail || subErr.message}`);
        }
      }

      router.push(`/app/purchases/bills/${billId}`);
    } catch (err: any) {
      setError(err.message || "Failed to save bill.");
    } finally {
      setSaving(false);
      setSubmitting(false);
    }
  };

  if (loadingBill) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#0073B7] border-t-transparent mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading bill editor...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  // Guard: Approved, Awaiting Payment, or Void bills cannot be edited directly
  const isEditable = billStatus === "DRAFT" || billStatus === "REJECTED" || billStatus === "AWAITING_APPROVAL";
  if (!isEditable) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-12 p-8 bg-white border border-slate-200 rounded-lg text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">This bill cannot be edited directly</h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Bill <span className="font-mono font-bold text-slate-800">{internalBillNumber || billId}</span> has already
            been approved or voided ({billStatus}). To preserve accounting integrity, approved bills cannot be modified.
            If adjustments are required, you must void this bill or issue a supplier credit note.
          </p>
          <div className="pt-2">
            <Link
              href={`/app/purchases/bills/${billId}`}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0073B7] text-white text-xs font-semibold hover:bg-[#005f96] transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Return to Bill
            </Link>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-6 pb-16">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <Link
            href={`/app/purchases/bills/${billId}`}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
            Cancel & Return to Bill
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-1 rounded">
              {internalBillNumber || "Draft Bill"}
            </span>
          </div>
        </div>

        {/* Page Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Edit Supplier Bill</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Update line items, invoice reference, and dates for this bill.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleSave(false)}
              disabled={saving || submitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {saving ? "Saving Changes..." : "Save Changes"}
            </button>
            <button
              onClick={() => handleSave(true)}
              disabled={saving || submitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              {submitting ? "Submitting..." : "Save & Submit for Approval"}
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError("")} className="text-red-500 hover:text-red-700">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* ── Bill Details Form ────────────────────────────── */}
        <div className="p-6 rounded-lg border border-slate-200 bg-white shadow-sm space-y-6">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Bill Header & Supplier</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Supplier Selector */}
            <div className="md:col-span-1">
              <SupplierSelector
                orgId={orgId}
                value={supplier}
                onChange={(s) => {
                  setSupplier(s);
                  if (s && s.payment_terms_id) {
                    handlePaymentTermChange(s.payment_terms_id);
                  }
                }}
              />
            </div>

            {/* Supplier Invoice Number */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Supplier Invoice # <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={supplierInvoiceNumber}
                onChange={(e) => setSupplierInvoiceNumber(e.target.value)}
                onBlur={checkDuplicates}
                placeholder="e.g. INV-99823 or MS-882931"
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-2 font-mono focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
              <p className="text-[11px] text-slate-400 mt-1">Invoice number from supplier&apos;s bill</p>
            </div>

            {/* Currency */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              >
                <option value="GBP">GBP (£) - British Pound</option>
                <option value="USD">USD ($) - US Dollar</option>
                <option value="EUR">EUR (€) - Euro</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2 border-t border-slate-100">
            {/* Bill Date */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Bill Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={billDate}
                onChange={(e) => setBillDate(e.target.value)}
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
            </div>

            {/* Payment Terms */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Terms</label>
              <select
                value={paymentTermId}
                onChange={(e) => handlePaymentTermChange(e.target.value)}
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              >
                <option value="">Custom Due Date</option>
                {paymentTerms.map((pt) => (
                  <option key={pt.id} value={pt.id}>
                    {pt.name} ({pt.days} days)
                  </option>
                ))}
              </select>
            </div>

            {/* Due Date */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Due Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
            </div>

            {/* Purchase Order Ref */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">PO Reference</label>
              <input
                type="text"
                value={poRef}
                onChange={(e) => setPoRef(e.target.value)}
                placeholder="e.g. PO-2026-0044"
                className="w-full text-xs rounded-md border border-slate-300 px-3 py-1.5 font-mono focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
            </div>
          </div>
        </div>

        {/* ── Line Items Editor ────────────────────────────── */}
        <div className="p-6 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Purchase Line Items</h2>
            <span className="text-xs text-slate-400">All prices in {currency}</span>
          </div>

          <BillLineEditor lines={lines} onChange={setLines} taxRates={taxRates} currency={currency} />

          {/* Totals Summary */}
          <div className="flex justify-end pt-4 border-t border-slate-100">
            <div className="w-72 space-y-2 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Subtotal (Net)</span>
                <span className="font-mono font-medium">{fmt(subtotal, currency)}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Tax / VAT Total</span>
                <span className="font-mono font-medium">{fmt(taxTotal, currency)}</span>
              </div>
              <div className="border-t border-slate-200 pt-2 flex justify-between text-sm font-bold text-slate-900">
                <span>Total Amount Due</span>
                <span className="font-mono">{fmt(total, currency)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Notes ────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-2">
            <label className="block text-xs font-semibold text-slate-700">General Notes</label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Annual cloud hosting bill for accounting infrastructure."
              className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
            />
          </div>

          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-2">
            <label className="block text-xs font-semibold text-slate-700">
              Internal Notes <span className="text-[11px] font-normal text-slate-400">(Finance Only)</span>
            </label>
            <textarea
              rows={3}
              value={internalNotes}
              onChange={(e) => setInternalNotes(e.target.value)}
              placeholder="e.g. Pre-approved by Engineering Director."
              className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
            />
          </div>
        </div>

        {/* Duplicate Warning Modal / Prompt */}
        {showOverrideModal && duplicateWarning && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg max-w-lg w-full p-6 shadow-xl space-y-4">
              <div className="flex items-center gap-3 text-amber-600">
                <AlertTriangle className="h-6 w-6 flex-shrink-0" />
                <h3 className="text-base font-bold text-slate-900">Potential Duplicate Bill Detected</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                A supplier invoice with the same or similar invoice number was found for this supplier.
              </p>

              <div className="space-y-2 max-h-48 overflow-y-auto">
                {duplicateWarning.map((m) => (
                  <div key={m.bill_id} className="p-3 bg-amber-50/70 border border-amber-200 rounded-md text-xs space-y-1">
                    <div className="flex justify-between font-semibold text-amber-950">
                      <span>{m.internal_bill_number || "Bill"}</span>
                      <span>{fmt(m.total, m.currency)}</span>
                    </div>
                    <div className="text-amber-800 text-[11px]">
                      Invoice #: <strong className="font-mono">{m.supplier_invoice_number}</strong> • Status: {m.status}
                    </div>
                    <p className="text-[11px] text-amber-700 italic">{m.reason}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-1 pt-2">
                <label className="block text-xs font-semibold text-slate-700">
                  Override Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={2}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain why this bill is valid despite the duplicate match (e.g. re-issued revision or verified recurring charge)"
                  className="w-full text-xs rounded-md border border-slate-300 p-2 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!overrideReason.trim()) {
                      alert("Please provide an override reason to continue.");
                      return;
                    }
                    setShowOverrideModal(false);
                    handleSave(false);
                  }}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-md shadow-sm transition-all"
                >
                  Confirm & Save Bill
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
