"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Lock,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  FileText,
  RotateCcw,
  Eye,
  Calendar,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface JournalLine {
  id: string;
  account_id: string;
  account?: {
    code: string;
    name: string;
    account_class: string;
  };
  description?: string;
  debit: string | number;
  credit: string | number;
}

interface JournalEntry {
  id: string;
  entry_number: string;
  entry_date: string;
  narration: string;
  reference?: string;
  source_type: "MANUAL" | "SYSTEM_INVOICE" | "SYSTEM_BILL" | "SYSTEM_PAYMENT" | "CLOSING_ENTRY";
  status: "DRAFT" | "POSTED" | "REVERSED";
  total_debit: string | number;
  total_credit: string | number;
  created_at: string;
  posted_at?: string;
  reversal_of_journal_id?: string;
  reversed_by_journal_id?: string;
  lines?: JournalLine[];
}

const STATUS_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  DRAFT: { bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-300" },
  POSTED: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  REVERSED: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
};

const SOURCE_BADGES: Record<string, string> = {
  MANUAL: "bg-sky-50 text-sky-700 border-sky-200",
  SYSTEM_INVOICE: "bg-indigo-50 text-indigo-700 border-indigo-200",
  SYSTEM_BILL: "bg-purple-50 text-purple-700 border-purple-200",
  SYSTEM_PAYMENT: "bg-emerald-50 text-emerald-700 border-emerald-200",
  CLOSING_ENTRY: "bg-amber-50 text-amber-700 border-amber-200",
};

const DEMO_JOURNALS: JournalEntry[] = [
  {
    id: "j-001",
    entry_number: "JRN-000001",
    entry_date: "2026-03-01",
    narration: "Monthly office depreciation allocation (fixtures and fittings)",
    reference: "DEP-2026-03",
    source_type: "MANUAL",
    status: "POSTED",
    total_debit: 450.0,
    total_credit: 450.0,
    created_at: "2026-03-01T10:00:00Z",
    posted_at: "2026-03-01T10:05:00Z",
    lines: [
      { id: "l1", account_id: "a1", account: { code: "6050", name: "Depreciation Expense", account_class: "EXPENSE" }, debit: 450.0, credit: 0 },
      { id: "l2", account_id: "a2", account: { code: "1550", name: "Accumulated Depreciation", account_class: "ASSET" }, debit: 0, credit: 450.0 },
    ],
  },
  {
    id: "j-002",
    entry_number: "JRN-000002",
    entry_date: "2026-03-05",
    narration: "Prepaid insurance adjustment for Q1 2026",
    reference: "INS-ADJ",
    source_type: "MANUAL",
    status: "POSTED",
    total_debit: 1200.0,
    total_credit: 1200.0,
    created_at: "2026-03-05T09:15:00Z",
    posted_at: "2026-03-05T09:20:00Z",
    lines: [
      { id: "l3", account_id: "a3", account: { code: "6030", name: "Insurance Expense", account_class: "EXPENSE" }, debit: 1200.0, credit: 0 },
      { id: "l4", account_id: "a4", account: { code: "1200", name: "Prepayments & Accruals", account_class: "ASSET" }, debit: 0, credit: 1200.0 },
    ],
  },
  {
    id: "j-003",
    entry_number: "JRN-000003",
    entry_date: "2026-03-10",
    narration: "Quarterly VAT reconciliation provision",
    reference: "VAT-Q1-PROV",
    source_type: "MANUAL",
    status: "DRAFT",
    total_debit: 3500.0,
    total_credit: 3500.0,
    created_at: "2026-03-10T14:30:00Z",
    lines: [
      { id: "l5", account_id: "a5", account: { code: "2200", name: "VAT Output Tax", account_class: "LIABILITY" }, debit: 3500.0, credit: 0 },
      { id: "l6", account_id: "a6", account: { code: "2210", name: "HMRC VAT Control Account", account_class: "LIABILITY" }, debit: 0, credit: 3500.0 },
    ],
  },
];

function fmtCur(amount: number | string | undefined) {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(num);
}

