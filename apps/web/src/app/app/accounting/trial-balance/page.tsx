"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import {
  FileSpreadsheet,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  Printer,
  Download,
  ShieldCheck,
  Building,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface TrialBalanceLine {
  account_id: string;
  account_code: string;
  account_name: string;
  account_class: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  debit_balance: string | number;
  credit_balance: string | number;
}

interface TrialBalanceReport {
  as_of_date: string;
  generated_at: string;
  total_debit: string | number;
  total_credit: string | number;
  is_balanced: boolean;
  currency: string;
  lines: TrialBalanceLine[];
}

const DEMO_REPORT: TrialBalanceReport = {
  as_of_date: new Date().toISOString().split("T")[0],
  generated_at: new Date().toISOString(),
  total_debit: 116350.50,
  total_credit: 116350.50,
  is_balanced: true,
  currency: "GBP",
  lines: [
    { account_id: "1", account_code: "1000", account_name: "Operating Bank Account", account_class: "ASSET", debit_balance: 45200.50, credit_balance: 0 },
    { account_id: "2", account_code: "1100", account_name: "Accounts Receivable", account_class: "ASSET", debit_balance: 18450.00, credit_balance: 0 },
    { account_id: "3", account_code: "1200", account_name: "Prepayments & Accrued Income", account_class: "ASSET", debit_balance: 2400.00, credit_balance: 0 },
    { account_id: "4", account_code: "1500", account_name: "Office Equipment & Tech", account_class: "ASSET", debit_balance: 8500.00, credit_balance: 0 },
    { account_id: "5", account_code: "2000", account_name: "Accounts Payable", account_class: "LIABILITY", debit_balance: 0, credit_balance: 12100.00 },
    { account_id: "6", account_code: "2200", account_name: "VAT Output Tax", account_class: "LIABILITY", debit_balance: 0, credit_balance: 4560.00 },
    { account_id: "7", account_code: "2210", account_name: "PAYE & NI Payable", account_class: "LIABILITY", debit_balance: 0, credit_balance: 3120.00 },
    { account_id: "8", account_code: "3000", account_name: "Share Capital", account_class: "EQUITY", debit_balance: 0, credit_balance: 25000.00 },
    { account_id: "9", account_code: "3200", account_name: "Retained Earnings", account_class: "EQUITY", debit_balance: 0, credit_balance: 14770.50 },
    { account_id: "10", account_code: "4000", account_name: "General Consulting Sales", account_class: "REVENUE", debit_balance: 0, credit_balance: 42000.00 },
    { account_id: "11", account_code: "4100", account_name: "Software License Revenue", account_class: "REVENUE", debit_balance: 0, credit_balance: 14800.00 },
    { account_id: "12", account_code: "5000", account_name: "Direct Cost of Goods Sold", account_class: "EXPENSE", debit_balance: 12800.00, credit_balance: 0 },
    { account_id: "13", account_code: "6000", account_name: "Rent & Office Rates", account_class: "EXPENSE", debit_balance: 12000.00, credit_balance: 0 },
    { account_id: "14", account_code: "6100", account_name: "Salaries & Wages", account_class: "EXPENSE", debit_balance: 17000.00, credit_balance: 0 },
  ],
};

function fmtCur(amount: number | string | undefined, currency = "GBP") {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(num);
}

