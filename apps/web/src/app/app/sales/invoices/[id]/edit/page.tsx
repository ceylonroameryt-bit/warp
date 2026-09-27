"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Save, AlertCircle, Ban } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import CustomerSelector from "@/components/CustomerSelector";
import InvoiceLineEditor, { LineItem, TaxRate } from "@/components/InvoiceLineEditor";
import InvoiceTotalsPanel from "@/components/InvoiceTotalsPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

export default function EditInvoicePage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const [invoice, setInvoice] = useState<any>(null);
  const [customer, setCustomer] = useState<any>(null);
  const [issueDate, setIssueDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [currency, setCurrency] = useState("GBP");
  const [paymentTermId, setPaymentTermId] = useState("");
  const [customerRef, setCustomerRef] = useState("");
  const [poRef, setPoRef] = useState("");
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("");
  const [internalNotes, setInternalNotes] = useState("");
  const [lines, setLines] = useState<LineItem[]>([]);
  const [taxRates, setTaxRates] = useState<TaxRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

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
    async function load() {
      if (!activeOrgId) return;
      try {
        const [invRes, taxRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${id}`, {
            credentials: "include",
          }),
          fetch(`${API_BASE}/api/v1/organisations/${activeOrgId}/tax-rates`, {
            credentials: "include",
          }),
        ]);

        if (invRes.ok) {
          const data = await invRes.json();
          if (data.status !== "DRAFT") {
            // Redirect away — only drafts are editable
            router.replace(`/app/sales/invoices/${id}`);
            return;
          }
          setInvoice(data);
          setIssueDate(data.issue_date?.split("T")[0] ?? "");
          setDueDate(data.due_date?.split("T")[0] ?? "");
          setCurrency(data.currency ?? "GBP");
          setPaymentTermId(data.payment_terms_id ?? "");
          setCustomerRef(data.customer_reference ?? "");
          setPoRef(data.purchase_order_reference ?? "");
          setNotes(data.notes ?? "");
          setTerms(data.terms ?? "");
          setInternalNotes(data.internal_notes ?? "");
          if (data.customer_id) {
            setCustomer({
              id: data.customer_id,
              business_name: data.customer_name_snapshot ?? "Unknown",
              email: data.customer_email_snapshot,
            });
          }
          setLines(
            (data.lines ?? []).map((l: any) => ({
              id: l.id,
              description: l.description,
              quantity: String(l.quantity),
              unit_price: String(l.unit_price),
              tax_rate_id: l.tax_rate_id ?? "",
              discount_type: l.discount_type ?? "",
              discount_value: String(l.discount_value ?? "0"),
              position: l.position,
            }))
          );
        } else {
          router.replace("/app/sales/invoices");
        }

        if (taxRes.ok) {
          setTaxRates(await taxRes.json());
        }
      } catch {
        setError("Failed to load invoice.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeOrgId, id, router]);

  async function handleSave() {
    if (!customer) { setError("Please select a customer."); return; }
    if (!lines.length) { setError("Add at least one line item."); return; }

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

      const res = await fetch(`${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data?.detail || "Failed to update invoice.");
        return;
      }
      router.push(`/app/sales/invoices/${id}?updated=1`);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 rounded-full border-2 border-sky-500 border-t-transparent" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-3 mb-6">
          <Link
            href={`/app/sales/invoices/${id}`}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Edit Draft Invoice
            </h1>
            <p className="text-xs text-slate-500">
              Edits are only permitted on DRAFT invoices
            </p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-5 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-5">
            {/* Customer */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Bill To</h2>
              <CustomerSelector orgId={activeOrgId} value={customer} onChange={setCustomer} disabled={saving} />
            </div>

            {/* Details */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-4">Invoice Details</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">Issue Date</label>
                  <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">Due Date</label>
                  <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">Currency</label>
                  <select value={currency} onChange={(e) => setCurrency(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white">
                    <option value="GBP">GBP</option>
                    <option value="EUR">EUR</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">Customer Ref</label>
                  <input type="text" value={customerRef} onChange={(e) => setCustomerRef(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 block mb-1">PO Number</label>
                  <input type="text" value={poRef} onChange={(e) => setPoRef(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
                </div>
              </div>
            </div>

            {/* Lines */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-100">
                <h2 className="text-sm font-semibold text-slate-700">Line Items</h2>
              </div>
              <InvoiceLineEditor lines={lines} taxRates={taxRates} onChange={setLines} currency={currency} disabled={saving} />
            </div>

            {/* Notes */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-700">Notes</h2>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">Customer Notes</label>
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">Terms</label>
                <textarea value={terms} onChange={(e) => setTerms(e.target.value)} rows={2}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">Internal Notes 🔒</label>
                <textarea value={internalNotes} onChange={(e) => setInternalNotes(e.target.value)} rows={2}
                  className="w-full px-3 py-2 text-sm border border-amber-200 rounded-lg focus:outline-none focus:border-amber-400 resize-none bg-amber-50" />
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <InvoiceTotalsPanel lines={lines} taxRates={taxRates} currency={currency} />
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <button type="button" onClick={handleSave} disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors">
                <Save className="h-4 w-4" />
                {saving ? "Saving…" : "Save Changes"}
              </button>
              <Link href={`/app/sales/invoices/${id}`}
                className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-slate-200 text-sm text-slate-600 rounded-lg hover:bg-slate-50 transition-colors">
                Cancel
              </Link>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
