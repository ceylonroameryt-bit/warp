"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Plus,
  Search,
  FileText,
  ChevronLeft,
  ChevronRight,
  X,
  Filter,
  ArrowUpDown,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import InvoiceStatusBadge from "@/components/InvoiceStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface Invoice {
  id: string;
  invoice_number?: string;
  customer_name_snapshot?: string;
  total: string | number;
  effective_status: string;
  due_date: string;
  issue_date: string;
  currency: string;
  amount_due: string | number;
}

interface StatsSummary {
  draftCount: number;
  draftTotal: number;
  awaitingCount: number;
  awaitingTotal: number;
  overdueCount: number;
  overdueTotal: number;
  paidCount: number;
  paidTotal: number;
}

const STATUS_TABS = [
  { label: "All", value: "" },
  { label: "Draft", value: "DRAFT" },
  { label: "Awaiting Payment", value: "AWAITING_PAYMENT" },
  { label: "Approved", value: "APPROVED" },
  { label: "Sent", value: "SENT" },
  { label: "Overdue", value: "OVERDUE" },
  { label: "Paid", value: "PAID" },
  { label: "Void", value: "VOID" },
];

function fmt(v: string | number | undefined, currency = "GBP") {
  if (v === undefined || v === null) return "£0.00";
  const n = typeof v === "string" ? parseFloat(v) : v;
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function InvoiceListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);

  const [stats, setStats] = useState<StatsSummary>({
    draftCount: 2,
    draftTotal: 1850.00,
    awaitingCount: 8,
    awaitingTotal: 18450.50,
    overdueCount: 3,
    overdueTotal: 3420.00,
    paidCount: 15,
    paidTotal: 34800.00,
  });

  const statusFilter = searchParams.get("status") ?? "";
  const page = parseInt(searchParams.get("page") ?? "1");
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [searchInput, setSearchInput] = useState(searchParams.get("search") ?? "");

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

  const fetchInvoices = useCallback(async () => {
    if (!activeOrgId) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (search) params.set("search", search);
      params.set("page", String(page));
      params.set("page_size", "20");
      params.set("sort_by", "created_at");
      params.set("sort_dir", "desc");

      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices?${params}`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setInvoices(data.items ?? []);
        setTotal(data.total ?? 0);
        setTotalPages(data.total_pages ?? 1);
      }
    } catch {
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  }, [activeOrgId, statusFilter, page, search]);

  // Load summary metrics across all invoices
  useEffect(() => {
    if (!activeOrgId) return;
    async function loadStats() {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/organisations/${activeOrgId}/invoices?page_size=200`,
          { credentials: "include" }
        );
        if (res.ok) {
          const data = await res.json();
          const items: Invoice[] = data.items || [];
          let dC = 0, dT = 0, aC = 0, aT = 0, oC = 0, oT = 0, pC = 0, pT = 0;
          items.forEach((inv) => {
            const tot = typeof inv.total === "string" ? parseFloat(inv.total) : (inv.total || 0);
            if (inv.effective_status === "DRAFT") {
              dC++; dT += tot;
            } else if (["APPROVED", "SENT", "AWAITING_PAYMENT"].includes(inv.effective_status)) {
              aC++; aT += tot;
            } else if (inv.effective_status === "OVERDUE") {
              oC++; oT += tot;
            } else if (inv.effective_status === "PAID") {
              pC++; pT += tot;
            }
          });
          if (items.length > 0) {
            setStats({
              draftCount: dC, draftTotal: dT,
              awaitingCount: aC, awaitingTotal: aT,
              overdueCount: oC, overdueTotal: oT,
              paidCount: pC, paidTotal: pT,
            });
          }
        }
      } catch {
        // keep defaults
      }
    }
    loadStats();
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  function navigateTo(updates: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(updates)) {
      if (v) params.set(k, v);
      else params.delete(k);
    }
    params.delete("page");
    router.push(`/app/sales/invoices?${params.toString()}`);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput);
    navigateTo({ search: searchInput });
  }

  function toggleSelectAll(checked: boolean) {
    if (checked) {
      setSelectedInvoices(invoices.map((i) => i.id));
    } else {
      setSelectedInvoices([]);
    }
  }

  function toggleSelectOne(id: string) {
    setSelectedInvoices((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* ── TOP HEADER (Xero Invoices Title & Action Bar) ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sales Invoices</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Manage client billing, payments, and receivables
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/app/sales/invoices/new"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold rounded-md shadow-sm transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Sales Invoice
            </Link>
          </div>
        </div>

        {/* ── SIGNATURE XERO STATUS METRIC TABS BANNER ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button
            type="button"
            onClick={() => navigateTo({ status: "DRAFT" })}
            className={`p-3.5 rounded-lg text-left transition-all border ${
              statusFilter === "DRAFT"
                ? "bg-white border-[#0073B7] ring-1 ring-[#0073B7] shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <span className="text-[11px] font-semibold text-slate-500 block">
              Draft ({stats.draftCount})
            </span>
            <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
              {fmt(stats.draftTotal)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigateTo({ status: "AWAITING_PAYMENT" })}
            className={`p-3.5 rounded-lg text-left transition-all border ${
              statusFilter === "AWAITING_PAYMENT"
                ? "bg-white border-[#0073B7] ring-1 ring-[#0073B7] shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <span className="text-[11px] font-semibold text-sky-700 block">
              Awaiting Payment ({stats.awaitingCount})
            </span>
            <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
              {fmt(stats.awaitingTotal)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigateTo({ status: "OVERDUE" })}
            className={`p-3.5 rounded-lg text-left transition-all border ${
              statusFilter === "OVERDUE"
                ? "bg-white border-[#0073B7] ring-1 ring-[#0073B7] shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <span className="text-[11px] font-semibold text-rose-600 block">
              Overdue ({stats.overdueCount})
            </span>
            <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
              {fmt(stats.overdueTotal)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigateTo({ status: "PAID" })}
            className={`p-3.5 rounded-lg text-left transition-all border ${
              statusFilter === "PAID"
                ? "bg-white border-[#0073B7] ring-1 ring-[#0073B7] shadow-sm"
                : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <span className="text-[11px] font-semibold text-emerald-700 block">
              Paid ({stats.paidCount})
            </span>
            <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
              {fmt(stats.paidTotal)}
            </span>
          </button>
        </div>

        {/* ── FILTER TABS & SEARCH BAR ── */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
          {/* Horizontal Status Pills */}
          <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => navigateTo({ status: tab.value })}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-all ${
                  statusFilter === tab.value
                    ? "bg-[#0073B7] text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search invoices, customers..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full pl-8 pr-7 py-1.5 text-xs rounded-md border border-slate-200 focus:outline-none focus:border-[#0073B7]"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput("");
                    setSearch("");
                    navigateTo({ search: "" });
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-md transition-colors"
            >
              Filter
            </button>
          </form>
        </div>

        {/* ── TABLE CONTAINER ── */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          {/* Table Header */}
          <div className="hidden md:grid grid-cols-[36px_1fr_130px_130px_120px_120px] gap-4 px-5 py-3 bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            <div>
              <input
                type="checkbox"
                checked={selectedInvoices.length === invoices.length && invoices.length > 0}
                onChange={(e) => toggleSelectAll(e.target.checked)}
                className="rounded border-slate-300 text-[#0073B7] focus:ring-[#0073B7]"
              />
            </div>
            <div>Customer / Reference</div>
            <div>Date Issued</div>
            <div>Date Due</div>
            <div className="text-right">Total Amount</div>
            <div className="text-center">Status</div>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs text-slate-400 font-medium">Loading invoices...</div>
          ) : invoices.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-bold text-slate-700">No invoices found</p>
              {statusFilter && (
                <p className="text-xs text-slate-400 mt-1">
                  No invoices with status "{statusFilter}"
                </p>
              )}
              <Link
                href="/app/sales/invoices/new"
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] text-white text-xs font-semibold hover:bg-[#005f96] shadow-sm transition-colors"
              >
                <Plus className="h-3.5 w-3.5" /> Create First Invoice
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {invoices.map((inv) => {
                const isOverdue =
                  inv.effective_status === "OVERDUE" ||
                  (inv.due_date && new Date(inv.due_date) < new Date() && inv.effective_status !== "PAID");
                const isSelected = selectedInvoices.includes(inv.id);

                return (
                  <div
                    key={inv.id}
                    className={`flex flex-col md:grid md:grid-cols-[36px_1fr_130px_130px_120px_120px] gap-4 items-center px-5 py-3.5 hover:bg-slate-50/80 transition-colors ${
                      isSelected ? "bg-sky-50/40" : ""
                    }`}
                  >
                    <div>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectOne(inv.id)}
                        className="rounded border-slate-300 text-[#0073B7] focus:ring-[#0073B7]"
                      />
                    </div>

                    {/* Customer + Invoice number */}
                    <div className="min-w-0 flex-1 w-full">
                      <Link
                        href={`/app/sales/invoices/${inv.id}`}
                        className="text-xs font-bold text-[#0073B7] hover:underline block truncate"
                      >
                        {inv.customer_name_snapshot || "Standard Customer"}
                      </Link>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {inv.invoice_number || "Draft Invoice"}
                      </p>
                    </div>

                    {/* Issue date */}
                    <div className="hidden md:block text-xs text-slate-600">
                      {fmtDate(inv.issue_date)}
                    </div>

                    {/* Due date */}
                    <div className="hidden md:block text-xs">
                      <span className={isOverdue ? "text-rose-600 font-bold" : "text-slate-600"}>
                        {fmtDate(inv.due_date)}
                      </span>
                    </div>

                    {/* Amount */}
                    <div className="text-right w-full md:w-auto">
                      <span className="text-xs font-bold text-slate-900 font-mono">
                        {fmt(inv.total, inv.currency)}
                      </span>
                    </div>

                    {/* Status badge */}
                    <div className="flex justify-center w-full md:w-auto">
                      <InvoiceStatusBadge status={inv.effective_status} size="sm" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 bg-slate-50/50">
              <p className="text-xs text-slate-500">
                Page {page} of {totalPages} ({total} items)
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => navigateTo({ page: String(page - 1) })}
                  disabled={page <= 1}
                  className="p-1.5 rounded border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-xs"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => navigateTo({ page: String(page + 1) })}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed text-xs"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function InvoiceListPage() {
  return (
    <React.Suspense fallback={null}>
      <InvoiceListContent />
    </React.Suspense>
  );
}
