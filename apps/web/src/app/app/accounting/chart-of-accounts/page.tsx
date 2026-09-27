"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Lock,
  Sparkles,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Building,
  RefreshCw,
  AlertCircle,
  FolderTree,
  FileSpreadsheet,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface Account {
  id: string;
  code: string;
  name: string;
  account_class: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  subtype: string;
  currency: string;
  description?: string;
  is_active: boolean;
  is_system: boolean;
  normal_balance: "DEBIT" | "CREDIT";
  current_balance: string | number;
}

const CLASS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ASSET: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  LIABILITY: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  EQUITY: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  REVENUE: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  EXPENSE: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
};

const DEMO_ACCOUNTS: Account[] = [
  { id: "1", code: "1000", name: "Operating Bank Account", account_class: "ASSET", subtype: "BANK", currency: "GBP", is_active: true, is_system: true, normal_balance: "DEBIT", current_balance: 45200.50 },
  { id: "2", code: "1100", name: "Accounts Receivable", account_class: "ASSET", subtype: "CURRENT_ASSET", currency: "GBP", is_active: true, is_system: true, normal_balance: "DEBIT", current_balance: 18450.00 },
  { id: "3", code: "1200", name: "Prepayments & Accrued Income", account_class: "ASSET", subtype: "PREPAYMENT", currency: "GBP", is_active: true, is_system: false, normal_balance: "DEBIT", current_balance: 2400.00 },
  { id: "4", code: "1500", name: "Office Equipment & Tech", account_class: "ASSET", subtype: "FIXED_ASSET", currency: "GBP", is_active: true, is_system: false, normal_balance: "DEBIT", current_balance: 8500.00 },
  { id: "5", code: "2000", name: "Accounts Payable", account_class: "LIABILITY", subtype: "CURRENT_LIABILITY", currency: "GBP", is_active: true, is_system: true, normal_balance: "CREDIT", current_balance: 12100.00 },
  { id: "6", code: "2200", name: "VAT Output Tax", account_class: "LIABILITY", subtype: "TAX_LIABILITY", currency: "GBP", is_active: true, is_system: true, normal_balance: "CREDIT", current_balance: 4560.00 },
  { id: "7", code: "2210", name: "PAYE & National Insurance Payable", account_class: "LIABILITY", subtype: "TAX_LIABILITY", currency: "GBP", is_active: true, is_system: false, normal_balance: "CREDIT", current_balance: 3120.00 },
  { id: "8", code: "3000", name: "Owner's Equity & Share Capital", account_class: "EQUITY", subtype: "EQUITY", currency: "GBP", is_active: true, is_system: false, normal_balance: "CREDIT", current_balance: 25000.00 },
  { id: "9", code: "3200", name: "Retained Earnings", account_class: "EQUITY", subtype: "RETAINED_EARNINGS", currency: "GBP", is_active: true, is_system: true, normal_balance: "CREDIT", current_balance: 14770.50 },
  { id: "10", code: "4000", name: "General Consulting Sales", account_class: "REVENUE", subtype: "OPERATING_REVENUE", currency: "GBP", is_active: true, is_system: false, normal_balance: "CREDIT", current_balance: 68400.00 },
  { id: "11", code: "4100", name: "Software License Revenue", account_class: "REVENUE", subtype: "OPERATING_REVENUE", currency: "GBP", is_active: true, is_system: false, normal_balance: "CREDIT", current_balance: 15200.00 },
  { id: "12", code: "5000", name: "Direct Cost of Goods Sold", account_class: "EXPENSE", subtype: "COST_OF_GOODS_SOLD", currency: "GBP", is_active: true, is_system: false, normal_balance: "DEBIT", current_balance: 19800.00 },
  { id: "13", code: "6000", name: "Rent & Office Rates", account_class: "EXPENSE", subtype: "OPERATING_EXPENSE", currency: "GBP", is_active: true, is_system: false, normal_balance: "DEBIT", current_balance: 12000.00 },
  { id: "14", code: "6100", name: "Salaries & Wages", account_class: "EXPENSE", subtype: "OPERATING_EXPENSE", currency: "GBP", is_active: true, is_system: false, normal_balance: "DEBIT", current_balance: 33800.00 },
];

function fmtCur(amount: number | string | undefined, currency = "GBP") {
  if (amount === undefined || amount === null) return "£0.00";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(num);
}

