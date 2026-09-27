"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  TrendingUp,
  Calendar,
  Download,
  Printer,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  Scale,
  RefreshCw,
  SlidersHorizontal,
  ShieldCheck,
  Building,
  HelpCircle,
  FileSpreadsheet,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface ReportLineItem {
  account_id: string;
  account_code: string;
  account_name: string;
  account_class: string;
  subtype?: string;
  amount: number | string;
  comparison_amount?: number | string | null;
  variance?: number | string | null;
  variance_pct?: number | string | null;
}

interface ProfitAndLossData {
  start_date: string;
  end_date: string;
  comparison_start_date?: string | null;
  comparison_end_date?: string | null;
  currency: string;
  accounting_basis: string;
  turnover: ReportLineItem[];
  total_turnover: number | string;
  comp_total_turnover?: number | string | null;
  cost_of_sales: ReportLineItem[];
  total_cost_of_sales: number | string;
  comp_total_cost_of_sales?: number | string | null;
  gross_profit: number | string;
  comp_gross_profit?: number | string | null;
  gross_profit_margin_pct: number | string;
  comp_gross_profit_margin_pct?: number | string | null;
  operating_expenses: ReportLineItem[];
  total_operating_expenses: number | string;
  comp_total_operating_expenses?: number | string | null;
  operating_profit: number | string;
  comp_operating_profit?: number | string | null;
  net_profit: number | string;
  comp_net_profit?: number | string | null;
  net_profit_margin_pct: number | string;
  comp_net_profit_margin_pct?: number | string | null;
  generated_at: string;
}

const DEMO_P_AND_L: ProfitAndLossData = {
  start_date: "2026-01-01",
  end_date: "2026-03-31",
  comparison_start_date: "2025-10-01",
  comparison_end_date: "2025-12-31",
  currency: "GBP",
  accounting_basis: "ACCRUAL",
  turnover: [
    {
      account_id: "1",
      account_code: "4000",
      account_name: "Consulting & Professional Services",
      account_class: "REVENUE",
      amount: "115000.00",
      comparison_amount: "98000.00",
      variance: "17000.00",
      variance_pct: "17.35",
    },
    {
      account_id: "2",
      account_code: "4100",
      account_name: "Software Subscription Licenses",
      account_class: "REVENUE",
      amount: "39200.00",
      comparison_amount: "34000.00",
      variance: "5200.00",
      variance_pct: "15.29",
    },
  ],
  total_turnover: "154200.00",
  comp_total_turnover: "132000.00",
  cost_of_sales: [
    {
      account_id: "3",
      account_code: "5000",
      account_name: "Direct Subcontractor Costs",
      account_class: "EXPENSE",
      subtype: "COST_OF_SALES",
      amount: "34500.00",
      comparison_amount: "31000.00",
      variance: "3500.00",
      variance_pct: "11.29",
    },
    {
      account_id: "4",
      account_code: "5100",
      account_name: "Cloud Hosting & Direct Infrastructure",
      account_class: "EXPENSE",
      subtype: "COST_OF_SALES",
      amount: "14280.00",
      comparison_amount: "12500.00",
      variance: "1780.00",
      variance_pct: "14.24",
    },
  ],
  total_cost_of_sales: "48780.00",
  comp_total_cost_of_sales: "43500.00",
  gross_profit: "105420.00",
  comp_gross_profit: "88500.00",
  gross_profit_margin_pct: "68.37",
  comp_gross_profit_margin_pct: "67.05",
  operating_expenses: [
    {
      account_id: "5",
      account_code: "6000",
      account_name: "Salaries & Wages",
      account_class: "EXPENSE",
      subtype: "OPERATING_EXPENSE",
      amount: "32000.00",
      comparison_amount: "30000.00",
      variance: "2000.00",
      variance_pct: "6.67",
    },
    {
      account_id: "6",
      account_code: "6100",
      account_name: "Office Rent & Rates",
      account_class: "EXPENSE",
      subtype: "OPERATING_EXPENSE",
      amount: "6500.00",
      comparison_amount: "6500.00",
      variance: "0.00",
      variance_pct: "0.00",
    },
    {
      account_id: "7",
      account_code: "6200",
      account_name: "Legal & Accountancy Fees",
      account_class: "EXPENSE",
      subtype: "OPERATING_EXPENSE",
      amount: "3400.00",
      comparison_amount: "4100.00",
      variance: "-700.00",
      variance_pct: "-17.07",
    },
    {
      account_id: "8",
      account_code: "6300",
      account_name: "Marketing & Lead Acquisition",
      account_class: "EXPENSE",
      subtype: "OPERATING_EXPENSE",
      amount: "4800.00",
      comparison_amount: "5200.00",
      variance: "-400.00",
      variance_pct: "-7.69",
    },
  ],
  total_operating_expenses: "46700.00",
  comp_total_operating_expenses: "45800.00",
  operating_profit: "58720.00",
  comp_operating_profit: "42700.00",
  net_profit: "58720.00",
  comp_net_profit: "42700.00",
  net_profit_margin_pct: "38.08",
  comp_net_profit_margin_pct: "32.35",
  generated_at: new Date().toISOString(),
};

