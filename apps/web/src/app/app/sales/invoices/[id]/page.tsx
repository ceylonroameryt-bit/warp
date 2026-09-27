"use client";

import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Download,
  Send,
  CheckCircle,
  Ban,
  Pencil,
  MailOpen,
  FileText,
  Clock,
  ExternalLink,
  AlertCircle,
  X,
  CreditCard,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import InvoiceStatusBadge from "@/components/InvoiceStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface InvoiceLine {
  id: string;
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate_snapshot?: string;
  discount_type?: string;
  discount_value: string;
  net_amount: string;
  tax_amount: string;
  gross_amount: string;
  position: number;
}

interface Delivery {
  id: string;
  recipient_email: string;
  status: string;
  sent_at?: string;
  failure_reason?: string;
  created_at: string;
}

interface Invoice {
  id: string;
  customer_id?: string;
  invoice_number?: string;
  effective_status: string;
  status: string;
  customer_name_snapshot?: string;
  customer_email_snapshot?: string;
  customer_vat_number_snapshot?: string;
  billing_address_snapshot?: any;
  issue_date: string;
  due_date: string;
  currency: string;
  customer_reference?: string;
  purchase_order_reference?: string;
  payment_terms_id?: string;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  total: string;
  amount_paid: string;
  amount_due: string;
  notes?: string;
  terms?: string;
  internal_notes?: string;
  approved_at?: string;
  sent_at?: string;
  voided_at?: string;
  void_reason?: string;
  created_at: string;
  lines: InvoiceLine[];
  deliveries: Delivery[];
}

