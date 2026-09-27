"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  FileSpreadsheet,
  Scale,
  Users,
  Building2,
  Calendar,
  ArrowRight,
  ShieldCheck,
  Download,
  Printer,
  Sparkles,
  BookOpen,
  PieChart,
  DollarSign,
  AlertCircle,
  Clock,
  ChevronRight,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

interface ReportCardProps {
  title: string;
  description: string;
  href: string;
  badge?: string;
  badgeColor?: string;
  icon: React.ReactNode;
  frequency: string;
  standard: string;
  keyMetricLabel: string;
  keyMetricValue: string;
}

function ReportCard({
  title,
  description,
  href,
  badge,
  badgeColor = "bg-sky-50 text-sky-700 border-sky-200",
  icon,
  frequency,
  standard,
  keyMetricLabel,
  keyMetricValue,
}: ReportCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 hover:border-[#00A3C4] shadow-sm hover:shadow-md transition-all duration-200 p-6 flex flex-col justify-between group">
      <div>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="h-12 w-12 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-center group-hover:bg-[#00A3C4]/10 group-hover:border-[#00A3C4]/30 transition-colors">
            {icon}
          </div>
          <div className="flex items-center gap-2">
            {badge && (
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badgeColor}`}
              >
                {badge}
              </span>
            )}
            <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
              {frequency}
            </span>
          </div>
        </div>

        <h3 className="text-base font-bold text-slate-900 group-hover:text-[#0073B7] transition-colors flex items-center gap-1.5">
          {title}
          <ChevronRight className="h-4 w-4 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-[#0073B7]" />
        </h3>
        <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
          {description}
        </p>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-500 font-medium">{keyMetricLabel}</span>
          <span className="font-bold font-mono text-slate-900">{keyMetricValue}</span>
        </div>
      </div>

      <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between">
        <span className="text-[11px] font-medium text-slate-400">
          Standard: <span className="text-slate-600">{standard}</span>
        </span>
        <Link
          href={href}
          className="inline-flex items-center gap-1 text-xs font-semibold text-[#0073B7] hover:text-[#005f96] transition-colors"
        >
          View Statement
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}

export default function ReportsHubPage() {
  const [selectedPeriod, setSelectedPeriod] = useState("2026-Q1");

  return (
    <DashboardLayout>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* ── HEADER BANNER ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-[#0A2540] via-[#0D3054] to-[#0A2540] text-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-800">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <ShieldCheck className="h-3.5 w-3.5" />
                Ledger Equilibrium Active
              </span>
              <span className="text-xs text-slate-400">UK GAAP / FRS 102 Compliant</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Financial Statements & Reports
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
              Real-time management accounting engine powered by double-entry ledger precision.
              Generate comparative P&L, balance sheets with automated retained earnings, and aged debtor/creditor schedules.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="bg-slate-800/80 border border-slate-700 rounded-lg p-1.5 flex items-center gap-2 text-xs">
              <Calendar className="h-4 w-4 text-sky-400 ml-1.5" />
              <select
                aria-label="Accounting Period"
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="bg-transparent text-white text-xs font-semibold focus:outline-none pr-3 cursor-pointer"
              >
                <option value="2026-Q1" className="bg-slate-900 text-white">Current Quarter (Q1 2026)</option>
                <option value="2026-YTD" className="bg-slate-900 text-white">Financial Year 2025/26 YTD</option>
                <option value="2025-FY" className="bg-slate-900 text-white">Financial Year 2024/25</option>
              </select>
            </div>

            <Link
              href="/app/accounting/trial-balance"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors border border-white/10"
            >
              <FileSpreadsheet className="h-4 w-4 text-sky-300" />
              Trial Balance
            </Link>
          </div>
        </div>

        {/* ── TOP KPI EXECUTIVE METRICS ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Net Profit YTD</span>
              <div className="h-8 w-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono text-slate-900">£105,420.00</span>
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                +14.8%
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Gross margin 68.4% on £154k turnover</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Net Assets</span>
              <div className="h-8 w-8 rounded-lg bg-sky-50 text-[#0073B7] flex items-center justify-center">
                <Scale className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono text-slate-900">£284,950.50</span>
              <span className="text-xs font-semibold text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded">
                Balanced
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Assets £342k · Liabilities £57k</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Aged Receivables</span>
              <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Users className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono text-slate-900">£24,650.00</span>
              <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                8 Invoices
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">92% within current 30-day terms</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Aged Payables</span>
              <div className="h-8 w-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <Building2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black font-mono text-slate-900">£18,220.00</span>
              <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                0 Overdue
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">All supplier liabilities current</p>
          </div>
        </div>

        {/* ── SECTION 1: PRIMARY FINANCIAL STATEMENTS ── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Primary Financial Statements</h2>
              <p className="text-xs text-slate-500">
                Core accounting reports reflecting trading performance and financial health
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <ReportCard
              title="Profit and Loss (Income Statement)"
              description="Summarises trading revenue, cost of sales, gross profit, and operating overheads over any fiscal timeframe with comparative analysis."
              href="/app/reports/profit-and-loss"
              badge="Most Viewed"
              badgeColor="bg-emerald-50 text-emerald-700 border-emerald-200"
              icon={<TrendingUp className="h-6 w-6 text-emerald-600" />}
              frequency="Monthly / Quarterly"
              standard="FRS 102 Section 5"
              keyMetricLabel="Net Operating Profit"
              keyMetricValue="£105,420.00"
            />

            <ReportCard
              title="Balance Sheet (Financial Position)"
              description="A point-in-time snapshot of entity assets, liabilities, and equity with automated mathematical equilibrium verification."
              href="/app/reports/balance-sheet"
              badge="Equilibrium Guaranteed"
              badgeColor="bg-sky-50 text-sky-700 border-sky-200"
              icon={<Scale className="h-6 w-6 text-[#0073B7]" />}
              frequency="As of Today"
              standard="FRS 102 Section 4"
              keyMetricLabel="Total Net Assets"
              keyMetricValue="£284,950.50"
            />

            <ReportCard
              title="Trial Balance (General Ledger)"
              description="Comprehensive listing of all Chart of Accounts debit and credit closing balances verifying zero posting discrepancy."
              href="/app/accounting/trial-balance"
              badge="Debit = Credit"
              badgeColor="bg-purple-50 text-purple-700 border-purple-200"
              icon={<FileSpreadsheet className="h-6 w-6 text-purple-600" />}
              frequency="Daily Continuous"
              standard="Double-Entry Core"
              keyMetricLabel="Balanced Debit/Credit"
              keyMetricValue="£116,350.50"
            />
          </div>
        </div>

        {/* ── SECTION 2: WORKING CAPITAL & AGING SCHEDULES ── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Working Capital & Aging Schedules</h2>
              <p className="text-xs text-slate-500">
                Debtor and creditor maturity schedules for cash-flow forecasting and credit control
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ReportCard
              title="Aged Receivables (Debtors Aging)"
              description="Itemised customer ledger tracking overdue sales invoices across 1-30, 31-60, 61-90, and >90 day brackets with drill-down."
              href="/app/reports/aged-receivables"
              badge="Credit Control"
              badgeColor="bg-blue-50 text-blue-700 border-blue-200"
              icon={<Users className="h-6 w-6 text-blue-600" />}
              frequency="Weekly"
              standard="Trade Receivables"
              keyMetricLabel="Overdue >30 Days"
              keyMetricValue="£1,970.00"
            />

            <ReportCard
              title="Aged Payables (Creditors Aging)"
              description="Outstanding vendor obligations and supplier bills categorised by payment due date to ensure prompt payment compliance."
              href="/app/reports/aged-payables"
              badge="Supplier Relations"
              badgeColor="bg-amber-50 text-amber-700 border-amber-200"
              icon={<Building2 className="h-6 w-6 text-amber-600" />}
              frequency="Weekly"
              standard="Trade Payables"
              keyMetricLabel="Due Next 7 Days"
              keyMetricValue="£4,300.00"
            />
          </div>
        </div>

        {/* ── SECTION 3: COMPLIANCE & EXPORT BANNER ── */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-sky-50 text-[#00A3C4] flex items-center justify-center flex-shrink-0">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                Audit Trail & Statutory Compliance Pack
              </h4>
              <p className="text-xs text-slate-600 mt-0.5">
                All statements are linked to underlying journal entries and source documents. Compatible with HMRC MTD and UK Companies House statutory filing formats.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            <Link
              href="/app/accounting/chart-of-accounts"
              className="px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors"
            >
              Chart of Accounts
            </Link>
            <Link
              href="/app/accounting/journals"
              className="px-4 py-2 rounded-lg bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-colors"
            >
              Review Journal Entries
            </Link>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
