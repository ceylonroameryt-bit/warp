"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileClock,
  CreditCard,
  AlertTriangle,
  Calendar,
  Plus,
  ArrowRight,
  Receipt,
  CheckCircle2,
  FileText,
  Clock,
  Search,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import BillStatusBadge from "@/components/BillStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface Metrics {
  awaiting_approval_count: number;
  awaiting_approval_amount: string | number;
  awaiting_payment_count: number;
  awaiting_payment_amount: string | number;
  overdue_count: number;
  overdue_amount: string | number;
  this_month_count: number;
  this_month_amount: string | number;
}

interface BillItem {
  id: string;
  internal_bill_number?: string;
  supplier_invoice_number: string;
  supplier_name_snapshot?: string;
  bill_date: string;
  due_date: string;
  total: string | number;
  currency: string;
  status: string;
  effective_status: string;
}

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

export default function PurchasesDashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [recentBills, setRecentBills] = useState<BillItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  useEffect(() => {
    async function init() {
      let orgId = ORG_ID;
      try {
        const res = await fetch("/api/v1/organisations/", { credentials: "include" });
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) {
            orgId = orgs[0].id;
            setActiveOrgId(orgId);
          }
        }
      } catch {
        // Fallback to default ORG_ID
      }

      if (!orgId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      Promise.all([
        fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/metrics`, { credentials: "include" })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
        fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills?page=1&page_size=8`, {
          credentials: "include",
        })
          .then((r) => (r.ok ? r.json() : { items: [] }))
          .catch(() => ({ items: [] })),
      ]).then(([metricData, billsData]) => {
        setMetrics(metricData);
        setRecentBills(billsData.items || []);
        setLoading(false);
      });
    }

    init();
  }, []);

  return (
    <DashboardLayout>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-6">
        {/* ── Page Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-sky-600 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                Purchases & Payables
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1 tracking-tight">
              Purchases Overview
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Track money out, review pending supplier invoices, and control payables approval.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/app/purchases/approvals"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs transition-colors"
            >
              <FileClock className="h-4 w-4 text-amber-500" />
              Approval Queue
              {metrics && metrics.awaiting_approval_count > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-800 font-bold">
                  {metrics.awaiting_approval_count}
                </span>
              )}
            </Link>

            <Link
              href="/app/purchases/bills/new"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-sky-600 rounded-lg hover:bg-sky-500 shadow-sm transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Bill
            </Link>
          </div>
        </div>

        {/* ── Sub-navigation Tabs ── */}
        <div className="flex items-center gap-6 mt-4 border-b border-slate-200 text-xs font-medium">
          <Link
            href="/app/purchases"
            className="pb-3 border-b-2 border-sky-600 text-sky-600 font-semibold"
          >
            Overview
          </Link>
          <Link
            href="/app/purchases/bills"
            className="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300 transition-colors"
          >
            Bills
          </Link>
          <Link
            href="/app/purchases/approvals"
            className="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300 transition-colors flex items-center gap-1.5"
          >
            Approvals
            {metrics && metrics.awaiting_approval_count > 0 && (
              <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.2 rounded-full">
                {metrics.awaiting_approval_count}
              </span>
            )}
          </Link>
          <Link
            href="/app/contacts?type=SUPPLIER"
            className="pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300 transition-colors"
          >
            Suppliers
          </Link>
        </div>

        {/* ── 4 KPI Metric Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {/* Card 1: Awaiting Approval */}
          <Link
            href="/app/purchases/approvals"
            className="p-5 rounded-xl bg-white border border-slate-200 hover:border-amber-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Awaiting Approval</span>
              <div className="h-8 w-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center group-hover:bg-amber-100 transition-colors">
                <FileClock className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                {loading ? "..." : fmt(metrics?.awaiting_approval_amount)}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span className="font-semibold text-slate-700">
                {metrics?.awaiting_approval_count || 0}
              </span>{" "}
              bills awaiting review
            </div>
          </Link>

          {/* Card 2: Awaiting Payment */}
          <Link
            href="/app/purchases/bills?status=AWAITING_PAYMENT"
            className="p-5 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Awaiting Payment</span>
              <div className="h-8 w-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                <CreditCard className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                {loading ? "..." : fmt(metrics?.awaiting_payment_amount)}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span className="font-semibold text-slate-700">
                {metrics?.awaiting_payment_count || 0}
              </span>{" "}
              approved bills due
            </div>
          </Link>

          {/* Card 3: Overdue */}
          <Link
            href="/app/purchases/bills?status=OVERDUE"
            className="p-5 rounded-xl bg-white border border-slate-200 hover:border-rose-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Overdue Payables</span>
              <div className="h-8 w-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center group-hover:bg-rose-100 transition-colors">
                <AlertTriangle className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-black text-rose-600 tracking-tight">
                {loading ? "..." : fmt(metrics?.overdue_amount)}
              </span>
            </div>
            <div className="mt-1 text-xs text-rose-500 flex items-center gap-1">
              <span className="font-semibold">{metrics?.overdue_count || 0}</span> bills past due
              date
            </div>
          </Link>

          {/* Card 4: Bills This Month */}
          <Link
            href="/app/purchases/bills"
            className="p-5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Purchase Bills This Month</span>
              <div className="h-8 w-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center group-hover:bg-slate-200 transition-colors">
                <Calendar className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-black text-slate-900 tracking-tight">
                {loading ? "..." : fmt(metrics?.this_month_amount)}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <span className="font-semibold text-slate-700">{metrics?.this_month_count || 0}</span>{" "}
              bills recorded this month
            </div>
          </Link>
        </div>

        {/* ── Recent Bills Table ── */}
        <div className="mt-8 bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Recent Supplier Bills</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Latest purchase payables recorded across your business
              </p>
            </div>
            <Link
              href="/app/purchases/bills"
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              View all bills
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/70 text-slate-500 border-b border-slate-100 font-semibold">
                <tr>
                  <th className="px-6 py-3">Bill #</th>
                  <th className="px-6 py-3">Supplier</th>
                  <th className="px-6 py-3">Supplier Invoice #</th>
                  <th className="px-6 py-3">Bill Date</th>
                  <th className="px-6 py-3">Due Date</th>
                  <th className="px-6 py-3 text-right">Total</th>
                  <th className="px-6 py-3 text-center">Status</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-10 text-center text-slate-400">
                      Loading bills...
                    </td>
                  </tr>
                ) : recentBills.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <div className="h-12 w-12 rounded-full bg-sky-50 text-sky-600 flex items-center justify-center mb-3">
                          <Receipt className="h-6 w-6" />
                        </div>
                        <h3 className="text-sm font-bold text-slate-800">No bills recorded yet</h3>
                        <p className="text-xs text-slate-400 max-w-sm mt-1">
                          Record supplier invoices, track due dates, and control payment approvals.
                        </p>
                        <Link
                          href="/app/purchases/bills/new"
                          className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm transition-colors"
                        >
                          Create First Bill
                        </Link>
                      </div>
                    </td>
                  </tr>
                ) : (
                  recentBills.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/80 transition-colors group">
                      <td className="px-6 py-3.5 font-bold text-slate-900">
                        <Link
                          href={`/app/purchases/bills/${b.id}`}
                          className="hover:text-sky-600 transition-colors"
                        >
                          {b.internal_bill_number || "—"}
                        </Link>
                      </td>
                      <td className="px-6 py-3.5 font-medium text-slate-800">
                        {b.supplier_name_snapshot || "Unknown Supplier"}
                      </td>
                      <td className="px-6 py-3.5 text-slate-600 font-mono text-[11px]">
                        {b.supplier_invoice_number}
                      </td>
                      <td className="px-6 py-3.5 text-slate-500">{fmtDate(b.bill_date)}</td>
                      <td className="px-6 py-3.5 text-slate-500">{fmtDate(b.due_date)}</td>
                      <td className="px-6 py-3.5 text-right font-bold text-slate-900">
                        {fmt(b.total, b.currency)}
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        <BillStatusBadge status={b.effective_status || b.status} />
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <Link
                          href={`/app/purchases/bills/${b.id}`}
                          className="text-xs font-semibold text-sky-600 hover:text-sky-700"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
