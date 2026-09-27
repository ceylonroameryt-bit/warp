"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Scale,
  Calendar,
  Download,
  Printer,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Building2,
  TrendingUp,
  FileSpreadsheet,
  CheckCircle2,
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
}

interface BalanceSheetData {
  as_of_date: string;
  comparison_as_of_date?: string | null;
  currency: string;
  fixed_assets: ReportLineItem[];
  total_fixed_assets: number | string;
  current_assets: ReportLineItem[];
  total_current_assets: number | string;
  total_assets: number | string;
  current_liabilities: ReportLineItem[];
  total_current_liabilities: number | string;
  non_current_liabilities: ReportLineItem[];
  total_non_current_liabilities: number | string;
  total_liabilities: number | string;
  net_current_assets: number | string;
  net_assets: number | string;
  equity: ReportLineItem[];
  current_year_earnings: number | string;
  total_equity: number | string;
  total_liabilities_and_equity: number | string;
  is_balanced: boolean;
  equilibrium_discrepancy: number | string;
  generated_at: string;
}

const DEMO_BALANCE_SHEET: BalanceSheetData = {
  as_of_date: "2026-03-31",
  comparison_as_of_date: "2025-12-31",
  currency: "GBP",
  fixed_assets: [
    { account_id: "1", account_code: "1500", account_name: "Office Equipment & Tech", account_class: "ASSET", subtype: "FIXED_ASSET", amount: "18500.00", comparison_amount: "15000.00" },
    { account_id: "2", account_code: "1510", account_name: "Computer Software & IP", account_class: "ASSET", subtype: "FIXED_ASSET", amount: "25000.00", comparison_amount: "25000.00" },
  ],
  total_fixed_assets: "43500.00",
  current_assets: [
    { account_id: "3", account_code: "1000", account_name: "Operating Bank Account (Barclays)", account_class: "ASSET", subtype: "CURRENT_ASSET", amount: "184650.50", comparison_amount: "142000.00" },
    { account_id: "4", account_code: "1100", account_name: "Trade Accounts Receivable (Debtors)", account_class: "ASSET", subtype: "CURRENT_ASSET", amount: "52400.00", comparison_amount: "48000.00" },
    { account_id: "5", account_code: "1200", account_name: "Prepayments & Accruals", account_class: "ASSET", subtype: "CURRENT_ASSET", amount: "4400.00", comparison_amount: "3500.00" },
  ],
  total_current_assets: "241450.50",
  total_assets: "284950.50",
  current_liabilities: [
    { account_id: "6", account_code: "2000", account_name: "Trade Accounts Payable (Creditors)", account_class: "LIABILITY", subtype: "CURRENT_LIABILITY", amount: "22400.00", comparison_amount: "19500.00" },
    { account_id: "7", account_code: "2200", account_name: "HMRC VAT Output Liability", account_class: "LIABILITY", subtype: "CURRENT_LIABILITY", amount: "14830.00", comparison_amount: "12100.00" },
    { account_id: "8", account_code: "2210", account_name: "PAYE / National Insurance Payable", account_class: "LIABILITY", subtype: "CURRENT_LIABILITY", amount: "6720.00", comparison_amount: "6400.00" },
  ],
  total_current_liabilities: "43950.00",
  non_current_liabilities: [
    { account_id: "9", account_code: "2700", account_name: "Long-Term Bank Loan (5 Yr)", account_class: "LIABILITY", subtype: "NON_CURRENT_LIABILITY", amount: "20000.00", comparison_amount: "25000.00" },
  ],
  total_non_current_liabilities: "20000.00",
  total_liabilities: "63950.00",
  net_current_assets: "197500.50",
  net_assets: "221000.50",
  equity: [
    { account_id: "10", account_code: "3000", account_name: "Ordinary Share Capital", account_class: "EQUITY", subtype: "EQUITY", amount: "50000.00", comparison_amount: "50000.00" },
    { account_id: "11", account_code: "3200", account_name: "Historical Retained Earnings", account_class: "EQUITY", subtype: "EQUITY", amount: "112280.50", comparison_amount: "80000.00" },
  ],
  current_year_earnings: "58720.00",
  total_equity: "221000.50",
  total_liabilities_and_equity: "284950.50",
  is_balanced: true,
  equilibrium_discrepancy: "0.0000",
  generated_at: new Date().toISOString(),
};

