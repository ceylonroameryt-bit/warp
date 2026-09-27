"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Receipt,
  FileCheck,
  AlertCircle,
  X,
  Search,
  ArrowRight,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import BillStatusBadge from "@/components/BillStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface BillItem {
  id: string;
  internal_bill_number?: string;
  supplier_invoice_number: string;
  supplier_name_snapshot?: string;
  bill_date: string;
  due_date: string;
  currency: string;
  total: number | string;
  status: string;
  effective_status: string;
  submitted_for_approval_at?: string;
  created_at: string;
}

function fmt(val: string | number | undefined, currency = "GBP") {
  if (val === undefined || val === null) return "—";
  const num = typeof val === "string" ? parseFloat(val) : val;
  const sym = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${sym}${num.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function timeWaiting(dateStr?: string) {
  if (!dateStr) return "Recently";
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} waiting`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? "s" : ""} waiting`;
}

export default function ApprovalsQueuePage() {
  const [bills, setBills] = useState<BillItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  // Approval / Rejection modal state
  const [selectedBill, setSelectedBill] = useState<BillItem | null>(null);
  const [modalType, setModalType] = useState<"approve" | "reject" | null>(null);
  const [commentOrReason, setCommentOrReason] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);

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

  const fetchQueue = async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/bills?status=AWAITING_APPROVAL&page_size=100`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setBills(data.items || []);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (orgId) {
      fetchQueue();
    }
  }, [orgId]);

  const handleAction = async () => {
    if (!selectedBill || !modalType || !orgId) return;
    if (modalType === "reject" && !commentOrReason.trim()) {
      alert("Rejection reason is required.");
      return;
    }

    setActionInProgress(true);
    try {
      const endpoint = modalType === "approve" ? "approve" : "reject";
      const body =
        modalType === "approve"
          ? { comment: commentOrReason || null }
          : { reason: commentOrReason };

      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/bills/${selectedBill.id}/${endpoint}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(body),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || `Failed to ${modalType} bill`);
        return;
      }

      setModalType(null);
      setSelectedBill(null);
      setCommentOrReason("");
      await fetchQueue();
    } catch {
      alert(`Error during ${modalType}`);
    } finally {
      setActionInProgress(false);
    }
  };

  const filteredBills = bills.filter((b) => {
    if (!search.trim()) return true;
    const s = search.toLowerCase();
    return (
      (b.supplier_name_snapshot && b.supplier_name_snapshot.toLowerCase().includes(s)) ||
      b.supplier_invoice_number.toLowerCase().includes(s) ||
      (b.internal_bill_number && b.internal_bill_number.toLowerCase().includes(s))
    );
  });

  const totalValue = bills.reduce((acc, b) => acc + (parseFloat(String(b.total)) || 0), 0);

  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto space-y-6 pb-12">
        {/* Page Title & Breadcrumb */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <Link href="/app/purchases" className="hover:text-slate-800">
                Purchases
              </Link>
              <span>/</span>
              <span className="text-slate-800 font-semibold">Approval Queue</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Supplier Bills Awaiting Approval
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Review and authorize pending purchase invoices before payment execution.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/app/purchases/bills"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
            >
              All Supplier Bills
            </Link>
          </div>
        </div>

        {/* ── KPI Stats Cards ──────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Bills In Queue</span>
              <Clock className="h-4 w-4 text-sky-600" />
            </div>
            <p className="text-2xl font-bold text-slate-900">{bills.length}</p>
            <p className="text-[11px] text-slate-400">Awaiting management review</p>
          </div>

          <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Total Queue Value</span>
              <Receipt className="h-4 w-4 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-slate-900">{fmt(totalValue)}</p>
            <p className="text-[11px] text-slate-400">Total payable when approved</p>
          </div>

          <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Queue Status</span>
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="text-2xl font-bold text-slate-900">
              {bills.length === 0 ? "All Clear" : "Pending"}
            </p>
            <p className="text-[11px] text-slate-400">
              {bills.length === 0 ? "No bills currently waiting" : "Action required"}
            </p>
          </div>
        </div>

        {/* ── Filter / Search Bar ─────────────────────────── */}
        <div className="flex items-center justify-between gap-4 bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm">
          <div className="relative flex-1 max-w-sm">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search supplier, invoice number..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
            />
          </div>
          <span className="text-xs text-slate-500 font-medium">
            Showing {filteredBills.length} of {bills.length} bills
          </span>
        </div>

        {/* ── Table of Bills Awaiting Approval ─────────────── */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-16 text-center space-y-2">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-[#0073B7] border-t-transparent mx-auto" />
              <p className="text-xs text-slate-500">Loading queue...</p>
            </div>
          ) : filteredBills.length === 0 ? (
            <div className="py-16 text-center space-y-3">
              <FileCheck className="h-10 w-10 text-emerald-500 mx-auto" />
              <div className="space-y-1">
                <p className="text-sm font-bold text-slate-800">Approval queue is clear</p>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  There are no supplier bills currently awaiting approval. Any newly submitted bills will appear here.
                </p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Supplier</th>
                    <th className="py-3 px-4">Supplier Inv #</th>
                    <th className="py-3 px-4">Internal Bill #</th>
                    <th className="py-3 px-4">Bill Date</th>
                    <th className="py-3 px-4">Due Date</th>
                    <th className="py-3 px-4 text-right">Total</th>
                    <th className="py-3 px-4">Time Waiting</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredBills.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {b.supplier_name_snapshot || "Supplier"}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-slate-800">
                        {b.supplier_invoice_number}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-500">
                        {b.internal_bill_number || "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-600">{fmtDate(b.bill_date)}</td>
                      <td className="py-3 px-4 text-slate-600 font-medium">{fmtDate(b.due_date)}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        {fmt(b.total, b.currency)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1 text-[11px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded-full font-medium">
                          <Clock className="h-3 w-3" />
                          {timeWaiting(b.submitted_for_approval_at || b.created_at)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <Link
                            href={`/app/purchases/bills/${b.id}`}
                            className="px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded border border-slate-200 transition-colors"
                          >
                            Review
                          </Link>
                          <button
                            onClick={() => {
                              setSelectedBill(b);
                              setModalType("reject");
                              setCommentOrReason("");
                            }}
                            className="px-2.5 py-1 text-xs font-semibold text-red-600 hover:bg-red-50 rounded border border-red-200 transition-colors"
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => {
                              setSelectedBill(b);
                              setModalType("approve");
                              setCommentOrReason("");
                            }}
                            className="px-3 py-1 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded shadow-xs transition-colors"
                          >
                            Approve
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── ACTION MODAL (APPROVE / REJECT) ──────────────────── */}
      {modalType && selectedBill && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">
                {modalType === "approve" ? "Approve Supplier Bill" : "Reject Supplier Bill"}
              </h3>
              <button
                onClick={() => setModalType(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Bill Summary Recap */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Supplier:</span>
                <span className="font-semibold text-slate-900">
                  {selectedBill.supplier_name_snapshot || "Supplier"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Invoice #:</span>
                <span className="font-mono text-slate-800">{selectedBill.supplier_invoice_number}</span>
              </div>
              <div className="flex justify-between font-bold text-slate-900 border-t border-slate-200 pt-1">
                <span>Total:</span>
                <span>{fmt(selectedBill.total, selectedBill.currency)}</span>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                {modalType === "approve" ? (
                  "Approval Comment (Optional)"
                ) : (
                  <>
                    Rejection Reason <span className="text-red-500">*</span>
                  </>
                )}
              </label>
              <textarea
                rows={3}
                value={commentOrReason}
                onChange={(e) => setCommentOrReason(e.target.value)}
                placeholder={
                  modalType === "approve"
                    ? "e.g. Verified against PO and budget."
                    : "e.g. Line item rate exceeds agreed contract rate."
                }
                className={`w-full text-xs rounded-md border p-2 focus:outline-none focus:ring-1 ${
                  modalType === "approve"
                    ? "border-slate-300 focus:ring-emerald-500"
                    : "border-slate-300 focus:ring-red-500"
                }`}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalType(null)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAction}
                disabled={actionInProgress}
                className={`px-4 py-1.5 text-xs font-semibold text-white rounded-md transition-all ${
                  modalType === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {actionInProgress
                  ? "Processing..."
                  : modalType === "approve"
                  ? "Confirm Approval"
                  : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
