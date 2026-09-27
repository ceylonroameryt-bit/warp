"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  ArrowRight,
  CreditCard,
  Building2,
  FileText,
  Receipt,
  UploadCloud,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronRight,
  MoreVertical,
  ExternalLink,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface FinancialSummary {
  salesDraftCount: number;
  salesDraftTotal: number;
  salesAwaitingCount: number;
  salesAwaitingTotal: number;
  salesOverdueCount: number;
  salesOverdueTotal: number;
  
  billsDraftCount: number;
  billsDraftTotal: number;
  billsAwaitingCount: number;
  billsAwaitingTotal: number;
  billsOverdueCount: number;
  billsOverdueTotal: number;

  capturedDocsCount: number;
}

export default function XeroDashboardPage() {
  const [summary, setSummary] = useState<FinancialSummary>({
    salesDraftCount: 2,
    salesDraftTotal: 1850.00,
    salesAwaitingCount: 8,
    salesAwaitingTotal: 18450.50,
    salesOverdueCount: 3,
    salesOverdueTotal: 3420.00,
    
    billsDraftCount: 1,
    billsDraftTotal: 490.00,
    billsAwaitingCount: 6,
    billsAwaitingTotal: 8640.20,
    billsOverdueCount: 2,
    billsOverdueTotal: 1250.00,

    capturedDocsCount: 4,
  });

  const [loading, setLoading] = useState(false);
  const [activeAccountTab, setActiveAccountTab] = useState<"current" | "savings">("current");

  // Load real records from backend if available
  useEffect(() => {
    async function loadStats() {
      try {
        const [invoicesRes, billsRes, docsRes] = await Promise.allSettled([
          fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/invoices?page_size=100`, { credentials: "include" }),
          fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/bills?page_size=100`, { credentials: "include" }),
          fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/documents?page_size=100`, { credentials: "include" }),
        ]);

        let sDraftC = 0, sDraftT = 0, sAwaitingC = 0, sAwaitingT = 0, sOverdueC = 0, sOverdueT = 0;
        let bDraftC = 0, bDraftT = 0, bAwaitingC = 0, bAwaitingT = 0, bOverdueC = 0, bOverdueT = 0;
        let cDocs = 0;

        if (invoicesRes.status === "fulfilled" && invoicesRes.value.ok) {
          const data = await invoicesRes.value.json();
          const items: any[] = data.items || [];
          items.forEach((inv) => {
            const tot = parseFloat(inv.total || 0);
            if (inv.effective_status === "DRAFT") {
              sDraftC++;
              sDraftT += tot;
            } else if (["APPROVED", "SENT", "AWAITING_PAYMENT"].includes(inv.effective_status)) {
              sAwaitingC++;
              sAwaitingT += tot;
            } else if (inv.effective_status === "OVERDUE") {
              sOverdueC++;
              sOverdueT += tot;
            }
          });
        }

        if (billsRes.status === "fulfilled" && billsRes.value.ok) {
          const data = await billsRes.value.json();
          const items: any[] = data.items || [];
          items.forEach((bill) => {
            const tot = parseFloat(bill.total || 0);
            if (bill.effective_status === "DRAFT") {
              bDraftC++;
              bDraftT += tot;
            } else if (["APPROVED", "AWAITING_PAYMENT"].includes(bill.effective_status)) {
              bAwaitingC++;
              bAwaitingT += tot;
            } else if (bill.effective_status === "OVERDUE") {
              bOverdueC++;
              bOverdueT += tot;
            }
          });
        }

        if (docsRes.status === "fulfilled" && docsRes.value.ok) {
          const data = await docsRes.value.json();
          const items: any[] = data.items || [];
          cDocs = items.filter((d: any) => ["UPLOADED", "PROCESSING", "NEEDS_REVIEW", "READY_FOR_BILL"].includes(d.status)).length;
        }

        setSummary((prev) => ({
          salesDraftCount: sDraftC || prev.salesDraftCount,
          salesDraftTotal: sDraftT || prev.salesDraftTotal,
          salesAwaitingCount: sAwaitingC || prev.salesAwaitingCount,
          salesAwaitingTotal: sAwaitingT || prev.salesAwaitingTotal,
          salesOverdueCount: sOverdueC || prev.salesOverdueCount,
          salesOverdueTotal: sOverdueT || prev.salesOverdueTotal,

          billsDraftCount: bDraftC || prev.billsDraftCount,
          billsDraftTotal: bDraftT || prev.billsDraftTotal,
          billsAwaitingCount: bAwaitingC || prev.billsAwaitingCount,
          billsAwaitingTotal: bAwaitingT || prev.billsAwaitingTotal,
          billsOverdueCount: bOverdueC || prev.billsOverdueCount,
          billsOverdueTotal: bOverdueT || prev.billsOverdueTotal,

          capturedDocsCount: cDocs || prev.capturedDocsCount,
        }));
      } catch {
        // keep fallback mock numbers
      }
    }

    loadStats();
  }, []);

  const formatGBP = (num: number) => {
    return "£" + num.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* ── TOP BANNER: EXECUTIVE GREETING & ORG STATUS ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Business Dashboard</h1>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                UK VAT Registered
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Acme Corp UK Ltd · Financial Year ends 31 Dec 2026 · Base currency: GBP (£)
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/app/documents"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5 text-sky-600" />
              Smart AI Inbox ({summary.capturedDocsCount})
            </Link>
            <Link
              href="/app/sales/invoices/new"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-[#0073B7] hover:bg-[#005f96] text-white shadow-sm transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              New Invoice
            </Link>
            <Link
              href="/app/purchases/bills/new"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 shadow-sm transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              New Bill
            </Link>
          </div>
        </div>

        {/* ── GRID OF XERO CORE WIDGETS ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 1: BUSINESS BANK ACCOUNT (The iconic Reconcile Card) */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-sky-50 border border-sky-200 text-sky-700 flex items-center justify-center font-bold">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Barclays Business Account</h3>
                  <p className="text-[11px] text-slate-500 font-mono">Sort: 20-04-71 · Acc: 84920194</p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <span className="text-[10px] text-slate-400">Updated 10m ago</span>
                <button className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600">
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Balances & Reconcile Button */}
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div className="grid grid-cols-2 gap-4 pb-4">
                <div>
                  <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Statement Balance</p>
                  <p className="text-2xl font-bold text-slate-900 font-mono mt-0.5 tracking-tight">£142,680.45</p>
                  <p className="text-[10px] text-emerald-600 font-medium mt-0.5">Synced via Open Banking feed</p>
                </div>
                <div>
                  <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Balance in Ladger</p>
                  <p className="text-2xl font-bold text-slate-900 font-mono mt-0.5 tracking-tight">£142,680.45</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Fully in sync</p>
                </div>
              </div>

              {/* Sparkline Graph Simulation */}
              <div className="py-2">
                <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span>30-day cash movements</span>
                  <span className="text-emerald-600 font-semibold flex items-center gap-0.5">
                    <ArrowUpRight className="h-3 w-3" /> +£14,250 net inflow
                  </span>
                </div>
                <div className="h-14 w-full relative">
                  <svg className="w-full h-full overflow-visible" viewBox="0 0 400 60" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="blueGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#0073B7" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="#0073B7" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M0,45 Q40,30 80,42 T160,25 T240,32 T320,15 T400,18 L400,60 L0,60 Z"
                      fill="url(#blueGrad)"
                    />
                    <path
                      d="M0,45 Q40,30 80,42 T160,25 T240,32 T320,15 T400,18"
                      fill="none"
                      stroke="#0073B7"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
              </div>

              {/* Iconic Xero Reconcile Action Pill */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-sky-700 font-medium">
                  <Link href="/app/dashboard" className="hover:underline">Account transactions</Link>
                  <span>·</span>
                  <Link href="/app/dashboard" className="hover:underline">Bank rules</Link>
                </div>

                <Link
                  href="/app/dashboard"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-bold shadow-sm transition-all"
                >
                  <span>Reconcile 8 items</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 2: INVOICES OWED TO YOU (Sales / Receivables)      */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center font-bold">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Invoices owed to you</h3>
                  <p className="text-[11px] text-slate-500">Accounts Receivable (Sales)</p>
                </div>
              </div>

              <Link
                href="/app/sales/invoices/new"
                className="inline-flex items-center gap-1 text-xs font-bold text-[#0073B7] hover:text-[#005f96] hover:underline"
              >
                <Plus className="h-3.5 w-3.5" /> New sales invoice
              </Link>
            </div>

            {/* Metric Status Pills Bar (Xero Signature) */}
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div className="grid grid-cols-3 gap-2">
                <Link
                  href="/app/sales/invoices?status=DRAFT"
                  className="p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-slate-600 block">
                    Draft ({summary.salesDraftCount})
                  </span>
                  <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                    {formatGBP(summary.salesDraftTotal)}
                  </span>
                </Link>

                <Link
                  href="/app/sales/invoices?status=AWAITING_PAYMENT"
                  className="p-2.5 rounded-lg bg-sky-50 hover:bg-sky-100/80 border border-sky-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-sky-800 block">
                    Awaiting ({summary.salesAwaitingCount})
                  </span>
                  <span className="text-sm font-bold text-sky-950 font-mono mt-0.5 block">
                    {formatGBP(summary.salesAwaitingTotal)}
                  </span>
                </Link>

                <Link
                  href="/app/sales/invoices?status=OVERDUE"
                  className="p-2.5 rounded-lg bg-rose-50 hover:bg-rose-100/80 border border-rose-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-rose-800 block">
                    Overdue ({summary.salesOverdueCount})
                  </span>
                  <span className="text-sm font-bold text-rose-950 font-mono mt-0.5 block">
                    {formatGBP(summary.salesOverdueTotal)}
                  </span>
                </Link>
              </div>

              {/* Aging Breakdown Visualization */}
              <div className="py-4">
                <p className="text-[11px] font-medium text-slate-500 mb-2">Invoice aging breakdown</p>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="bg-slate-100/80 rounded-md p-2">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Older</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-slate-300 rounded-t h-4" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 font-mono">£1.2k</span>
                  </div>
                  <div className="bg-rose-50/60 rounded-md p-2 border border-rose-100">
                    <span className="text-[10px] text-rose-600 uppercase font-semibold">Aug</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-rose-400 rounded-t h-8" />
                    </div>
                    <span className="text-xs font-bold text-rose-800 font-mono">£3.4k</span>
                  </div>
                  <div className="bg-sky-50/60 rounded-md p-2 border border-sky-100">
                    <span className="text-[10px] text-sky-600 uppercase font-semibold">Current</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-sky-500 rounded-t h-10" />
                    </div>
                    <span className="text-xs font-bold text-sky-900 font-mono">£11.8k</span>
                  </div>
                  <div className="bg-emerald-50/60 rounded-md p-2 border border-emerald-100">
                    <span className="text-[10px] text-emerald-600 uppercase font-semibold">Future</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-emerald-400 rounded-t h-6" />
                    </div>
                    <span className="text-xs font-bold text-emerald-800 font-mono">£5.4k</span>
                  </div>
                </div>
              </div>

              {/* Bottom link */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">Total outstanding receivables</span>
                <Link
                  href="/app/sales/invoices"
                  className="text-xs font-bold text-[#0073B7] hover:underline flex items-center gap-1"
                >
                  View all invoices ({summary.salesDraftCount + summary.salesAwaitingCount + summary.salesOverdueCount})
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 3: BILLS YOU NEED TO PAY (Purchases / Payables)    */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 flex items-center justify-center font-bold">
                  <Receipt className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Bills you need to pay</h3>
                  <p className="text-[11px] text-slate-500">Accounts Payable (Suppliers)</p>
                </div>
              </div>

              <Link
                href="/app/purchases/bills/new"
                className="inline-flex items-center gap-1 text-xs font-bold text-[#0073B7] hover:text-[#005f96] hover:underline"
              >
                <Plus className="h-3.5 w-3.5" /> New bill
              </Link>
            </div>

            {/* Metric Status Pills */}
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div className="grid grid-cols-3 gap-2">
                <Link
                  href="/app/purchases/bills?status=DRAFT"
                  className="p-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-slate-600 block">
                    Draft ({summary.billsDraftCount})
                  </span>
                  <span className="text-sm font-bold text-slate-900 font-mono mt-0.5 block">
                    {formatGBP(summary.billsDraftTotal)}
                  </span>
                </Link>

                <Link
                  href="/app/purchases/bills?status=AWAITING_PAYMENT"
                  className="p-2.5 rounded-lg bg-sky-50 hover:bg-sky-100/80 border border-sky-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-sky-800 block">
                    Awaiting ({summary.billsAwaitingCount})
                  </span>
                  <span className="text-sm font-bold text-sky-950 font-mono mt-0.5 block">
                    {formatGBP(summary.billsAwaitingTotal)}
                  </span>
                </Link>

                <Link
                  href="/app/purchases/bills?status=OVERDUE"
                  className="p-2.5 rounded-lg bg-rose-50 hover:bg-rose-100/80 border border-rose-200 transition-colors"
                >
                  <span className="text-[11px] font-semibold text-rose-800 block">
                    Overdue ({summary.billsOverdueCount})
                  </span>
                  <span className="text-sm font-bold text-rose-950 font-mono mt-0.5 block">
                    {formatGBP(summary.billsOverdueTotal)}
                  </span>
                </Link>
              </div>

              {/* Payable Aging Chart */}
              <div className="py-4">
                <p className="text-[11px] font-medium text-slate-500 mb-2">Upcoming bills schedule</p>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="bg-rose-50/60 rounded-md p-2 border border-rose-100">
                    <span className="text-[10px] text-rose-600 uppercase font-semibold">Overdue</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-rose-400 rounded-t h-5" />
                    </div>
                    <span className="text-xs font-bold text-rose-800 font-mono">£1.2k</span>
                  </div>
                  <div className="bg-amber-50/60 rounded-md p-2 border border-amber-100">
                    <span className="text-[10px] text-amber-700 uppercase font-semibold">Due 7 Days</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-amber-400 rounded-t h-9" />
                    </div>
                    <span className="text-xs font-bold text-amber-900 font-mono">£4.1k</span>
                  </div>
                  <div className="bg-slate-50 rounded-md p-2 border border-slate-200">
                    <span className="text-[10px] text-slate-600 uppercase font-semibold">Due 14 Days</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-slate-400 rounded-t h-7" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 font-mono">£3.2k</span>
                  </div>
                  <div className="bg-slate-50 rounded-md p-2 border border-slate-200">
                    <span className="text-[10px] text-slate-600 uppercase font-semibold">Later</span>
                    <div className="h-10 flex items-end justify-center py-1">
                      <div className="w-6 bg-slate-400 rounded-t h-3" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 font-mono">£1.3k</span>
                  </div>
                </div>
              </div>

              {/* Bottom link */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">Payable cash commitment</span>
                <Link
                  href="/app/purchases/bills"
                  className="text-xs font-bold text-[#0073B7] hover:underline flex items-center gap-1"
                >
                  View all bills ({summary.billsDraftCount + summary.billsAwaitingCount + summary.billsOverdueCount})
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 4: SMART DOCUMENT CAPTURE (Hubdoc / AI Inbox)     */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-sky-50 border border-sky-200 text-sky-700 flex items-center justify-center font-bold">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">Smart Document Capture</h3>
                    <span className="text-[10px] bg-sky-100 text-sky-800 font-bold px-1.5 py-0.2 rounded">
                      AI Optical Engine
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500">Autonomous receipt & invoice extraction</p>
                </div>
              </div>

              <Link
                href="/app/documents"
                className="text-xs font-bold text-[#0073B7] hover:underline"
              >
                Go to Inbox
              </Link>
            </div>

            <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
              {/* Quick dropzone banner */}
              <Link
                href="/app/documents?upload=true"
                className="p-4 rounded-lg border-2 border-dashed border-sky-300 hover:border-sky-500 bg-sky-50/40 hover:bg-sky-50/80 transition-all flex items-center justify-center gap-3 group text-center"
              >
                <UploadCloud className="h-6 w-6 text-sky-600 group-hover:scale-110 transition-transform" />
                <div>
                  <p className="text-xs font-bold text-slate-800">Drop PDF invoices or phone receipts here</p>
                  <p className="text-[11px] text-slate-500">Auto-classified, OCR line-item matched & ready for bill creation</p>
                </div>
              </Link>

              {/* Recent Extracted Documents Stream */}
              <div className="space-y-2">
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Awaiting Confirmation</p>
                
                <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold">
                      PDF
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-900">AWS EMEA SARL · Invoice #INV-83921</p>
                      <p className="text-[10px] text-slate-500">Extracted: Supplier matched · Tax 20% · Confidence 99%</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-900 font-mono">£412.80</p>
                    <Link
                      href="/app/documents"
                      className="text-[11px] text-sky-600 hover:text-sky-800 font-semibold"
                    >
                      Convert →
                    </Link>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded bg-amber-100 text-amber-700 flex items-center justify-center text-xs font-bold">
                      IMG
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-900">Staples UK · Receipt #REC-2041</p>
                      <p className="text-[10px] text-slate-500">Extracted: Office Supplies · Tax 20% · Confidence 94%</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-900 font-mono">£48.50</p>
                    <Link
                      href="/app/documents"
                      className="text-[11px] text-sky-600 hover:text-sky-800 font-semibold"
                    >
                      Convert →
                    </Link>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">4 documents ready to process</span>
                <Link
                  href="/app/documents"
                  className="inline-flex items-center gap-1 text-xs font-bold text-[#0073B7] hover:underline"
                >
                  Process all in Smart Inbox
                  <ChevronRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 5: TOTAL CASH IN & OUT (Cashflow Comparison)      */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Total cash in and out</h3>
                <p className="text-[11px] text-slate-500">6-Month comparative cashflow</p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  <span className="text-slate-600 text-[11px]">Cash in</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-sky-500" />
                  <span className="text-slate-600 text-[11px]">Cash out</span>
                </div>
              </div>
            </div>

            <div className="p-5 flex-1 flex flex-col justify-between">
              {/* Monthly Grouped Bars */}
              <div className="grid grid-cols-6 gap-3 text-center py-4">
                {[
                  { month: "Apr", in: 28, out: 19 },
                  { month: "May", in: 34, out: 22 },
                  { month: "Jun", in: 31, out: 26 },
                  { month: "Jul", in: 42, out: 28 },
                  { month: "Aug", in: 39, out: 24 },
                  { month: "Sep", in: 46, out: 29 },
                ].map((item) => (
                  <div key={item.month} className="flex flex-col items-center">
                    <div className="h-24 flex items-end justify-center gap-1 py-1">
                      <div
                        className="w-3.5 bg-emerald-500 hover:bg-emerald-600 rounded-t transition-all"
                        style={{ height: `${(item.in / 50) * 100}%` }}
                        title={`In: £${item.in}k`}
                      />
                      <div
                        className="w-3.5 bg-sky-500 hover:bg-sky-600 rounded-t transition-all"
                        style={{ height: `${(item.out / 50) * 100}%` }}
                        title={`Out: £${item.out}k`}
                      />
                    </div>
                    <span className="text-[11px] font-semibold text-slate-600 mt-1">{item.month}</span>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">Net operating surplus YTD</span>
                <span className="font-bold text-emerald-600 font-mono text-sm">+£78,420.00</span>
              </div>
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════ */}
          {/* WIDGET 6: ACCOUNT WATCHLIST                                */}
          {/* ══════════════════════════════════════════════════════════ */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Account Watchlist</h3>
                <p className="text-[11px] text-slate-500">Key performance ledger accounts</p>
              </div>
              <span className="text-xs text-sky-700 font-medium hover:underline cursor-pointer">
                Manage accounts
              </span>
            </div>

            <div className="p-0 flex-1 overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] font-semibold text-slate-400 uppercase tracking-wider bg-slate-50/50">
                    <th className="px-5 py-2.5">Account</th>
                    <th className="px-4 py-2.5 text-right">This Month</th>
                    <th className="px-5 py-2.5 text-right">YTD</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  <tr className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      200 - Sales / Software Turnover
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      £38,450.00
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-900">
                      £218,900.00
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      400 - Advertising & Digital Marketing
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      £1,250.00
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-900">
                      £8,940.00
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      420 - Software & Cloud Hosting
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      £2,400.00
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-900">
                      £16,800.00
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      450 - Legal & Accountancy Services
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      £750.00
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-900">
                      £4,500.00
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      480 - Travel & Subsistence
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium text-slate-900">
                      £320.00
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-900">
                      £2,150.00
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50/30 flex items-center justify-between text-xs">
              <span className="text-slate-500">Showing 5 tracked ledger codes</span>
              <span className="text-sky-700 font-semibold hover:underline cursor-pointer">
                View Full Chart of Accounts →
              </span>
            </div>
          </div>

        </div>
      </div>
    </DashboardLayout>
  );
}