function fmt(v: string | number | undefined, currency = "GBP") {
  if (v === undefined) return "—";
  const n = typeof v === "string" ? parseFloat(v) : v;
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${n.toLocaleString("en-GB", { minimumFractionDigits: 2 })}`;
}

function fmtDate(d: string | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function fmtDateTime(d: string | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Send Modal ───────────────────────────────────────────────
function SendModal({
  invoice,
  orgId,
  onClose,
  onSent,
}: {
  invoice: Invoice;
  orgId: string;
  onClose: () => void;
  onSent: () => void;
}) {
  const [to, setTo] = useState(invoice.customer_email_snapshot || "");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState(
    `Invoice ${invoice.invoice_number || "Draft"} — payment due ${fmtDate(invoice.due_date)}`
  );
  const [message, setMessage] = useState(
    `Hi ${invoice.customer_name_snapshot || "there"},\n\nPlease find attached invoice ${invoice.invoice_number || ""} for ${fmt(invoice.total, invoice.currency)}.\n\nPayment is due by ${fmtDate(invoice.due_date)}.\n\nThank you for your business.`
  );
  const [attachPdf, setAttachPdf] = useState(true);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState("");

  async function handleSend() {
    if (!to) { setErr("Recipient email is required."); return; }
    setSending(true); setErr("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/invoices/${invoice.id}/send`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ recipient_email: to, cc: cc || null, subject, message, attach_pdf: attachPdf }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        setErr(data?.detail || "Failed to queue email.");
        return;
      }
      onSent();
    } catch {
      setErr("Network error.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800 flex items-center gap-2">
            <MailOpen className="h-4 w-4 text-sky-600" /> Send Invoice
          </h2>
          <button onClick={onClose} className="p-1 hover:text-slate-700 text-slate-400">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {err && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {err}
            </div>
          )}
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1">To *</label>
            <input type="email" value={to} onChange={(e) => setTo(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1">CC</label>
            <input type="email" value={cc} onChange={(e) => setCc(e.target.value)} placeholder="Optional…"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1">Subject</label>
            <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1">Message</label>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={5}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 resize-none" />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={attachPdf} onChange={(e) => setAttachPdf(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400" />
            <span className="text-sm text-slate-700">Attach PDF invoice</span>
          </label>
        </div>
        <div className="flex gap-3 px-6 pb-6">
          <button onClick={onClose}
            className="flex-1 py-2.5 border border-slate-200 text-sm rounded-lg text-slate-600 hover:bg-slate-50 transition-colors">
            Cancel
          </button>
          <button onClick={handleSend} disabled={sending}
            className="flex-1 py-2.5 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors">
            {sending ? "Queueing…" : "Send Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Void Modal ───────────────────────────────────────────────
function VoidModal({
  invoice,
  orgId,
  onClose,
  onVoided,
}: {
  invoice: Invoice;
  orgId: string;
  onClose: () => void;
  onVoided: () => void;
}) {
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function handleVoid() {
    if (!reason.trim()) { setErr("A reason is required."); return; }
    setLoading(true); setErr("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/invoices/${invoice.id}/void`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ reason }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        setErr(data?.detail || "Failed to void invoice.");
        return;
      }
      onVoided();
    } catch {
      setErr("Network error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-red-100 bg-red-50 rounded-t-2xl">
          <h2 className="font-semibold text-red-700 flex items-center gap-2">
            <Ban className="h-4 w-4" /> Void Invoice
          </h2>
          <button onClick={onClose} className="p-1 hover:text-red-700 text-red-400">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-600">
            This will permanently void invoice <strong>{invoice.invoice_number}</strong>. The
            record will be retained for audit purposes.
          </p>
          {err && <p className="text-xs text-red-600">{err}</p>}
          <div>
            <label className="text-xs font-medium text-slate-500 block mb-1">Reason *</label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
              placeholder="Reason for voiding this invoice…"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-red-400 resize-none" />
          </div>
        </div>
        <div className="flex gap-3 px-6 pb-6">
          <button onClick={onClose}
            className="flex-1 py-2.5 border border-slate-200 text-sm rounded-lg text-slate-600 hover:bg-slate-50 transition-colors">
            Cancel
          </button>
          <button onClick={handleVoid} disabled={loading}
            className="flex-1 py-2.5 bg-red-600 text-white text-sm font-semibold rounded-lg hover:bg-red-700 disabled:opacity-60 transition-colors">
            {loading ? "Voiding…" : "Void Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────
function InvoiceDetailContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const invoiceId = params.id as string;

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [showVoidModal, setShowVoidModal] = useState(false);
  const [notice, setNotice] = useState(searchParams.get("new") === "1" ? "Invoice created successfully!" : "");
  const [actionErr, setActionErr] = useState("");

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

  async function loadInvoice() {
    if (!activeOrgId) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${invoiceId}`,
        { credentials: "include" }
      );
      if (res.ok) {
        setInvoice(await res.json());
      } else if (res.status === 404) {
        router.replace("/app/sales/invoices");
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activeOrgId) {
      loadInvoice();
    }
  }, [activeOrgId, invoiceId]);

  async function handleApprove() {
    if (!activeOrgId) return;
    setApproving(true); setActionErr("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${invoiceId}/approve`,
        { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: "{}" }
      );
      if (!res.ok) {
        const data = await res.json();
        setActionErr(data?.detail || "Approval failed.");
        return;
      }
      await loadInvoice();
      setNotice("Invoice approved successfully.");
    } catch {
      setActionErr("Network error.");
    } finally {
      setApproving(false);
    }
  }

  async function handleGeneratePdf() {
    if (!activeOrgId) return;
    setGeneratingPdf(true); setActionErr("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${invoiceId}/pdf`,
        { method: "POST", credentials: "include" }
      );
      if (!res.ok) { setActionErr("PDF generation failed."); return; }
      // Download
      const dlRes = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices/${invoiceId}/pdf`,
        { credentials: "include" }
      );
      if (dlRes.ok) {
        const { download_url } = await dlRes.json();
        if (download_url) window.open(download_url, "_blank");
        else setNotice("PDF generated. Check files section.");
      }
    } catch {
      setActionErr("Network error.");
    } finally {
      setGeneratingPdf(false);
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

  if (!invoice) return null;

  const isDraft = invoice.status === "DRAFT";
  const canApprove = isDraft;
  const canSend = !["DRAFT", "VOID"].includes(invoice.status);
  const canPay = !["DRAFT", "VOID", "PAID"].includes(invoice.status);
  const canVoid = !["DRAFT", "VOID", "PAID"].includes(invoice.status);
  const canEdit = isDraft;

  return (
    <DashboardLayout>
      {showSendModal && (
        <SendModal
          invoice={invoice}
          orgId={activeOrgId}
          onClose={() => setShowSendModal(false)}
          onSent={() => {
            setShowSendModal(false);
            setNotice("Invoice queued for delivery.");
            loadInvoice();
          }}
        />
      )}
      {showVoidModal && (
        <VoidModal
          invoice={invoice}
          orgId={activeOrgId}
          onClose={() => setShowVoidModal(false)}
          onVoided={() => {
            setShowVoidModal(false);
            setNotice("Invoice voided.");
            loadInvoice();
          }}
        />
      )}

      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        {/* Back + Header */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div className="flex items-start gap-3">
            <Link
              href="/app/sales/invoices"
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors mt-0.5"
            >
              <ChevronLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-bold text-slate-900">
                  {invoice.invoice_number || "Draft Invoice"}
                </h1>
                <InvoiceStatusBadge status={invoice.effective_status} />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {invoice.customer_name_snapshot || "No customer"} ·
                Created {fmtDate(invoice.created_at)}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-2">
            {canEdit && (
              <Link
                href={`/app/sales/invoices/${invoice.id}/edit`}
                className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 text-sm font-medium text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Link>
            )}
            {canApprove && (
              <button
                onClick={handleApprove}
                disabled={approving}
                className="flex items-center gap-1.5 px-3 py-2 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors"
              >
                <CheckCircle className="h-3.5 w-3.5" />
                {approving ? "Approving…" : "Approve"}
              </button>
            )}
            {canSend && (
              <button
                onClick={() => setShowSendModal(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-700 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 transition-colors"
              >
                <Send className="h-3.5 w-3.5" />
                Send
              </button>
            )}
            {canPay && (
              <Link
                href={`/app/payments/new?type=INCOMING&contact_id=${invoice.customer_id || ""}&invoice_id=${invoice.id}`}
                className="flex items-center gap-1.5 px-3 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 transition-colors"
              >
                <CreditCard className="h-3.5 w-3.5" />
                Record Payment
              </Link>
            )}
            <button
              onClick={handleGeneratePdf}
              disabled={generatingPdf}
              className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 text-sm font-medium text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-60 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              {generatingPdf ? "Generating…" : "PDF"}
            </button>
            {canVoid && (
              <button
                onClick={() => setShowVoidModal(true)}
                className="flex items-center gap-1.5 px-3 py-2 border border-red-200 text-sm font-medium text-red-600 rounded-lg hover:bg-red-50 transition-colors"
              >
                <Ban className="h-3.5 w-3.5" />
                Void
              </button>
            )}
          </div>
        </div>

        {notice && (
          <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-2.5 mb-5 text-sm text-emerald-700">
            <span>{notice}</span>
            <button onClick={() => setNotice("")} className="ml-3">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        {actionErr && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5 mb-5 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" /> {actionErr}
            <button className="ml-auto" onClick={() => setActionErr("")}><X className="h-4 w-4" /></button>
          </div>
        )}

        {/* Void banner */}
        {invoice.status === "VOID" && invoice.void_reason && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 mb-5">
            <p className="text-sm font-semibold text-red-700 mb-1 flex items-center gap-2">
              <Ban className="h-4 w-4" /> Invoice Voided
            </p>
            <p className="text-sm text-red-600">{invoice.void_reason}</p>
            {invoice.voided_at && (
              <p className="text-xs text-red-400 mt-1">{fmtDateTime(invoice.voided_at)}</p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Invoice Preview */}
          <div className="lg:col-span-2 space-y-4">
            {/* Header Block */}
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <div className="grid grid-cols-2 gap-8 mb-6">
                {/* Bill To */}
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Bill To</p>
                  <p className="font-semibold text-slate-800">{invoice.customer_name_snapshot}</p>
                  {invoice.customer_email_snapshot && (
                    <p className="text-sm text-slate-500">{invoice.customer_email_snapshot}</p>
                  )}
                  {invoice.billing_address_snapshot && (
                    <div className="text-sm text-slate-500 mt-1">
                      {invoice.billing_address_snapshot.line1 && <p>{invoice.billing_address_snapshot.line1}</p>}
                      {invoice.billing_address_snapshot.city && <p>{invoice.billing_address_snapshot.city}</p>}
                      {invoice.billing_address_snapshot.postcode && <p>{invoice.billing_address_snapshot.postcode}</p>}
                    </div>
                  )}
                  {invoice.customer_vat_number_snapshot && (
                    <p className="text-xs text-slate-400 mt-1">VAT: {invoice.customer_vat_number_snapshot}</p>
                  )}
                </div>

                {/* Dates */}
                <div className="space-y-2">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Issue Date</p>
                    <p className="text-sm font-medium text-slate-800">{fmtDate(invoice.issue_date)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Due Date</p>
                    <p className="text-sm font-medium text-slate-800">{fmtDate(invoice.due_date)}</p>
                  </div>
                  {invoice.customer_reference && (
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Ref</p>
                      <p className="text-sm text-slate-800">{invoice.customer_reference}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Lines */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-800 text-slate-200 text-xs">
                      <th className="px-3 py-2 text-left rounded-l-lg">Description</th>
                      <th className="px-3 py-2 text-right">Qty</th>
                      <th className="px-3 py-2 text-right">Unit Price</th>
                      <th className="px-3 py-2 text-right">VAT</th>
                      <th className="px-3 py-2 text-right rounded-r-lg">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {invoice.lines.map((line) => (
                      <tr key={line.id} className="hover:bg-slate-50">
                        <td className="px-3 py-3 font-medium text-slate-800">{line.description}</td>
                        <td className="px-3 py-3 text-right text-slate-600">
                          {parseFloat(line.quantity) % 1 === 0 ? parseInt(line.quantity) : parseFloat(line.quantity).toFixed(2)}
                        </td>
                        <td className="px-3 py-3 text-right text-slate-600">
                          {fmt(line.unit_price, invoice.currency)}
                        </td>
                        <td className="px-3 py-3 text-right text-slate-500">
                          {line.tax_rate_snapshot ? `${parseFloat(line.tax_rate_snapshot)}%` : "—"}
                        </td>
                        <td className="px-3 py-3 text-right font-semibold text-slate-800">
                          {fmt(line.gross_amount, invoice.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totals */}
              <div className="flex justify-end mt-4">
                <div className="w-56 space-y-1.5">
                  <div className="flex justify-between text-sm text-slate-600 border-t border-slate-200 pt-2">
                    <span>Subtotal</span>
                    <span className="font-medium tabular-nums">{fmt(invoice.subtotal, invoice.currency)}</span>
                  </div>
                  {parseFloat(invoice.discount_total) > 0 && (
                    <div className="flex justify-between text-sm text-emerald-600">
                      <span>Discount</span>
                      <span className="font-medium tabular-nums">−{fmt(invoice.discount_total, invoice.currency)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm text-slate-600">
                    <span>VAT</span>
                    <span className="font-medium tabular-nums">{fmt(invoice.tax_total, invoice.currency)}</span>
                  </div>
                  <div className="flex justify-between border-t-2 border-slate-800 pt-2">
                    <span className="font-bold text-slate-900">Total</span>
                    <span className="text-lg font-bold text-slate-900 tabular-nums">
                      {fmt(invoice.total, invoice.currency)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Notes */}
              {(invoice.notes || invoice.terms) && (
                <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {invoice.notes && (
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Notes</p>
                      <p className="text-sm text-slate-600 whitespace-pre-wrap">{invoice.notes}</p>
                    </div>
                  )}
                  {invoice.terms && (
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Terms</p>
                      <p className="text-sm text-slate-600 whitespace-pre-wrap">{invoice.terms}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Internal notes */}
            {invoice.internal_notes && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <p className="text-[10px] font-bold text-amber-600 uppercase tracking-wider mb-1 flex items-center gap-1">
                  🔒 Internal Notes (not shown to customer)
                </p>
                <p className="text-sm text-amber-900 whitespace-pre-wrap">{invoice.internal_notes}</p>
              </div>
            )}

            {/* Delivery History */}
            {invoice.deliveries.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 border-b border-slate-100">
                  <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <MailOpen className="h-4 w-4 text-slate-400" />
                    Delivery History
                  </h2>
                </div>
                <div className="divide-y divide-slate-50">
                  {invoice.deliveries.map((d) => (
                    <div key={d.id} className="flex items-center justify-between px-5 py-3">
                      <div>
                        <p className="text-sm font-medium text-slate-800">{d.recipient_email}</p>
                        <p className="text-xs text-slate-400">{fmtDateTime(d.created_at)}</p>
                      </div>
                      <InvoiceStatusBadge status={d.status} size="sm" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Amount Due Card */}
            <div className="bg-slate-900 rounded-xl p-5 text-white">
              <p className="text-xs font-medium text-slate-400 mb-1">Amount Due</p>
              <p className="text-3xl font-bold tabular-nums">
                {fmt(invoice.amount_due, invoice.currency)}
              </p>
              {parseFloat(invoice.amount_paid) > 0 && (
                <p className="text-xs text-emerald-400 mt-2">
                  {fmt(invoice.amount_paid, invoice.currency)} paid
                </p>
              )}
            </div>

            {/* Timeline */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-400" />
                Timeline
              </h2>
              <div className="space-y-3">
                <div className="flex gap-3">
                  <div className="h-2 w-2 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-slate-700">Created</p>
                    <p className="text-xs text-slate-400">{fmtDateTime(invoice.created_at)}</p>
                  </div>
                </div>
                {invoice.approved_at && (
                  <div className="flex gap-3">
                    <div className="h-2 w-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-slate-700">Approved</p>
                      <p className="text-xs text-slate-400">{fmtDateTime(invoice.approved_at)}</p>
                    </div>
                  </div>
                )}
                {invoice.sent_at && (
                  <div className="flex gap-3">
                    <div className="h-2 w-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-slate-700">Sent</p>
                      <p className="text-xs text-slate-400">{fmtDateTime(invoice.sent_at)}</p>
                    </div>
                  </div>
                )}
                {invoice.voided_at && (
                  <div className="flex gap-3">
                    <div className="h-2 w-2 rounded-full bg-red-500 mt-1.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-slate-700">Voided</p>
                      <p className="text-xs text-slate-400">{fmtDateTime(invoice.voided_at)}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function InvoiceDetailPage() {
  return (
    <React.Suspense fallback={null}>
      <InvoiceDetailContent />
    </React.Suspense>
  );
}