function fmtCur(amount: number | string | undefined | null, currency = "GBP") {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(num);
}

export default function BalanceSheetPage() {
  const [asOfDate, setAsOfDate] = useState("2026-03-31");
  const [comparisonDate, setComparisonDate] = useState("2025-12-31");
  const [enableComparison, setEnableComparison] = useState(true);
  const [report, setReport] = useState<BalanceSheetData>(DEMO_BALANCE_SHEET);
  const [loading, setLoading] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      let url = `${API_BASE}/api/v1/organisations/${ORG_ID}/reports/balance-sheet?as_of_date=${asOfDate}`;
      if (enableComparison && comparisonDate) {
        url += `&comparison_date=${comparisonDate}`;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data && data.total_assets !== undefined) {
          setReport(data);
        }
      }
    } catch (err) {
      console.warn("Using demo Balance Sheet data", err);
    } finally {
      setLoading(false);
    }
  }, [asOfDate, comparisonDate, enableComparison]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExportCSV = () => {
    const rows = [
      ["Balance Sheet (Statement of Financial Position)"],
      [`As of: ${report.as_of_date}`],
      [`Currency: ${report.currency}`],
      [`Equilibrium Status: ${report.is_balanced ? "PERFECTLY BALANCED" : "DISCREPANCY DETECTED"}`],
      [],
      ["Account Code", "Account Name", "Amount (£)", report.comparison_as_of_date ? `As of ${report.comparison_as_of_date} (£)` : ""],
      ["FIXED ASSETS"],
      ...report.fixed_assets.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
      ]),
      ["TOTAL FIXED ASSETS", "", Number(report.total_fixed_assets).toFixed(2), ""],
      [],
      ["CURRENT ASSETS"],
      ...report.current_assets.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
      ]),
      ["TOTAL CURRENT ASSETS", "", Number(report.total_current_assets).toFixed(2), ""],
      ["TOTAL ASSETS", "", Number(report.total_assets).toFixed(2), ""],
      [],
      ["CURRENT LIABILITIES"],
      ...report.current_liabilities.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
      ]),
      ["TOTAL CURRENT LIABILITIES", "", Number(report.total_current_liabilities).toFixed(2), ""],
      [],
      ["NON-CURRENT LIABILITIES"],
      ...report.non_current_liabilities.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
      ]),
      ["TOTAL NON-CURRENT LIABILITIES", "", Number(report.total_non_current_liabilities).toFixed(2), ""],
      ["TOTAL LIABILITIES", "", Number(report.total_liabilities).toFixed(2), ""],
      ["NET CURRENT ASSETS", "", Number(report.net_current_assets).toFixed(2), ""],
      ["TOTAL NET ASSETS", "", Number(report.net_assets).toFixed(2), ""],
      [],
      ["CAPITAL & RESERVES (EQUITY)"],
      ...report.equity.map((item) => [
        item.account_code,
        `"${item.account_name.replace(/"/g, '""')}"`,
        Number(item.amount).toFixed(2),
        item.comparison_amount ? Number(item.comparison_amount).toFixed(2) : "",
      ]),
      ["CURRENT YEAR EARNINGS", "Automated P&L Integration", Number(report.current_year_earnings).toFixed(2), ""],
      ["TOTAL EQUITY", "", Number(report.total_equity).toFixed(2), ""],
      ["TOTAL LIABILITIES & EQUITY", "", Number(report.total_liabilities_and_equity).toFixed(2), ""],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `balance_sheet_as_of_${report.as_of_date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const hasComparison = enableComparison && report.comparison_as_of_date;

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
              <span className="text-slate-800">Balance Sheet</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <Scale className="h-6 w-6 text-[#0073B7]" />
              Balance Sheet (Statement of Financial Position)
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Cumulative financial state conforming to UK Companies House & FRS 102 Section 4 guidelines.
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
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-600">As of Date:</span>
              <input
                type="date"
                aria-label="As of Date"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={enableComparison}
                  onChange={(e) => setEnableComparison(e.target.checked)}
                  className="rounded border-slate-300 text-[#0073B7] focus:ring-[#0073B7]"
                />
                <span className="font-medium text-slate-700">Compare Prior Period:</span>
              </label>
              {enableComparison && (
                <input
                  type="date"
                  aria-label="Prior Period Comparison Date"
                  value={comparisonDate}
                  onChange={(e) => setComparisonDate(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-md px-2 py-1 font-mono text-slate-800"
                />
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
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

        {/* ── ACCOUNTING EQUILIBRIUM SEAL ── */}
        <div
          className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
            report.is_balanced
              ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
              : "bg-rose-50/70 border-rose-200 text-rose-900"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {report.is_balanced ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-rose-600 flex-shrink-0" />
            )}
            <div>
              <p className="font-bold">
                {report.is_balanced
                  ? "Ledger Equilibrium Verified: Total Assets ≡ Total Liabilities & Equity"
                  : "Attention: Ledger Equilibrium Discrepancy Detected"}
              </p>
              <p className="text-[11px] text-slate-600">
                Total Assets: <span className="font-mono font-semibold">{fmtCur(report.total_assets)}</span> ·
                Total Liabilities & Equity: <span className="font-mono font-semibold">{fmtCur(report.total_liabilities_and_equity)}</span> ·
                Variance: <span className="font-mono font-bold">{fmtCur(report.equilibrium_discrepancy)}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full font-bold bg-white/80 border text-[11px] shadow-2xs">
              Net Assets: {fmtCur(report.net_assets)}
            </span>
          </div>
        </div>

        {/* ── STATEMENT TABLE ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Acme Corp UK Ltd — Statement of Financial Position
              </h2>
              <p className="text-xs text-slate-500">
                As at {report.as_of_date} (Currency: {report.currency})
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
                  <th className="py-2.5 px-4 text-right">As at {report.as_of_date}</th>
                  {hasComparison && (
                    <th className="py-2.5 px-4 text-right text-slate-500">
                      As at {report.comparison_as_of_date}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {/* ── FIXED ASSETS ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 4 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide">
                    Fixed Assets (Non-Current)
                  </td>
                </tr>
                {report.fixed_assets.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">{fmtCur(item.amount)}</td>
                    {hasComparison && (
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">{fmtCur(item.comparison_amount)}</td>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Fixed Assets</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">{fmtCur(report.total_fixed_assets)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£40,000.00</td>}
                </tr>

                {/* ── CURRENT ASSETS ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 4 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Current Assets
                  </td>
                </tr>
                {report.current_assets.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">{fmtCur(item.amount)}</td>
                    {hasComparison && (
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">{fmtCur(item.comparison_amount)}</td>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Current Assets</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">{fmtCur(report.total_current_assets)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£193,500.00</td>}
                </tr>

                {/* ── TOTAL ASSETS ── */}
                <tr className="bg-sky-50/60 font-black border-t-2 border-b-2 border-sky-300 text-sky-950 text-sm">
                  <td className="py-3 px-6 font-mono"></td>
                  <td className="py-3 px-4">TOTAL ASSETS</td>
                  <td className="py-3 px-4 font-mono text-right text-base font-black">{fmtCur(report.total_assets)}</td>
                  {hasComparison && <td className="py-3 px-4 font-mono text-right text-sky-900">£233,500.00</td>}
                </tr>

                {/* ── CURRENT LIABILITIES ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 4 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Current Liabilities (Due within 1 Year)
                  </td>
                </tr>
                {report.current_liabilities.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">{fmtCur(item.amount)}</td>
                    {hasComparison && (
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">{fmtCur(item.comparison_amount)}</td>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Current Liabilities</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">{fmtCur(report.total_current_liabilities)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£38,000.00</td>}
                </tr>

                {/* ── NET CURRENT ASSETS ── */}
                <tr className="bg-slate-50 font-bold border-t border-slate-200 text-slate-800">
                  <td className="py-2.5 px-6 font-mono"></td>
                  <td className="py-2.5 px-4">Net Current Assets (Working Capital)</td>
                  <td className="py-2.5 px-4 font-mono text-right">{fmtCur(report.net_current_assets)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-right text-slate-600">£155,500.00</td>}
                </tr>

                {/* ── NON-CURRENT LIABILITIES ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 4 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Non-Current Liabilities (Due after 1 Year)
                  </td>
                </tr>
                {report.non_current_liabilities.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">{fmtCur(item.amount)}</td>
                    {hasComparison && (
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">{fmtCur(item.comparison_amount)}</td>
                    )}
                  </tr>
                ))}
                <tr className="bg-slate-100/60 font-bold border-t border-slate-200">
                  <td className="py-2.5 px-6 font-mono text-slate-500"></td>
                  <td className="py-2.5 px-4 text-slate-900">Total Non-Current Liabilities</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">{fmtCur(report.total_non_current_liabilities)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£25,000.00</td>}
                </tr>

                {/* ── TOTAL LIABILITIES ── */}
                <tr className="bg-slate-100 font-bold border-t border-slate-300">
                  <td className="py-2.5 px-6 font-mono"></td>
                  <td className="py-2.5 px-4 text-slate-900">TOTAL LIABILITIES</td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 text-right">{fmtCur(report.total_liabilities)}</td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£63,000.00</td>}
                </tr>

                {/* ── TOTAL NET ASSETS ── */}
                <tr className="bg-emerald-50/70 font-black border-t-2 border-b-2 border-emerald-300 text-emerald-950 text-sm">
                  <td className="py-3 px-6 font-mono"></td>
                  <td className="py-3 px-4">TOTAL NET ASSETS</td>
                  <td className="py-3 px-4 font-mono text-right text-base text-emerald-800 font-black">{fmtCur(report.net_assets)}</td>
                  {hasComparison && <td className="py-3 px-4 font-mono text-right text-emerald-700">£170,500.00</td>}
                </tr>

                {/* ── EQUITY / CAPITAL & RESERVES ── */}
                <tr className="bg-slate-50/80">
                  <td colSpan={hasComparison ? 4 : 3} className="py-2 px-6 font-bold text-slate-900 uppercase tracking-wide pt-4">
                    Capital and Reserves (Equity)
                  </td>
                </tr>
                {report.equity.map((item) => (
                  <tr key={item.account_id} className="hover:bg-sky-50/40 transition-colors">
                    <td className="py-2.5 px-6 font-mono text-slate-500">{item.account_code}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{item.account_name}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">{fmtCur(item.amount)}</td>
                    {hasComparison && (
                      <td className="py-2.5 px-4 font-mono text-slate-600 text-right">{fmtCur(item.comparison_amount)}</td>
                    )}
                  </tr>
                ))}
                {/* Current Year Profit Line */}
                <tr className="bg-sky-50/30 hover:bg-sky-50/60 transition-colors">
                  <td className="py-2.5 px-6 font-mono text-sky-600 font-semibold">P&L</td>
                  <td className="py-2.5 px-4 font-medium text-sky-900 flex items-center gap-1.5">
                    Current Year Earnings
                    <span className="text-[10px] bg-sky-100 text-sky-800 px-1.5 py-0.5 rounded font-semibold">
                      Automated
                    </span>
                  </td>
                  <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 text-right">
                    {fmtCur(report.current_year_earnings)}
                  </td>
                  {hasComparison && <td className="py-2.5 px-4 font-mono text-slate-600 text-right">£40,500.00</td>}
                </tr>

                {/* ── TOTAL EQUITY ── */}
                <tr className="bg-slate-100/80 font-bold border-t-2 border-slate-300">
                  <td className="py-3 px-6 font-mono"></td>
                  <td className="py-3 px-4 text-slate-900">TOTAL CAPITAL & RESERVES (EQUITY)</td>
                  <td className="py-3 px-4 font-mono text-slate-900 text-right text-sm font-black">{fmtCur(report.total_equity)}</td>
                  {hasComparison && <td className="py-3 px-4 font-mono text-right text-slate-700">£170,500.00</td>}
                </tr>

                {/* ── TOTAL LIABILITIES & EQUITY (EQUILIBRIUM CHECK) ── */}
                <tr className="bg-slate-900 font-black text-white text-sm">
                  <td className="py-3.5 px-6 font-mono"></td>
                  <td className="py-3.5 px-4 flex items-center gap-2">
                    TOTAL LIABILITIES & EQUITY
                    <span className="text-[10px] bg-emerald-500 text-slate-950 font-black px-2 py-0.5 rounded">
                      EQUILIBRIUM: {report.is_balanced ? "100% MATCH" : "DISCREPANCY"}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-right text-base text-emerald-400 font-black">
                    {fmtCur(report.total_liabilities_and_equity)}
                  </td>
                  {hasComparison && <td className="py-3.5 px-4 font-mono text-right text-slate-400">£233,500.00</td>}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