function TrialBalanceContent() {
  const [asOfDate, setAsOfDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [report, setReport] = useState<TrialBalanceReport>(DEMO_REPORT);
  const [loading, setLoading] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/ledger/trial-balance?as_of_date=${asOfDate}`, {
        headers,
      });

      if (res.ok) {
        const data = await res.json();
        if (data && data.lines) {
          setReport(data);
        }
      }
    } catch (err) {
      console.warn("Using demo trial balance report", err);
    } finally {
      setLoading(false);
    }
  }, [asOfDate]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handlePrint = () => {
    window.print();
  };

  const handleExportCSV = () => {
    const headers = ["Account Code", "Account Name", "Class", "Debit (£)", "Credit (£)"];
    const rows = report.lines.map((l) => [
      `"${l.account_code}"`,
      `"${l.account_name.replace(/"/g, '""')}"`,
      `"${l.account_class}"`,
      Number(l.debit_balance).toFixed(2),
      Number(l.credit_balance).toFixed(2),
    ]);
    rows.push([
      '"TOTAL"',
      '""',
      '""',
      Number(report.total_debit).toFixed(2),
      Number(report.total_credit).toFixed(2),
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Trial_Balance_${asOfDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Group lines by Class
  const classes: Array<"ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE"> = [
    "ASSET",
    "LIABILITY",
    "EQUITY",
    "REVENUE",
    "EXPENSE",
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-12 print:p-0 print:m-0">
        {/* Report Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5 print:hidden">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-sky-100 text-[#0073B7]">
                <FileSpreadsheet className="h-5 w-5" />
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Trial Balance</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              General ledger summary verifying total debits equal total credits across all account classes.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-white px-2.5 py-1.5 rounded-md border border-slate-300 text-xs shadow-2xs">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              <span className="text-slate-500 font-medium">As of:</span>
              <input
                type="date"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                className="font-medium text-slate-900 focus:outline-none"
              />
            </div>

            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-all"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              Export CSV
            </button>

            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Printer className="h-3.5 w-3.5" />
              Print Report
            </button>
          </div>
        </div>

        {/* Official Accounting Integrity Badge */}
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {report.is_balanced ? (
              <div className="h-9 w-9 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
                <ShieldCheck className="h-5 w-5" />
              </div>
            ) : (
              <div className="h-9 w-9 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">
                  {report.is_balanced ? "Double-Entry Balance Verified" : "Ledger Out of Balance"}
                </span>
                <span className={`text-[10px] px-2 py-0.2 rounded font-mono font-bold ${report.is_balanced ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                  {report.is_balanced ? "STATUS: BALANCED" : "STATUS: UNBALANCED"}
                </span>
              </div>
              <div className="text-[11px] text-slate-500">
                Σ Debits ({fmtCur(report.total_debit)}) = Σ Credits ({fmtCur(report.total_credit)}) · Generated {new Date(report.generated_at).toLocaleTimeString("en-GB")}
              </div>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-mono text-slate-400">Precision: Exact Decimal (NUMERIC 19,4)</span>
          </div>
        </div>

        {/* Printable Report Document */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden p-6 print:border-none print:shadow-none">
          {/* Printable Header */}
          <div className="border-b border-slate-200 pb-4 mb-6 text-center">
            <h2 className="text-lg font-bold text-slate-900 uppercase tracking-wide">Trial Balance Report</h2>
            <p className="text-xs text-slate-500">As at {asOfDate} · Currency: {report.currency}</p>
          </div>

          <table className="w-full text-left text-xs text-slate-600">
            <thead className="border-b-2 border-slate-800 text-[11px] font-bold uppercase text-slate-800 tracking-wider">
              <tr>
                <th className="py-2.5 px-3 w-24">Code</th>
                <th className="py-2.5 px-3">Account Name</th>
                <th className="py-2.5 px-3 w-32">Class</th>
                <th className="py-2.5 px-3 text-right w-36">Debit ({report.currency})</th>
                <th className="py-2.5 px-3 text-right w-36">Credit ({report.currency})</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {classes.map((cls) => {
                const classLines = report.lines.filter((l) => l.account_class === cls);
                if (classLines.length === 0) return null;

                const classDebit = classLines.reduce((s, l) => s + (parseFloat(String(l.debit_balance)) || 0), 0);
                const classCredit = classLines.reduce((s, l) => s + (parseFloat(String(l.credit_balance)) || 0), 0);

                return (
                  <React.Fragment key={cls}>
                    {/* Section Header */}
                    <tr className="bg-slate-50/70 font-bold text-slate-800">
                      <td colSpan={3} className="py-2 px-3 tracking-wide">
                        {cls} ACCOUNTS
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-[11px] text-slate-500">
                        {classDebit > 0 ? fmtCur(classDebit) : "—"}
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-[11px] text-slate-500">
                        {classCredit > 0 ? fmtCur(classCredit) : "—"}
                      </td>
                    </tr>

                    {/* Account Rows */}
                    {classLines.map((line) => (
                      <tr key={line.account_id} className="hover:bg-slate-50/40">
                        <td className="py-2 px-3 font-mono font-bold text-slate-800 pl-6">{line.account_code}</td>
                        <td className="py-2 px-3 text-slate-900 font-medium">{line.account_name}</td>
                        <td className="py-2 px-3 text-slate-400 text-[11px] font-mono">{line.account_class}</td>
                        <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                          {Number(line.debit_balance) > 0 ? fmtCur(line.debit_balance) : "—"}
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                          {Number(line.credit_balance) > 0 ? fmtCur(line.credit_balance) : "—"}
                        </td>
                      </tr>
                    ))}
                  </React.Fragment>
                );
              })}
            </tbody>

            {/* Grand Total Footer (Double Underline Standard Accounting Line) */}
            <tfoot className="border-t-2 border-b-4 border-slate-900 font-bold text-slate-900 text-xs">
              <tr>
                <td colSpan={3} className="py-3 px-3 uppercase tracking-wider font-extrabold text-slate-900">
                  Total Trial Balance
                </td>
                <td className="py-3 px-3 text-right font-mono font-extrabold text-sm text-slate-900">
                  {fmtCur(report.total_debit)}
                </td>
                <td className="py-3 px-3 text-right font-mono font-extrabold text-sm text-slate-900">
                  {fmtCur(report.total_credit)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function TrialBalancePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Trial Balance...</div>}>
      <TrialBalanceContent />
    </Suspense>
  );
}
