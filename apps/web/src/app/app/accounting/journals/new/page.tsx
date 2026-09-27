"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  ArrowLeft,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Save,
  Send,
  HelpCircle,
  Lock,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface AccountOption {
  id: string;
  code: string;
  name: string;
  account_class: string;
  normal_balance: string;
}

interface JournalFormLine {
  account_id: string;
  description: string;
  debit: string;
  credit: string;
}

const DEMO_ACCOUNTS: AccountOption[] = [
  { id: "1", code: "1000", name: "Operating Bank Account", account_class: "ASSET", normal_balance: "DEBIT" },
  { id: "2", code: "1100", name: "Accounts Receivable", account_class: "ASSET", normal_balance: "DEBIT" },
  { id: "3", code: "1200", name: "Prepayments & Accruals", account_class: "ASSET", normal_balance: "DEBIT" },
  { id: "4", code: "1500", name: "Office Equipment", account_class: "ASSET", normal_balance: "DEBIT" },
  { id: "5", code: "2000", name: "Accounts Payable", account_class: "LIABILITY", normal_balance: "CREDIT" },
  { id: "6", code: "2200", name: "VAT Output Tax", account_class: "LIABILITY", normal_balance: "CREDIT" },
  { id: "8", code: "3000", name: "Share Capital", account_class: "EQUITY", normal_balance: "CREDIT" },
  { id: "10", code: "4000", name: "Consulting Sales", account_class: "REVENUE", normal_balance: "CREDIT" },
  { id: "12", code: "5000", name: "Cost of Goods Sold", account_class: "EXPENSE", normal_balance: "DEBIT" },
  { id: "13", code: "6000", name: "Rent Expense", account_class: "EXPENSE", normal_balance: "DEBIT" },
  { id: "14", code: "6050", name: "Depreciation Expense", account_class: "EXPENSE", normal_balance: "DEBIT" },
];

