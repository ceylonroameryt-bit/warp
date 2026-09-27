"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Clock,
  AlertTriangle,
  TrendingUp,
  Plus,
  ArrowRight,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import InvoiceStatusBadge from "@/components/InvoiceStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface DashStats {
  draft_count: number;
  awaiting_count: number;
  overdue_count: number;
  invoiced_this_month: number;
  currency: string;
}

interface Invoice {
  id: string;
  invoice_number?: string;
  customer_name_snapshot?: string;
  total: number;
  effective_status: string;
  due_date: string;
  issue_date: string;
  currency: string;
}

function fmt(v: number, currency = "GBP") {
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2 })}`;
}

export default function SalesDashboardPage() {
  const [stats, setStats] = useState<DashStats | null>(null);
  const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);
  const [overdueInvoices, setOverdueInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [allRes, overdueRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/invoices?page_size=5&sort_by=created_at&sort_dir=desc`, {
            credentials: "include",
          }),
          fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/invoices?status=OVERDUE&page_size=5`, {
            credentials: "include",
          }),
        ]);

        let allData: any = { items: [], total: 0 };
        let overdueData: any = { items: [], total: 0 };

        if (allRes.ok) allData = await allRes.json();
        if (overdueRes.ok) overdueData = await overdueRes.json();

        setRecentInvoices(allData.items ?? []);
        setOverdueInvoices(overdueData.items ?? []);

        // Compute stats from available data
        const drafts = (allData.items ?? []).filter((i: Invoice) => i.effective_status === "DRAFT");
        const awaiting = (allData.items ?? []).filter((i: Invoice) =>
          ["APPROVED", "SENT", "AWAITING_PAYMENT"].includes(i.effective_status)
        );

        setStats({
          draft_count: drafts.length,
          awaiting_count: awaiting.length,
          overdue_count: overdueData.total ?? 0,
          invoiced_this_month: 0,
          currency: "GBP",
        });
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    if (ORG_ID) load();
    else setLoading(false);
  }, []);

  const statCards = [
    {
      title: "Draft Invoices",
      value: stats?.draft_count ?? 0,
      type: "count",
      icon: Clock,
      color: "text-slate-600",
      bg: "bg-slate-50",
      border: "border-slate-200",
      link: "/app/sales/invoices?status=DRAFT",
    },
    {
      title: "Awaiting Payment",
      value: stats?.awaiting_count ?? 0,
      type: "count",
      icon: FileText,
      color: "text-blue-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
      link: "/app/sales/invoices?status=AWAITING_PAYMENT",
    },
    {
      title: "Overdue",
      value: stats?.overdue_count ?? 0,
      type: "count",
      icon: AlertTriangle,
      color: "text-amber-600",
      bg: "bg-amber-50",
      border: "border-amber-200",
      link: "/app/sales/invoices?status=OVERDUE",
    },
    {
      title: "Total Invoiced This Month",
      value: stats?.invoiced_this_month ?? 0,
      type: "money",
      currency: stats?.currency ?? "GBP",
      icon: TrendingUp,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      link: "/app/sales/invoices",
    },
  ];

  return (
    <DashboardLayout>
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Sales</h1>
            <p className="text-sm text-slate-500 mt-1">
              Invoices and money coming into your business
            </p>
          </div>
          <Link
            href="/app/sales/invoices/new"
            className="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Invoice
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => (
            <Link
              key={card.title}
              href={card.link}
              className={`block p-5 rounded-xl border ${card.border} ${card.bg} hover:shadow-md transition-all group`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1">
                    {card.title}
                  </p>
                  <p className={`text-2xl font-bold ${card.color}`}>
                    {loading
                      ? "—"
                      : card.type === "money"
                      ? fmt(card.value as number, card.currency)
                      : card.value}
                  </p>
                </div>
                <div className={`p-2.5 rounded-lg ${card.bg} border ${card.border}`}>
                  <card.icon className={`h-5 w-5 ${card.color}`} />
                </div>
              </div>
              <div className="mt-3 flex items-center gap-1 text-xs font-medium text-slate-400 group-hover:text-sky-600 transition-colors">
                View all
                <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Recent Invoices */}
          <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800 text-sm">Recent Invoices</h2>
              <Link
                href="/app/sales/invoices"
                className="text-xs text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {loading ? (
              <div className="p-8 text-center text-sm text-slate-400">Loading…</div>
            ) : recentInvoices.length === 0 ? (
              <div className="p-8 text-center">
                <FileText className="h-10 w-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm font-medium text-slate-500">No invoices yet</p>
                <p className="text-xs text-slate-400 mt-1">
                  Create your first invoice to begin tracking money in.
                </p>
                <Link
                  href="/app/sales/invoices/new"
                  className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700"
                >
                  <Plus className="h-3.5 w-3.5" /> Create Invoice
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-slate-50">
                {recentInvoices.map((inv) => (
                  <Link
                    key={inv.id}
                    href={`/app/sales/invoices/${inv.id}`}
                    className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors group"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 group-hover:text-sky-600 transition-colors">
                        {inv.invoice_number || "Draft"}
                      </p>
                      <p className="text-xs text-slate-400 truncate">
                        {inv.customer_name_snapshot || "Unknown customer"}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 ml-4 shrink-0">
                      <InvoiceStatusBadge status={inv.effective_status} size="sm" />
                      <span className="text-sm font-bold text-slate-800 tabular-nums">
                        {fmt(inv.total, inv.currency)}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Overdue */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-amber-200 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-amber-100 bg-amber-50">
              <h2 className="font-semibold text-amber-800 text-sm flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                Overdue
              </h2>
              <Link
                href="/app/sales/invoices?status=OVERDUE"
                className="text-xs text-amber-600 hover:text-amber-700 font-medium"
              >
                View all
              </Link>
            </div>
            {loading ? (
              <div className="p-6 text-sm text-slate-400 text-center">Loading…</div>
            ) : overdueInvoices.length === 0 ? (
              <div className="p-6 text-center">
                <p className="text-sm text-slate-500">No overdue invoices. 🎉</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-50">
                {overdueInvoices.map((inv) => (
                  <Link
                    key={inv.id}
                    href={`/app/sales/invoices/${inv.id}`}
                    className="flex items-center justify-between px-5 py-3 hover:bg-amber-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800">
                        {inv.invoice_number}
                      </p>
                      <p className="text-xs text-slate-400 truncate">
                        {inv.customer_name_snapshot}
                      </p>
                    </div>
                    <span className="text-sm font-bold text-amber-700 tabular-nums ml-3 shrink-0">
                      {fmt(inv.total, inv.currency)}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
