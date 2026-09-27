"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Users,
  Calendar,
  Download,
  Printer,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  Clock,
  ArrowUpRight,
  ShieldCheck,
  FileText,
  Building,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface AgedItemDetail {
  document_id: string;
  document_number: string;
  reference?: string | null;
  issue_date: string;
  due_date: string;
  days_overdue: number;
  total_amount: number | string;
  paid_amount: number | string;
  remaining_balance: number | string;
  bucket: "CURRENT" | "DAYS_1_30" | "DAYS_31_60" | "DAYS_61_90" | "DAYS_OVER_90";
}

interface AgedContactSummary {
  contact_id: string;
  contact_name: string;
  company_number?: string | null;
  currency: string;
  current: number | string;
  days_1_30: number | string;
  days_31_60: number | string;
  days_61_90: number | string;
  days_over_90: number | string;
  total: number | string;
  items: AgedItemDetail[];
}

interface AgedReportSummaryBuckets {
  current: number | string;
  days_1_30: number | string;
  days_31_60: number | string;
  days_61_90: number | string;
  days_over_90: number | string;
  grand_total: number | string;
}

interface AgedReportResponse {
  report_type: "RECEIVABLES" | "PAYABLES";
  as_of_date: string;
  contacts: AgedContactSummary[];
  totals: AgedReportSummaryBuckets;
  currency: string;
  generated_at: string;
}

const DEMO_AGED_RECEIVABLES: AgedReportResponse = {
  report_type: "RECEIVABLES",
  as_of_date: "2026-03-31",
  totals: {
    current: "22680.00",
    days_1_30: "1500.00",
    days_31_60: "3000.00",
    days_61_90: "1200.00",
    days_over_90: "770.00",
    grand_total: "29150.00",
  },
  contacts: [
    {
      contact_id: "c1",
      contact_name: "Apex Commercial Client Ltd",
      company_number: "08812345",
      currency: "GBP",
      current: "12000.00",
      days_1_30: "1500.00",
      days_31_60: "3000.00",
      days_61_90: "0.00",
      days_over_90: "0.00",
      total: "16500.00",
      items: [
        {
          document_id: "inv-1",
          document_number: "INV-2026-0089",
          reference: "PO-APEX-992",
          issue_date: "2026-03-01",
          due_date: "2026-04-15",
          days_overdue: 0,
          total_amount: "12000.00",
          paid_amount: "0.00",
          remaining_balance: "12000.00",
          bucket: "CURRENT",
        },
        {
          document_id: "inv-2",
          document_number: "INV-2026-0072",
          reference: "Consulting Phase 1",
          issue_date: "2026-02-15",
          due_date: "2026-03-16",
          days_overdue: 15,
          total_amount: "2000.00",
          paid_amount: "500.00",
          remaining_balance: "1500.00",
          bucket: "DAYS_1_30",
        },
        {
          document_id: "inv-3",
          document_number: "INV-2026-0044",
          reference: "System Integration",
          issue_date: "2026-01-15",
          due_date: "2026-02-14",
          days_overdue: 45,
          total_amount: "3000.00",
          paid_amount: "0.00",
          remaining_balance: "3000.00",
          bucket: "DAYS_31_60",
        },
      ],
    },
    {
      contact_id: "c2",
      contact_name: "Beacon Tech Solutions Plc",
      company_number: "11223344",
      currency: "GBP",
      current: "10680.00",
      days_1_30: "0.00",
      days_31_60: "0.00",
      days_61_90: "1200.00",
      days_over_90: "770.00",
      total: "12650.00",
      items: [
        {
          document_id: "inv-4",
          document_number: "INV-2026-0095",
          reference: "Q1 Retainer",
          issue_date: "2026-03-10",
          due_date: "2026-04-10",
          days_overdue: 0,
          total_amount: "10680.00",
          paid_amount: "0.00",
          remaining_balance: "10680.00",
          bucket: "CURRENT",
        },
        {
          document_id: "inv-5",
          document_number: "INV-2025-0199",
          reference: "Old Services Balance",
          issue_date: "2025-11-20",
          due_date: "2025-12-20",
          days_overdue: 101,
          total_amount: "770.00",
          paid_amount: "0.00",
          remaining_balance: "770.00",
          bucket: "DAYS_OVER_90",
        },
      ],
    },
  ],
  currency: "GBP",
  generated_at: new Date().toISOString(),
};

function fmtCur(amount: number | string | undefined | null, currency = "GBP") {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(num);
}