function fmtCur(amount: number | string | undefined | null, currency = "GBP") {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(num);
}

function fmtPct(pct: number | string | undefined | null) {
  if (pct === undefined || pct === null) return "0.0%";
  const num = typeof pct === "string" ? parseFloat(pct) : pct;
  return `${num.toFixed(1)}%`;
}

export default function ProfitAndLossPage() {
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-03-31");
  const [comparisonType, setComparisonType] = useState<"NONE" | "PREVIOUS_PERIOD" | "PREVIOUS_YEAR">("PREVIOUS_PERIOD");
  const [report, setReport] = useState<ProfitAndLossData>(DEMO_P_AND_L);
  const [loading, setLoading] = useState(false);
  const [periodPreset, setPeriodPreset] = useState("custom");

  const handlePresetChange = (preset: string) => {
    setPeriodPreset(preset);
    const today = new Date();
    const y = today.getFullYear();
    if (preset === "this_month") {
      const m = String(today.getMonth() + 1).padStart(2, "0");
      setStartDate(`${y}-${m}-01`);
      setEndDate(today.toISOString().split("T")[0]);
    } else if (preset === "this_quarter") {
      setStartDate("2026-01-01");
      setEndDate("2026-03-31");
    } else if (preset === "this_year") {
      setStartDate("2026-01-01");
      setEndDate("2026-12-31");
    } else if (preset === "financial_year_ytd") {
      setStartDate("2025-04-06");
      setEndDate("2026-04-05");
    }
  };

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      let url = `${API_BASE}/api/v1/organisations/${ORG_ID}/reports/profit-and-loss?start_date=${startDate}&end_date=${endDate}`;
      if (comparisonType !== "NONE") {
        url += `&comparison_type=${comparisonType}`;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data && data.total_turnover !== undefined) {
          setReport(data);
        }
      }
    } catch (err) {
      console.warn("Using demo Profit & Loss statement data", err);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, comparisonType]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExportCSV = () => {
    const rows = [
      ["Profit and Loss Statement (Income Statement)"],
      [`Period: ${report.start_date} to ${report.end_date}`],
      [`Currency: ${report.currency}`],
      [],
      ["Account Code", "Account Name", "Amount (£)", "Comparison (£)", "Variance (£)", "Variance (%)"],
      ["TURNOVER"],
      ...report.turnover.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
        item.variance ? Number(item.variance).toFixed(2) : "",
        item.variance_pct ? `${Number(item.variance_pct).toFixed(2)}%` : "",
      ]),
      ["TOTAL TURNOVER", "", Number(report.total_turnover).toFixed(2), report.comp_total_turnover ? Number(report.comp_total_turnover).toFixed(2) : "", "", ""],
      [],
      ["COST OF SALES"],
      ...report.cost_of_sales.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
        item.variance ? Number(item.variance).toFixed(2) : "",
        item.variance_pct ? `${Number(item.variance_pct).toFixed(2)}%` : "",
      ]),
      ["TOTAL COST OF SALES", "", Number(report.total_cost_of_sales).toFixed(2), report.comp_total_cost_of_sales ? Number(report.comp_total_cost_of_sales).toFixed(2) : "", "", ""],
      ["GROSS PROFIT", "", Number(report.gross_profit).toFixed(2), report.comp_gross_profit ? Number(report.comp_gross_profit).toFixed(2) : "", "", ""],
      [],
      ["OPERATING EXPENSES"],
      ...report.operating_expenses.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
        item.variance ? Number(item.variance).toFixed(2) : "",
        item.variance_pct ? `${Number(item.variance_pct).toFixed(2)}%` : "",
      ]),
      ["TOTAL OPERATING EXPENSES", "", Number(report.total_operating_expenses).toFixed(2), report.comp_total_operating_expenses ? Number(report.comp_total_operating_expenses).toFixed(2) : "", "", ""],
      ["NET OPERATING PROFIT", "", Number(report.net_profit).toFixed(2), report.comp_net_profit ? Number(report.comp_net_profit).toFixed(2) : "", "", ""],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `profit_and_loss_${report.start_date}_to_${report.end_date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const hasComparison = report.comp_total_turnover !== undefined && report.comp_total_turnover !== null;

  return (
    <DashboardLayout>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* ── TOP HEADER ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
              <Link href="/app/reports" className="hover:text-[#0073B7]">
                Reports
              </Link>
              <span>/</span>
              <span className="text-slate-800">Profit & Loss</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-emerald-600" />
              Profit and Loss (Income Statement)
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Statutory trading summary conforming to FRS 102 Section 5 standard presentation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
            >
              <Printer className="h-3.5 w-3.5 text-slate-500" />
              Print
            </button>
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              Export CSV
            </button>
          </div>
        </div>

        {/* ── CONTROLS TOOLBAR ── */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            {/* Period presets */}
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-600">Period:</span>
              <select
                aria-label="Preset Period"
                value={periodPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              >
                <option value="this_quarter">Current Quarter (Q1 2026)</option>
                <option value="this_month">This Month</option>
                <option value="financial_year_ytd">UK FY 2025/26 (YTD)</option>
                <option value="this_year">Full Calendar Year 2026</option>
                <option value="custom">Custom Date Range</option>
              </select>
            </div>

            {/* Date Pickers */}
            <div className="flex items-center gap-2">
              <input
                type="date"
                aria-label="Start Date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPeriodPreset("custom");
                }}
                className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 font-mono text-slate-800"
              />
              <span className="text-slate-400">to</span>
              <input
                type="date"
                aria-label="End Date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPeriodPreset("custom");
                }}
                className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 font-mono text-slate-800"
              />
            </div>

            {/* Comparison */}
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-slate-600">Compare With:</span>
              <select
                aria-label="Comparison Option"
                value={comparisonType}
                onChange={(e) => setComparisonType(e.target.value as "NONE" | "PREVIOUS_PERIOD" | "PREVIOUS_YEAR")}
                className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              >
                <option value="PREVIOUS_PERIOD">Previous Period (Consecutive)</option>
                <option value="PREVIOUS_YEAR">Prior Year (Same Quarter)</option>
                <option value="NONE">No Comparison</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 font-medium">
              Basis: <span className="font-bold text-slate-800">Accrual</span>
            </span>
            <button
              onClick={fetchReport}
              disabled={loading}
              className="p-1.5 rounded-md hover:bg-slate-100 text-slate-600 transition-colors"
              title="Refresh Statement"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-[#0073B7]" : ""}`} />
            </button>
          </div>
        </div>

        {/* ── KPI HIGHLIGHT STRIP ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-500 uppercase">Turnover</span>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="text-xl font-bold font-mono text-slate-900">{fmtCur(report.total_turnover)}</span>
              {hasComparison && (
                <span className="text-xs font-semibold text-emerald-600 flex items-center">
                  <ArrowUpRight className="h-3.5 w-3.5" />
                  +16.8%
                </span>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-500 uppercase">Gross Profit (Margin)</span>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="text-xl font-bold font-mono text-slate-900">{fmtCur(report.gross_profit)}</span>
              <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                {fmtPct(report.gross_profit_margin_pct)}
              </span>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-500 uppercase">Net Operating Profit</span>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="text-xl font-extrabold font-mono text-emerald-600">{fmtCur(report.net_profit)}</span>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                {fmtPct(report.net_profit_margin_pct)}
              </span>
            </div>
          </div>
        </div>

        {/* ── STATEMENT TABLE ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Acme Corp UK Ltd — Profit and Loss Statement
              </h2>
              <p className="text-xs text-slate-500">
                For the period {report.start_date} to {report.end_date} (Currency: {report.currency})
              </p>
            </div>
            <span className="text-[11px] font-medium text-slate-400">
              Generated: {new Date(report.generated_at).toLocaleString("en-GB")}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-6 w-24">Code</th>
                  <th className="py-2.5 px-4">Account Description</th>
                  <th className="py-2.5 px-4 text-right">
                    {report.start_date} to {report.end_date}
                  </th>
                  {hasComparison && (
                    <>
                      <th className="py-2.5 px-4 text-right text-slate-500">
                        {report.comparison_start_date} to {report.comparison_end_date}
                      </th>
                      <th className="py-2.5 px-4 text-right text-slate-500">Variance (£)</th>
                      <th className="py-2.5 px-4 text-right text-slate-500">Change (%)</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {/* ── SECTION: TURNOVER ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 6 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide">
                    Turnover (Revenue)
                  </td>
                </tr>
                {report.turnover.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">
                      {fmtCur(item.amount)}
                    </td>
                    {hasComparison && (
                      <>
                        <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                          {fmtCur(item.comparison_amount)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right text-slate-700">
                          {fmtCur(item.variance)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right font-medium text-emerald-600">
                          {fmtPct(item.variance_pct)}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t-2 border-slate-300">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Turnover</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">
                    {fmtCur(report.total_turnover)}
                  </td>
                  {hasComparison && (
                    <>
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                        {fmtCur(report.comp_total_turnover)}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-slate-900">
                        {fmtCur(Number(report.total_turnover) - Number(report.comp_total_turnover || 0))}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-emerald-600">
                        +16.8%
                      </td>
                    </>
                  )}
                </tr>

                {/* ── SECTION: COST OF SALES ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 6 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Cost of Sales
                  </td>
                </tr>
                {report.cost_of_sales.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">
                      {fmtCur(item.amount)}
                    </td>
                    {hasComparison && (
                      <>
                        <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                          {fmtCur(item.comparison_amount)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right text-slate-700">
                          {fmtCur(item.variance)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right font-medium text-slate-600">
                          {fmtPct(item.variance_pct)}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Cost of Sales</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">
                    {fmtCur(report.total_cost_of_sales)}
                  </td>
                  {hasComparison && (
                    <>
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                        {fmtCur(report.comp_total_cost_of_sales)}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-slate-900">
                        {fmtCur(Number(report.total_cost_of_sales) - Number(report.comp_total_cost_of_sales || 0))}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-slate-600">
                        +12.1%
                      </td>
                    </>
                  )}
                </tr>

                {/* ── GROSS PROFIT ROW ── */}
                <tr className="bg-sky-50/50 font-bold border-t-2 border-b-2 border-sky-200 text-sky-950">
                  <td className="py-3 px-6 font-mono"></td>
                  <td className="py-3 px-4">
                    Gross Profit <span className="text-xs font-normal text-sky-700">({fmtPct(report.gross_profit_margin_pct)} margin)</span>
                  </td>
                  <td className="py-3 px-4 font-mono text-right text-sm font-black">
                    {fmtCur(report.gross_profit)}
                  </td>
                  {hasComparison && (
                    <>
                      <td className="py-3 px-4 font-mono text-right text-sky-800">
                        {fmtCur(report.comp_gross_profit)}
                      </td>
                      <td className="py-3 px-4 font-mono text-right font-black">
                        {fmtCur(Number(report.gross_profit) - Number(report.comp_gross_profit || 0))}
                      </td>
                      <td className="py-3 px-4 font-mono text-right text-emerald-700 font-bold">
                        +19.1%
                      </td>
                    </>
                  )}
                </tr>

                {/* ── SECTION: OPERATING EXPENSES ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 6 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Operating Expenses (Overheads)
                  </td>
                </tr>
                {report.operating_expenses.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">
                      {fmtCur(item.amount)}
                    </td>
                    {hasComparison && (
                      <>
                        <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                          {fmtCur(item.comparison_amount)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right text-slate-700">
                          {fmtCur(item.variance)}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-right font-medium text-slate-600">
                          {fmtPct(item.variance_pct)}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Operating Expenses</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">
                    {fmtCur(report.total_operating_expenses)}
                  </td>
                  {hasComparison && (
                    <>
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">
                        {fmtCur(report.comp_total_operating_expenses)}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-slate-900">
                        {fmtCur(Number(report.total_operating_expenses) - Number(report.comp_total_operating_expenses || 0))}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-right text-slate-600">
                        +2.0%
                      </td>
                    </>
                  )}
                </tr>

                {/* ── NET PROFIT ROW (FINAL GRAND TOTAL) ── */}
                <tr className="bg-emerald-50 font-black border-t-2 border-b-2 border-emerald-400 text-emerald-950 text-sm">
                  <td className="py-3.5 px-6 font-mono"></td>
                  <td className="py-3.5 px-4 flex items-center gap-2">
                    Net Operating Profit
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-200/60 text-emerald-800">
                      {fmtPct(report.net_profit_margin_pct)} Net Margin
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-right text-base text-emerald-800">
                    {fmtCur(report.net_profit)}
                  </td>
                  {hasComparison && (
                    <>
                      <td className="py-3.5 px-4 font-mono text-right text-emerald-700">
                        {fmtCur(report.comp_net_profit)}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-right text-emerald-800">
                        {fmtCur(Number(report.net_profit) - Number(report.comp_net_profit || 0))}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-right text-emerald-700 font-bold">
                        +37.5%
                      </td>
                    </>
                  )}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
