"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import {
  Lock,
  Unlock,
  Calendar,
  ShieldAlert,
  Plus,
  Save,
  CheckCircle2,
  AlertCircle,
  Clock,
  Settings2,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface AccountingSettings {
  lock_date?: string;
  financial_year_end_month: number;
  financial_year_end_day: number;
  allow_prior_period_posting: boolean;
}

interface FinancialPeriod {
  id: string;
  period_name: string;
  start_date: string;
  end_date: string;
  is_locked: boolean;
  locked_at?: string;
  lock_reason?: string;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const DEMO_PERIODS: FinancialPeriod[] = [
  {
    id: "p1",
    period_name: "FY 2025 Annual Closed",
    start_date: "2025-01-01",
    end_date: "2025-12-31",
    is_locked: true,
    locked_at: "2026-01-15T18:00:00Z",
    lock_reason: "Statutory year-end accounts filed with Companies House & HMRC",
  },
  {
    id: "p2",
    period_name: "Q1 2026",
    start_date: "2026-01-01",
    end_date: "2026-03-31",
    is_locked: false,
  },
  {
    id: "p3",
    period_name: "Q2 2026",
    start_date: "2026-04-01",
    end_date: "2026-06-30",
    is_locked: false,
  },
];

function AccountingPeriodsContent() {
  const [settings, setSettings] = useState<AccountingSettings>({
    lock_date: "2025-12-31",
    financial_year_end_month: 3,
    financial_year_end_day: 31,
    allow_prior_period_posting: false,
  });
  const [periods, setPeriods] = useState<FinancialPeriod[]>(DEMO_PERIODS);
  const [loading, setLoading] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // New Period Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [newPeriodData, setNewPeriodData] = useState({
    period_name: "",
    start_date: "",
    end_date: "",
    is_locked: false,
    lock_reason: "",
  });
  const [submittingPeriod, setSubmittingPeriod] = useState(false);
  const [periodError, setPeriodError] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // Settings
      const resSet = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounting/settings`, { headers });
      if (resSet.ok) {
        const s = await resSet.json();
        setSettings(s);
      }

      // Periods
      const resPer = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounting/periods`, { headers });
      if (resPer.ok) {
        const p = await resPer.json();
        if (p && p.length > 0) {
          setPeriods(p);
        }
      }
    } catch (err) {
      console.warn("Using demo periods data", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setSettingsSuccess(false);

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounting/settings`, {
        method: "PUT",
        headers,
        body: JSON.stringify(settings),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update accounting settings");
      }

      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
    } catch (err: any) {
      alert(err.message || "Failed to save settings");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleToggleLock = async (period: FinancialPeriod) => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounting/periods/${period.id}/lock`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          is_locked: !period.is_locked,
          lock_reason: !period.is_locked ? "Closed by Accountant" : undefined,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to toggle period lock");
      }

      await fetchData();
    } catch (err: any) {
      alert(err.message || "Failed to update period lock status");
    }
  };

  const handleCreatePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingPeriod(true);
    setPeriodError("");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounting/periods`, {
        method: "POST",
        headers,
        body: JSON.stringify(newPeriodData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create financial period");
      }

      setModalOpen(false);
      setNewPeriodData({
        period_name: "",
        start_date: "",
        end_date: "",
        is_locked: false,
        lock_reason: "",
      });
      await fetchData();
    } catch (err: any) {
      setPeriodError(err.message || "Failed to create period");
    } finally {
      setSubmittingPeriod(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-6 pb-12">
        {/* Header */}
        <div className="border-b border-slate-200 pb-5">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-sky-100 text-[#0073B7]">
              <Lock className="h-5 w-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Financial Periods & Period Locking</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Prevent accidental or unauthorized journal entries, invoices, and bills into closed fiscal periods.
          </p>
        </div>

        {/* Global Period Lock Date Settings Form */}
        <form onSubmit={handleSaveSettings} className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-[#0073B7]" />
              Global Ledger Lock Settings
            </h2>
            {settingsSuccess && (
              <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" /> Settings Saved!
              </span>
            )}
          </div>

          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3 text-xs text-amber-800">
            <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Accounting Invariant: Strict Period Locking</p>
              <p className="mt-0.5 text-amber-700">
                Any journal entry, sales invoice, supplier bill, or payment dated on or before the Lock Date is strictly blocked with HTTP 422 Unprocessable Content. Only an authorised Accountant or Owner may alter this date.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Global Lock Date (All Users Blocked Prior to Date)
              </label>
              <input
                type="date"
                value={settings.lock_date || ""}
                onChange={(e) => setSettings({ ...settings, lock_date: e.target.value || undefined })}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Leave blank to allow transactions at any historic date.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Financial Year End Month
              </label>
              <select
                value={settings.financial_year_end_month}
                onChange={(e) => setSettings({ ...settings, financial_year_end_month: parseInt(e.target.value) })}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none bg-white"
              >
                {MONTH_NAMES.map((m, idx) => (
                  <option key={idx + 1} value={idx + 1}>
                    {m} (e.g. Month {idx + 1})
                  </option>
                ))}
              </select>
              <span className="text-[11px] text-slate-400 mt-1 block">
                Default UK statutory financial year end is March (Month 3).
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end">
            <button
              type="submit"
              disabled={savingSettings}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {savingSettings ? "Saving..." : "Save Lock Settings"}
            </button>
          </div>
        </form>

        {/* Defined Financial Periods List */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Defined Financial Periods</h2>
              <p className="text-[11px] text-slate-500">Lock specific months or quarters individually</p>
            </div>

            <button
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Period
            </button>
          </div>

          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-100/70 border-b border-slate-200 text-[10px] font-semibold uppercase text-slate-500">
              <tr>
                <th className="py-2.5 px-4">Period Name</th>
                <th className="py-2.5 px-4 w-32">Start Date</th>
                <th className="py-2.5 px-4 w-32">End Date</th>
                <th className="py-2.5 px-4 w-32 text-center">Status</th>
                <th className="py-2.5 px-4">Lock Details</th>
                <th className="py-2.5 px-4 text-right w-28">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {periods.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/50">
                  <td className="py-3 px-4 font-semibold text-slate-900">{p.period_name}</td>
                  <td className="py-3 px-4 font-mono text-slate-600">{p.start_date}</td>
                  <td className="py-3 px-4 font-mono text-slate-600">{p.end_date}</td>
                  <td className="py-3 px-4 text-center">
                    {p.is_locked ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                        <Lock className="h-2.5 w-2.5" /> LOCKED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <Unlock className="h-2.5 w-2.5" /> OPEN
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {p.is_locked ? (
                      <div className="text-[11px] text-slate-500">
                        <span className="font-medium text-slate-700">{p.lock_reason || "Period closed"}</span>
                        {p.locked_at && <span className="text-slate-400 block font-mono text-[10px]">At {new Date(p.locked_at).toLocaleDateString("en-GB")}</span>}
                      </div>
                    ) : (
                      <span className="text-slate-400 text-[11px]">Unrestricted posting</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleToggleLock(p)}
                      className={`px-2.5 py-1 rounded text-xs font-semibold transition-colors border ${
                        p.is_locked
                          ? "bg-white hover:bg-slate-50 text-slate-700 border-slate-300"
                          : "bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200"
                      }`}
                    >
                      {p.is_locked ? "Unlock" : "Lock Period"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Add Financial Period Modal */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-sm">Create Financial Period</h3>
                <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
              </div>

              <form onSubmit={handleCreatePeriod} className="p-6 space-y-4 text-xs">
                {periodError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-md flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{periodError}</span>
                  </div>
                )}

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Period Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Q3 2026"
                    value={newPeriodData.period_name}
                    onChange={(e) => setNewPeriodData({ ...newPeriodData, period_name: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Start Date</label>
                    <input
                      type="date"
                      required
                      value={newPeriodData.start_date}
                      onChange={(e) => setNewPeriodData({ ...newPeriodData, start_date: e.target.value })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">End Date</label>
                    <input
                      type="date"
                      required
                      value={newPeriodData.end_date}
                      onChange={(e) => setNewPeriodData({ ...newPeriodData, end_date: e.target.value })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="is_locked"
                    checked={newPeriodData.is_locked}
                    onChange={(e) => setNewPeriodData({ ...newPeriodData, is_locked: e.target.checked })}
                    className="h-4 w-4 rounded text-[#0073B7] focus:ring-[#0073B7]"
                  />
                  <label htmlFor="is_locked" className="font-semibold text-slate-700 cursor-pointer">
                    Immediately lock this period
                  </label>
                </div>

                {newPeriodData.is_locked && (
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Lock Reason</label>
                    <input
                      type="text"
                      placeholder="e.g. Accounts signed off"
                      value={newPeriodData.lock_reason}
                      onChange={(e) => setNewPeriodData({ ...newPeriodData, lock_reason: e.target.value })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </div>
                )}

                <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="px-3 py-1.5 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingPeriod}
                    className="px-4 py-1.5 bg-[#0073B7] hover:bg-[#005f96] text-white font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
                  >
                    {submittingPeriod ? "Creating..." : "Create Period"}
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

export default function AccountingPeriodsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Period Settings...</div>}>
      <AccountingPeriodsContent />
    </Suspense>
  );
}