function ChartOfAccountsContent() {
  const [accounts, setAccounts] = useState<Account[]>(DEMO_ACCOUNTS);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [seeding, setSeeding] = useState(false);
  const [seedSuccess, setSeedSuccess] = useState(false);

  // New Account Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    code: "",
    name: "",
    account_class: "ASSET",
    subtype: "CURRENT_ASSET",
    currency: "GBP",
    description: "",
    normal_balance: "DEBIT",
  });
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      let url = `${API_BASE}/api/v1/organisations/${ORG_ID}/accounts`;
      if (activeTab !== "ALL") url += `?account_class=${activeTab}`;

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          setAccounts(data);
        }
      }
    } catch (err) {
      console.warn("Using offline demo COA list", err);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleSeedStandard = async () => {
    setSeeding(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounts/seed-standard`, {
        method: "POST",
        headers,
      });
      if (res.ok) {
        setSeedSuccess(true);
        setTimeout(() => setSeedSuccess(false), 3000);
        await fetchAccounts();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSeeding(false);
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg("");
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounts`, {
        method: "POST",
        headers,
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create account");
      }

      setModalOpen(false);
      setFormData({
        code: "",
        name: "",
        account_class: "ASSET",
        subtype: "CURRENT_ASSET",
        currency: "GBP",
        description: "",
        normal_balance: "DEBIT",
      });
      await fetchAccounts();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create account");
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = accounts.filter((a) => {
    if (activeTab !== "ALL" && a.account_class !== activeTab) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return a.code.toLowerCase().includes(q) || a.name.toLowerCase().includes(q) || a.subtype.toLowerCase().includes(q);
  });

  const counts = {
    ALL: accounts.length,
    ASSET: accounts.filter((a) => a.account_class === "ASSET").length,
    LIABILITY: accounts.filter((a) => a.account_class === "LIABILITY").length,
    EQUITY: accounts.filter((a) => a.account_class === "EQUITY").length,
    REVENUE: accounts.filter((a) => a.account_class === "REVENUE").length,
    EXPENSE: accounts.filter((a) => a.account_class === "EXPENSE").length,
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header Title & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-sky-100 text-[#0073B7]">
                <BookOpen className="h-5 w-5" />
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Chart of Accounts</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              General ledger master accounts for double-entry bookkeeping, financial statements, and tax compliance.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSeedStandard}
              disabled={seeding}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-sky-600 ${seeding ? "animate-spin" : ""}`} />
              {seedSuccess ? "Standard Seeded!" : "Seed UK GAAP Template"}
            </button>

            <button
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="h-4 w-4" />
              Add Account
            </button>
          </div>
        </div>

        {/* Filter Tabs & Search Controls */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
          {/* Class Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0 text-xs">
            {(["ALL", "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                  activeTab === tab
                    ? "bg-[#0073B7] text-white font-semibold shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                <span>{tab === "ALL" ? "All Accounts" : tab.charAt(0) + tab.slice(1).toLowerCase() + "s"}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    activeTab === tab ? "bg-white/20 text-white" : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {counts[tab]}
                </span>
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search code, name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-md bg-slate-50 border border-slate-200 text-slate-900 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-[#0073B7] transition-all"
            />
          </div>
        </div>

        {/* Ledger Table */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
              <tr>
                <th className="py-3 px-4 w-20">Code</th>
                <th className="py-3 px-4">Account Name</th>
                <th className="py-3 px-4 w-32">Class</th>
                <th className="py-3 px-4 w-40">Subtype</th>
                <th className="py-3 px-4 w-24">Balance Side</th>
                <th className="py-3 px-4 text-right w-36">Current Balance</th>
                <th className="py-3 px-4 text-center w-24">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <FolderTree className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    No accounts found matching your filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((acc) => {
                  const style = CLASS_COLORS[acc.account_class] || { bg: "bg-slate-50", text: "text-slate-700", border: "border-slate-200" };
                  return (
                    <tr key={acc.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">{acc.code}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{acc.name}</div>
                        {acc.description && <div className="text-[11px] text-slate-400">{acc.description}</div>}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${style.bg} ${style.text} ${style.border}`}>
                          {acc.account_class}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                        {acc.subtype.replace(/_/g, " ")}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-700">
                        {acc.normal_balance}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        {fmtCur(acc.current_balance, acc.currency)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {acc.is_system ? (
                          <span
                            title="System account - core automated transactions post here"
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold"
                          >
                            <Lock className="h-2.5 w-2.5" /> System
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Custom</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Create Account Modal */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-sm">Add New Account</h3>
                <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
              </div>

              <form onSubmit={handleCreateAccount} className="p-6 space-y-4 text-xs">
                {errorMsg && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-md flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Account Code</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. 6200"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Account Class</label>
                    <select
                      value={formData.account_class}
                      onChange={(e) => {
                        const cls = e.target.value;
                        const normal = cls === "ASSET" || cls === "EXPENSE" ? "DEBIT" : "CREDIT";
                        setFormData({ ...formData, account_class: cls, normal_balance: normal });
                      }}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none bg-white"
                    >
                      <option value="ASSET">ASSET</option>
                      <option value="LIABILITY">LIABILITY</option>
                      <option value="EQUITY">EQUITY</option>
                      <option value="REVENUE">REVENUE</option>
                      <option value="EXPENSE">EXPENSE</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Account Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Advertising & Marketing"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Subtype</label>
                    <select
                      value={formData.subtype}
                      onChange={(e) => setFormData({ ...formData, subtype: e.target.value })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none bg-white"
                    >
                      <option value="CURRENT_ASSET">CURRENT_ASSET</option>
                      <option value="BANK">BANK</option>
                      <option value="FIXED_ASSET">FIXED_ASSET</option>
                      <option value="CURRENT_LIABILITY">CURRENT_LIABILITY</option>
                      <option value="TAX_LIABILITY">TAX_LIABILITY</option>
                      <option value="EQUITY">EQUITY</option>
                      <option value="OPERATING_REVENUE">OPERATING_REVENUE</option>
                      <option value="OPERATING_EXPENSE">OPERATING_EXPENSE</option>
                      <option value="COST_OF_GOODS_SOLD">COST_OF_GOODS_SOLD</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Normal Balance</label>
                    <select
                      value={formData.normal_balance}
                      onChange={(e) => setFormData({ ...formData, normal_balance: e.target.value as any })}
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none bg-white font-mono"
                    >
                      <option value="DEBIT">DEBIT (Dr)</option>
                      <option value="CREDIT">CREDIT (Cr)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Description (Optional)</label>
                  <input
                    type="text"
                    placeholder="Brief explanation of intended usage"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                  />
                </div>

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
                    disabled={submitting}
                    className="px-4 py-1.5 bg-[#0073B7] hover:bg-[#005f96] text-white font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50"
                  >
                    {submitting ? "Saving..." : "Save Account"}
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

export default function ChartOfAccountsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Chart of Accounts...</div>}>
      <ChartOfAccountsContent />
    </Suspense>
  );
}