export default function AgedReceivablesPage() {
  const [asOfDate, setAsOfDate] = useState("2026-03-31");
  const [report, setReport] = useState<AgedReportResponse>(DEMO_AGED_RECEIVABLES);
  const [loading, setLoading] = useState(false);
  const [expandedContacts, setExpandedContacts] = useState<Record<string, boolean>>({ c1: true });

  const toggleContact = (id: string) => {
    setExpandedContacts((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${ORG_ID}/reports/aged-receivables?as_of_date=${asOfDate}`,
        { headers }
      );
      if (res.ok) {
        const data = await res.json();
        if (data && data.totals !== undefined) {
          setReport(data);
        }
      }
    } catch (err) {
      console.warn("Using demo aged receivables data", err);
    } finally {
      setLoading(false);
    }
  }, [asOfDate]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExportCSV = () => {
    const rows = [
      ["Aged Receivables (Debtors Aging Schedule)"],
      [`As of Date: ${report.as_of_date}`],
      [`Currency: ${report.currency}`],
      [],
      ["Customer Name", "Company Number", "Current (£)", "1-30 Days (£)", "31-60 Days (£)", "61-90 Days (£)", ">90 Days (£)", "Total (£)"],
      ...report.contacts.map((c) => [
        `"${c.contact_name.replace(/"/g, '""')}"`,
        c.company_number || "",
        Number(c.current).toFixed(2),
        Number(c.days_1_30).toFixed(2),
        Number(c.days_31_60).toFixed(2),
        Number(c.days_61_90).toFixed(2),
        Number(c.days_over_90).toFixed(2),
        Number(c.total).toFixed(2),
      ]),
      [
        '"GRAND TOTAL"',
        '""',
        Number(report.totals.current).toFixed(2),
        Number(report.totals.days_1_30).toFixed(2),
        Number(report.totals.days_31_60).toFixed(2),
        Number(report.totals.days_61_90).toFixed(2),
        Number(report.totals.days_over_90).toFixed(2),
        Number(report.totals.grand_total).toFixed(2),
      ],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `aged_receivables_as_of_${report.as_of_date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
              <span className="text-slate-800">Aged Receivables</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <Users className="h-6 w-6 text-blue-600" />
              Aged Receivables (Debtors Aging Schedule)
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Itemised debtor tracking categorized by due-date brackets with partial payment tracking.
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
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-600">As of Date:</span>
            <input
              type="date"
              aria-label="As of Date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-md px-2.5 py-1.5 font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchReport}
              disabled={loading}
              className="p-1.5 rounded-md hover:bg-slate-100 text-slate-600 transition-colors"
              title="Refresh Schedule"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-[#0073B7]" : ""}`} />
            </button>
          </div>
        </div>

        {/* ── AGING BUCKETS METRIC CARDS ── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Current</span>
            <div className="mt-1">
              <span className="text-lg font-bold font-mono text-emerald-600">
                {fmtCur(report.totals.current)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Not yet due</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">1 - 30 Days</span>
            <div className="mt-1">
              <span className="text-lg font-bold font-mono text-amber-600">
                {fmtCur(report.totals.days_1_30)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Overdue 1-30d</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">31 - 60 Days</span>
            <div className="mt-1">
              <span className="text-lg font-bold font-mono text-orange-600">
                {fmtCur(report.totals.days_31_60)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Follow up required</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">61 - 90 Days</span>
            <div className="mt-1">
              <span className="text-lg font-bold font-mono text-rose-600">
                {fmtCur(report.totals.days_61_90)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Critical overdue</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">&gt; 90 Days</span>
            <div className="mt-1">
              <span className="text-lg font-bold font-mono text-purple-700">
                {fmtCur(report.totals.days_over_90)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Doubtful balance</p>
          </div>

          <div className="bg-slate-900 text-white rounded-xl border border-slate-800 p-3.5 shadow-sm">
            <span className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider">Grand Total</span>
            <div className="mt-1">
              <span className="text-lg font-black font-mono text-sky-400">
                {fmtCur(report.totals.grand_total)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">Total outstanding</p>
          </div>
        </div>

        {/* ── AGING SCHEDULE TABLE ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Customer Aging Analysis & Invoice Breakdown
              </h2>
              <p className="text-xs text-slate-500">
                Click any customer row to expand and inspect specific unpaid invoices and payment allocations
              </p>
            </div>
            <span className="text-[11px] font-medium text-slate-400">
              {report.contacts.length} Customers with balances
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-6">Customer</th>
                  <th className="py-2.5 px-4 text-right">Current</th>
                  <th className="py-2.5 px-4 text-right">1 - 30 Days</th>
                  <th className="py-2.5 px-4 text-right">31 - 60 Days</th>
                  <th className="py-2.5 px-4 text-right">61 - 90 Days</th>
                  <th className="py-2.5 px-4 text-right">&gt; 90 Days</th>
                  <th className="py-2.5 px-6 text-right font-black">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.contacts.map((contact) => {
                  const isExpanded = !!expandedContacts[contact.contact_id];
                  return (
                    <React.Fragment key={contact.contact_id}>
                      <tr
                        onClick={() => toggleContact(contact.contact_id)}
                        className="hover:bg-sky-50/50 cursor-pointer transition-colors group"
                      >
                        <td className="py-3 px-6">
                          <div className="flex items-center gap-2">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4 text-[#0073B7]" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-slate-700" />
                            )}
                            <div>
                              <span className="font-bold text-slate-900 group-hover:text-[#0073B7]">
                                {contact.contact_name}
                              </span>
                              {contact.company_number && (
                                <span className="ml-2 text-[10px] text-slate-400 font-mono">
                                  #{contact.company_number}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-right text-slate-700">
                          {fmtCur(contact.current)}
                        </td>
                        <td className="py-3 px-4 font-mono text-right text-slate-700">
                          {fmtCur(contact.days_1_30)}
                        </td>
                        <td className="py-3 px-4 font-mono text-right text-slate-700">
                          {fmtCur(contact.days_31_60)}
                        </td>
                        <td className="py-3 px-4 font-mono text-right text-slate-700">
                          {fmtCur(contact.days_61_90)}
                        </td>
                        <td className="py-3 px-4 font-mono text-right text-slate-700">
                          {fmtCur(contact.days_over_90)}
                        </td>
                        <td className="py-3 px-6 font-mono text-right font-black text-slate-900">
                          {fmtCur(contact.total)}
                        </td>
                      </tr>

                      {/* Expandable Invoice Drill-Down */}
                      {isExpanded && (
                        <tr className="bg-slate-50/80">
                          <td colSpan={7} className="py-3 px-8">
                            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
                              <table className="w-full text-left text-[11px]">
                                <thead className="bg-slate-100/80 text-slate-500 font-semibold border-b border-slate-200">
                                  <tr>
                                    <th className="py-2 px-4">Invoice #</th>
                                    <th className="py-2 px-3">Reference</th>
                                    <th className="py-2 px-3">Issue Date</th>
                                    <th className="py-2 px-3">Due Date</th>
                                    <th className="py-2 px-3">Overdue</th>
                                    <th className="py-2 px-3 text-right">Total Gross</th>
                                    <th className="py-2 px-3 text-right">Paid</th>
                                    <th className="py-2 px-4 text-right font-bold">Remaining</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                  {contact.items.map((inv) => (
                                    <tr key={inv.document_id} className="hover:bg-slate-50">
                                      <td className="py-2 px-4 font-mono font-semibold text-[#0073B7]">
                                        <Link href={`/app/sales/invoices`}>
                                          {inv.document_number}
                                        </Link>
                                      </td>
                                      <td className="py-2 px-3 text-slate-600">{inv.reference || "—"}</td>
                                      <td className="py-2 px-3 font-mono text-slate-500">{inv.issue_date}</td>
                                      <td className="py-2 px-3 font-mono text-slate-500">{inv.due_date}</td>
                                      <td className="py-2 px-3">
                                        {inv.days_overdue > 0 ? (
                                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                                            {inv.days_overdue} days
                                          </span>
                                        ) : (
                                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                            Current
                                          </span>
                                        )}
                                      </td>
                                      <td className="py-2 px-3 font-mono text-slate-600 text-right">
                                        {fmtCur(inv.total_amount)}
                                      </td>
                                      <td className="py-2 px-3 font-mono text-slate-600 text-right">
                                        {fmtCur(inv.paid_amount)}
                                      </td>
                                      <td className="py-2 px-4 font-mono text-right font-bold text-slate-900">
                                        {fmtCur(inv.remaining_balance)}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}

                {/* ── GRAND TOTALS FOOTER ── */}
                <tr className="bg-slate-100/90 font-black border-t-2 border-slate-300 text-slate-900 text-xs">
                  <td className="py-3 px-6 uppercase tracking-wider">GRAND TOTAL</td>
                  <td className="py-3 px-4 font-mono text-right text-emerald-700">
                    {fmtCur(report.totals.current)}
                  </td>
                  <td className="py-3 px-4 font-mono text-right text-amber-700">
                    {fmtCur(report.totals.days_1_30)}
                  </td>
                  <td className="py-3 px-4 font-mono text-right text-orange-700">
                    {fmtCur(report.totals.days_31_60)}
                  </td>
                  <td className="py-3 px-4 font-mono text-right text-rose-700">
                    {fmtCur(report.totals.days_61_90)}
                  </td>
                  <td className="py-3 px-4 font-mono text-right text-purple-800">
                    {fmtCur(report.totals.days_over_90)}
                  </td>
                  <td className="py-3 px-6 font-mono text-right text-sm text-slate-950">
                    {fmtCur(report.totals.grand_total)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
