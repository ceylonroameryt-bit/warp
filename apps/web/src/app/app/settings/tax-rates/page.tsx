"use client";

import React, { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, AlertCircle, CheckCircle } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface TaxRate {
  id: string;
  name: string;
  code: string;
  rate: string;
  tax_type: string;
  active: boolean;
}

const TAX_TYPE_LABELS: Record<string, string> = {
  STANDARD: "Standard",
  REDUCED: "Reduced",
  ZERO: "Zero Rate",
  EXEMPT: "Exempt",
  OUTSIDE_SCOPE: "Outside Scope",
};

export default function TaxRatesSettingsPage() {
  const [rates, setRates] = useState<TaxRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newRate, setNewRate] = useState("20.0000");
  const [newType, setNewType] = useState("STANDARD");
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState("");

  async function loadRates() {
    if (!ORG_ID) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${ORG_ID}/tax-rates?active_only=false`,
        { credentials: "include" }
      );
      if (res.ok) setRates(await res.json());
    } catch {
      setError("Failed to load tax rates.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRates(); }, []);

  async function handleCreate() {
    if (!newName.trim() || !newCode.trim()) {
      setCreateErr("Name and code are required.");
      return;
    }
    setCreating(true); setCreateErr("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${ORG_ID}/tax-rates`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            name: newName,
            code: newCode.toUpperCase(),
            rate: newRate,
            tax_type: newType,
          }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        setCreateErr(data?.detail || "Failed to create tax rate.");
        return;
      }
      setNewName(""); setNewCode(""); setNewRate("20.0000"); setNewType("STANDARD");
      setShowCreate(false);
      setSuccess("Tax rate created.");
      await loadRates();
    } catch {
      setCreateErr("Network error.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeactivate(rateId: string) {
    try {
      await fetch(
        `${API_BASE}/api/v1/organisations/${ORG_ID}/tax-rates/${rateId}`,
        { method: "DELETE", credentials: "include" }
      );
      setSuccess("Tax rate deactivated.");
      await loadRates();
    } catch {
      setError("Failed to deactivate tax rate.");
    }
  }

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Tax Rates</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Configure VAT and tax rates for your invoices
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-3 py-2 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Rate
          </button>
        </div>

        {success && (
          <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 mb-4 text-sm text-emerald-700">
            <CheckCircle className="h-4 w-4" /> {success}
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4 text-sm text-red-700">
            <AlertCircle className="h-4 w-4" /> {error}
          </div>
        )}

        {/* Create Form */}
        {showCreate && (
          <div className="bg-white border border-sky-200 rounded-xl p-5 mb-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">New Tax Rate</h2>
            {createErr && (
              <p className="text-xs text-red-500 mb-3">{createErr}</p>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-slate-500 block mb-1">Name *</label>
                <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Standard Rate"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">Code *</label>
                <input type="text" value={newCode} onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                  placeholder="e.g. STD20"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">Rate %</label>
                <input type="number" value={newRate} onChange={(e) => setNewRate(e.target.value)}
                  min="0" max="100" step="0.0001"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400" />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-slate-500 block mb-1">Type</label>
                <select value={newType} onChange={(e) => setNewType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white">
                  {Object.entries(TAX_TYPE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={handleCreate} disabled={creating}
                className="px-4 py-2 bg-sky-600 text-white text-sm font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors">
                {creating ? "Creating…" : "Create Rate"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="px-4 py-2 border border-slate-200 text-sm text-slate-600 rounded-lg hover:bg-slate-50 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Rates Table */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="hidden sm:grid grid-cols-[1fr_80px_100px_120px_80px_60px] gap-4 px-5 py-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <div>Name</div>
            <div>Code</div>
            <div className="text-right">Rate</div>
            <div>Type</div>
            <div>Status</div>
            <div />
          </div>

          {loading ? (
            <div className="px-5 py-8 text-sm text-slate-400 text-center">Loading…</div>
          ) : rates.length === 0 ? (
            <div className="px-5 py-8 text-sm text-slate-400 text-center">
              No tax rates. Click "Add Rate" to create one.
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {rates.map((r) => (
                <div
                  key={r.id}
                  className={`grid grid-cols-1 sm:grid-cols-[1fr_80px_100px_120px_80px_60px] gap-4 items-center px-5 py-3.5 ${
                    !r.active ? "opacity-50" : ""
                  }`}
                >
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{r.name}</p>
                  </div>
                  <div>
                    <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-600">
                      {r.code}
                    </code>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-slate-800">{parseFloat(r.rate)}%</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">
                      {TAX_TYPE_LABELS[r.tax_type] ?? r.tax_type}
                    </span>
                  </div>
                  <div>
                    {r.active ? (
                      <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                        Active
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                        Inactive
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 justify-end">
                    {r.active && (
                      <button
                        onClick={() => handleDeactivate(r.id)}
                        className="p-1.5 text-slate-300 hover:text-red-500 transition-colors"
                        title="Deactivate"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <p className="text-xs text-slate-400 mt-4 leading-relaxed">
          Deactivating a rate removes it from new invoices but preserves it on historical records.
        </p>
      </div>
    </DashboardLayout>
  );
}