function JournalsContent() {
  const [journals, setJournals] = useState<JournalEntry[]>(DEMO_JOURNALS);
  const [loading, setLoading] = useState(false);
  const [activeStatus, setActiveStatus] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Reversal Modal State
  const [reversalModalOpen, setReversalModalOpen] = useState(false);
  const [targetJournal, setTargetJournal] = useState<JournalEntry | null>(null);
  const [reversalDate, setReversalDate] = useState(new Date().toISOString().split("T")[0]);
  const [reversalReason, setReversalReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");

  const fetchJournals = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      let url = `${API_BASE}/api/v1/organisations/${ORG_ID}/journals?limit=100`;
      if (activeStatus !== "ALL") url += `&status=${activeStatus}`;

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          setJournals(data.items);
        }
      }
    } catch (err) {
      console.warn("Using demo journals", err);
    } finally {
      setLoading(false);
    }
  }, [activeStatus]);

  useEffect(() => {
    fetchJournals();
  }, [fetchJournals]);

  const handlePost = async (journalId: string) => {
    setActionLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/journals/${journalId}/post`, {
        method: "POST",
        headers,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to post journal");
      }

      await fetchJournals();
    } catch (err: any) {
      alert(err.message || "Failed to post journal");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReverse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetJournal) return;
    setActionLoading(true);
    setActionError("");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/journals/${targetJournal.id}/reverse`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          reversal_date: reversalDate,
          reversal_reason: reversalReason,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to reverse journal");
      }

      setReversalModalOpen(false);
      setTargetJournal(null);
      setReversalReason("");
      await fetchJournals();
    } catch (err: any) {
      setActionError(err.message || "Failed to reverse journal");
    } finally {
      setActionLoading(false);
    }
  };

  const filtered = journals.filter((j) => {
    if (activeStatus !== "ALL" && j.status !== activeStatus) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      j.entry_number.toLowerCase().includes(q) ||
      j.narration.toLowerCase().includes(q) ||
      (j.reference && j.reference.toLowerCase().includes(q))
    );
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-sky-100 text-[#0073B7]">
                <Layers className="h-5 w-5" />
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Manual Journals</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Double-entry adjusting journals, accruals, prepayments, depreciation, and year-end reclassifications.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/app/accounting/journals/new"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="h-4 w-4" />
              New Manual Journal
            </Link>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center gap-1 text-xs">
            {(["ALL", "POSTED", "DRAFT", "REVERSED"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveStatus(tab)}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  activeStatus === tab
                    ? "bg-[#0073B7] text-white font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {tab === "ALL" ? "All Entries" : tab.charAt(0) + tab.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search JRN#, narration..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-md bg-slate-50 border border-slate-200 text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-[#0073B7] transition-all"
            />
          </div>
        </div>

        {/* Journals Table */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
              <tr>
                <th className="py-3 px-4 w-12"></th>
                <th className="py-3 px-4 w-28">Number</th>
                <th className="py-3 px-4 w-28">Date</th>
                <th className="py-3 px-4">Narration & Reference</th>
                <th className="py-3 px-4 w-32">Source</th>
                <th className="py-3 px-4 text-right w-28">Debit Total</th>
                <th className="py-3 px-4 text-right w-28">Credit Total</th>
                <th className="py-3 px-4 text-center w-24">Status</th>
                <th className="py-3 px-4 text-right w-36">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    No journal entries found matching criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((j) => {
                  const isExpanded = expandedId === j.id;
                  const statusStyle = STATUS_BADGES[j.status] || STATUS_BADGES.DRAFT;
                  const sourceStyle = SOURCE_BADGES[j.source_type] || "bg-slate-50 text-slate-700 border-slate-200";

                  return (
                    <React.Fragment key={j.id}>
                      <tr className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : j.id)}
                            className="p-1 text-slate-400 hover:text-slate-600 rounded"
                            title={isExpanded ? "Collapse lines" : "View lines"}
                          >
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">{j.entry_number}</td>
                        <td className="py-3 px-4 text-slate-600 font-mono">{j.entry_date}</td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-slate-900">{j.narration}</div>
                          {j.reference && (
                            <div className="text-[11px] text-slate-400 font-mono">Ref: {j.reference}</div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${sourceStyle}`}>
                            {j.source_type.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">{fmtCur(j.total_debit)}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">{fmtCur(j.total_credit)}</td>
                        <td className="py-3 px-4 text-center">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
                            {j.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {j.status === "DRAFT" && (
                              <button
                                onClick={() => handlePost(j.id)}
                                disabled={actionLoading}
                                className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] shadow-2xs transition-colors"
                              >
                                Post
                              </button>
                            )}
                            {j.status === "POSTED" && (
                              <button
                                onClick={() => {
                                  setTargetJournal(j);
                                  setReversalModalOpen(true);
                                }}
                                disabled={actionLoading}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-[11px] transition-colors"
                              >
                                <RotateCcw className="h-3 w-3" /> Reverse
                              </button>
                            )}
                            {j.status === "REVERSED" && (
                              <span className="text-slate-400 text-[11px]">Reversed</span>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Journal Lines Sub-table */}
                      {isExpanded && (
                        <tr className="bg-slate-50/80 border-b border-slate-200">
                          <td colSpan={9} className="p-4">
                            <div className="bg-white rounded border border-slate-200 overflow-hidden shadow-2xs">
                              <div className="bg-slate-100 px-3 py-1.5 text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between">
                                <span>Double-Entry Journal Lines</span>
                                <span className="text-emerald-700 font-mono text-[10px] flex items-center gap-1">
                                  <CheckCircle2 className="h-3 w-3" /> Balanced: Dr {fmtCur(j.total_debit)} = Cr {fmtCur(j.total_credit)}
                                </span>
                              </div>
                              <table className="w-full text-xs text-left">
                                <thead className="border-b border-slate-200 bg-slate-50/50 text-[10px] uppercase text-slate-400 font-semibold">
                                  <tr>
                                    <th className="py-2 px-3">Account Code & Name</th>
                                    <th className="py-2 px-3">Class</th>
                                    <th className="py-2 px-3">Line Memo</th>
                                    <th className="py-2 px-3 text-right">Debit (Dr)</th>
                                    <th className="py-2 px-3 text-right">Credit (Cr)</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {j.lines && j.lines.length > 0 ? (
                                    j.lines.map((l, idx) => (
                                      <tr key={idx} className="hover:bg-slate-50/50">
                                        <td className="py-2 px-3">
                                          <span className="font-mono font-bold text-slate-900 mr-2">
                                            {l.account?.code || "—"}
                                          </span>
                                          <span className="text-slate-700">{l.account?.name || "General Ledger"}</span>
                                        </td>
                                        <td className="py-2 px-3">
                                          <span className="text-[10px] font-mono text-slate-500">
                                            {l.account?.account_class || "—"}
                                          </span>
                                        </td>
                                        <td className="py-2 px-3 text-slate-500">{l.description || "—"}</td>
                                        <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                                          {Number(l.debit) > 0 ? fmtCur(l.debit) : "—"}
                                        </td>
                                        <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                                          {Number(l.credit) > 0 ? fmtCur(l.credit) : "—"}
                                        </td>
                                      </tr>
                                    ))
                                  ) : (
                                    <tr>
                                      <td colSpan={5} className="py-4 text-center text-slate-400 text-xs">
                                        Lines data not available
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Atomic Reversal Modal */}
        {reversalModalOpen && targetJournal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-rose-700">
                  <RotateCcw className="h-4 w-4" />
                  <h3 className="font-bold text-slate-900 text-sm">Reverse Journal {targetJournal.entry_number}</h3>
                </div>
                <button onClick={() => setReversalModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
              </div>

              <form onSubmit={handleReverse} className="p-6 space-y-4 text-xs">
                <p className="text-slate-600">
                  This will generate an atomic reversing counter-entry that swaps all debits and credits, permanently linking to this journal and preserving ledger immutability.
                </p>

                {actionError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-md flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{actionError}</span>
                  </div>
                )}

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Reversal Effective Date</label>
                  <input
                    type="date"
                    required
                    value={reversalDate}
                    onChange={(e) => setReversalDate(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-rose-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Audit Reason for Reversal</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Inadvertent duplicate depreciation run"
                    value={reversalReason}
                    onChange={(e) => setReversalReason(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-rose-500 focus:outline-none"
                  />
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setReversalModalOpen(false)}
                    className="px-3 py-1.5 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    {actionLoading ? "Reversing..." : "Execute Reversal"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function JournalsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Journals...</div>}>
      <JournalsContent />
    </Suspense>
  );
}