export default function NewJournalPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<AccountOption[]>(DEMO_ACCOUNTS);
  const [entryDate, setEntryDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [narration, setNarration] = useState("");
  const [reference, setReference] = useState("");

  const [lines, setLines] = useState<JournalFormLine[]>([
    { account_id: "", description: "", debit: "", credit: "" },
    { account_id: "", description: "", debit: "", credit: "" },
  ]);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Fetch Chart of Accounts for selector
  useEffect(() => {
    async function loadAccounts() {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/accounts?is_active=true`, { headers });
        if (res.ok) {
          const data = await res.json();
          if (data && data.length > 0) {
            setAccounts(data);
          }
        }
      } catch (err) {
        console.warn("Using demo account options", err);
      }
    }
    loadAccounts();
  }, []);

  const handleLineChange = (index: number, field: keyof JournalFormLine, value: string) => {
    const updated = [...lines];
    updated[index] = { ...updated[index], [field]: value };

    // Prevent both debit and credit on same line
    if (field === "debit" && value && parseFloat(value) > 0) {
      updated[index].credit = "";
    } else if (field === "credit" && value && parseFloat(value) > 0) {
      updated[index].debit = "";
    }

    setLines(updated);
  };

  const addLine = () => {
    setLines([...lines, { account_id: "", description: "", debit: "", credit: "" }]);
  };

  const removeLine = (index: number) => {
    if (lines.length <= 2) {
      setErrorMsg("A journal entry requires at least 2 lines for double-entry bookkeeping.");
      return;
    }
    setLines(lines.filter((_, idx) => idx !== index));
  };

  // Live balance math
  const totalDebit = lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0);
  const totalCredit = lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0);
  const diff = Math.abs(totalDebit - totalCredit);
  const isBalanced = diff < 0.0001 && totalDebit > 0;

  const handleSubmit = async (postDirectly: boolean) => {
    setErrorMsg("");

    if (!narration.trim()) {
      setErrorMsg("Please enter a narration/description for this journal entry.");
      return;
    }

    if (lines.length < 2) {
      setErrorMsg("A journal entry must contain at least 2 lines.");
      return;
    }

    for (let i = 0; i < lines.length; i++) {
      const l = lines[i];
      if (!l.account_id) {
        setErrorMsg(`Line #${i + 1} is missing an account.`);
        return;
      }
      const d = parseFloat(l.debit) || 0;
      const c = parseFloat(l.credit) || 0;
      if (d <= 0 && c <= 0) {
        setErrorMsg(`Line #${i + 1} must have a positive Debit or Credit amount.`);
        return;
      }
    }

    if (!isBalanced) {
      setErrorMsg(`Journal is out of balance by £${diff.toFixed(2)}. Total debits must equal total credits.`);
      return;
    }

    setSubmitting(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const payload = {
        entry_date: entryDate,
        narration: narration.trim(),
        reference: reference.trim() || undefined,
        status: postDirectly ? "POSTED" : "DRAFT",
        lines: lines.map((l) => ({
          account_id: l.account_id,
          description: l.description.trim() || undefined,
          debit: parseFloat(l.debit) || 0,
          credit: parseFloat(l.credit) || 0,
        })),
      };

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/journals`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create journal entry.");
      }

      router.push("/app/accounting/journals");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit journal");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-6 pb-16">
        {/* Top Breadcrumb & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div className="flex items-center gap-3">
            <Link
              href="/app/accounting/journals"
              className="p-1.5 rounded-md hover:bg-slate-100 text-slate-500 hover:text-slate-900 transition-colors"
              title="Back to Journals"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">New Manual Journal</h1>
              <p className="text-xs text-slate-500">Record adjusting transactions directly into the general ledger</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSubmit(false)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5 text-slate-500" />
              Save as Draft
            </button>
            <button
              type="button"
              disabled={submitting || !isBalanced}
              onClick={() => handleSubmit(true)}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
              {submitting ? "Posting..." : "Save & Post Journal"}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Journal Header Fields */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Entry Date <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="date"
                  required
                  value={entryDate}
                  onChange={(e) => setEntryDate(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                />
              </div>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Narration / Description <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Month-end depreciation for IT hardware"
                value={narration}
                onChange={(e) => setNarration(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Reference / Memo (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. ADJ-2026-03"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none font-mono"
              />
            </div>
          </div>
        </div>

        {/* Journal Double-Entry Lines Table */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Accounting Entries</h2>
            <span className="text-[11px] text-slate-500">Every entry requires at least 1 Debit and 1 Credit</span>
          </div>

          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/70 border-b border-slate-200 text-[10px] font-semibold uppercase text-slate-500">
              <tr>
                <th className="py-2.5 px-3 w-8 text-center">#</th>
                <th className="py-2.5 px-3 w-64">Account <span className="text-rose-500">*</span></th>
                <th className="py-2.5 px-3">Line Description</th>
                <th className="py-2.5 px-3 w-36 text-right">Debit (Dr)</th>
                <th className="py-2.5 px-3 w-36 text-right">Credit (Cr)</th>
                <th className="py-2.5 px-3 w-12 text-center"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                  <td className="py-2 px-3 text-center text-slate-400 font-mono">{idx + 1}</td>
                  <td className="py-2 px-3">
                    <select
                      value={line.account_id}
                      onChange={(e) => handleLineChange(idx, "account_id", e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none bg-white"
                    >
                      <option value="">Select Account...</option>
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.code} - {acc.name} ({acc.account_class})
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="text"
                      placeholder="Optional memo..."
                      value={line.description}
                      onChange={(e) => handleLineChange(idx, "description", e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={line.debit}
                      onChange={(e) => handleLineChange(idx, "debit", e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs text-right font-mono border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      value={line.credit}
                      onChange={(e) => handleLineChange(idx, "credit", e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs text-right font-mono border border-slate-300 rounded-md focus:border-[#0073B7] focus:outline-none"
                    />
                  </td>
                  <td className="py-2 px-3 text-center">
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                      title="Delete Line"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="p-3 bg-slate-50/50 border-t border-slate-200">
            <button
              type="button"
              onClick={addLine}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
            >
              <Plus className="h-3.5 w-3.5 text-[#0073B7]" />
              Add Another Line
            </button>
          </div>
        </div>

        {/* Live Double-Entry Balancing Card */}
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            {isBalanced ? (
              <div className="h-10 w-10 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
                <CheckCircle2 className="h-6 w-6" />
              </div>
            ) : (
              <div className="h-10 w-10 rounded-full bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-600 shrink-0">
                <AlertCircle className="h-6 w-6" />
              </div>
            )}
            <div>
              <div className="text-xs font-bold text-slate-900">
                {isBalanced ? "Ledger In Equilibrium" : "Out of Balance"}
              </div>
              <div className="text-[11px] text-slate-500">
                {isBalanced
                  ? "Debits exactly equal Credits. Ready for general ledger posting."
                  : `Variance of £${diff.toFixed(2)}. Adjust entries until difference is zero.`}
              </div>
            </div>
          </div>

          {/* Running Totals */}
          <div className="flex items-center gap-6 border-t sm:border-t-0 pt-4 sm:pt-0 border-slate-100">
            <div className="text-right">
              <div className="text-[10px] uppercase font-semibold text-slate-400">Total Debit</div>
              <div className="font-mono font-bold text-slate-900 text-sm">
                £{totalDebit.toFixed(2)}
              </div>
            </div>

            <div className="text-right">
              <div className="text-[10px] uppercase font-semibold text-slate-400">Total Credit</div>
              <div className="font-mono font-bold text-slate-900 text-sm">
                £{totalCredit.toFixed(2)}
              </div>
            </div>

            <div className="text-right pl-3 border-l border-slate-200">
              <div className="text-[10px] uppercase font-semibold text-slate-400">Difference</div>
              <div className={`font-mono font-black text-sm ${isBalanced ? "text-emerald-600" : "text-rose-600"}`}>
                £{diff.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
