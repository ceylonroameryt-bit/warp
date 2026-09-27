"use client";

import React, { useState, useEffect, useRef } from "react";
import { Search, Plus, X, Building2, ChevronDown, Check, AlertCircle } from "lucide-react";

export interface Supplier {
  id: string;
  business_name: string;
  email?: string;
  reference?: string;
  vat_number?: string;
  contact_type: string;
  payment_terms_id?: string;
}

interface Props {
  orgId: string;
  value?: Supplier | null;
  onChange: (supplier: Supplier | null) => void;
  disabled?: boolean;
  error?: string;
}

interface QuickSupplierForm {
  business_name: string;
  email: string;
  phone: string;
  vat_number: string;
  payment_terms_id: string;
}

interface PaymentTermOption {
  id: string;
  name: string;
  days: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function SupplierSelector({
  orgId,
  value,
  onChange,
  disabled = false,
  error,
}: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);

  // Quick Create Modal State
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTermOption[]>([]);
  const [quickForm, setQuickForm] = useState<QuickSupplierForm>({
    business_name: "",
    email: "",
    phone: "",
    vat_number: "",
    payment_terms_id: "",
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => searchRef.current?.focus(), 50);
    }
  }, [open]);

  // Load payment terms when quick create opens
  useEffect(() => {
    if (showQuickCreate && orgId) {
      fetch(`${API_BASE}/api/v1/organisations/${orgId}/payment-terms`, { credentials: "include" })
        .then((r) => (r.ok ? r.json() : []))
        .then((data) => setPaymentTerms(Array.isArray(data) ? data : data.items || []))
        .catch(() => {});
    }
  }, [showQuickCreate, orgId]);

  // Search suppliers (SUPPLIER or BOTH)
  useEffect(() => {
    const delay = setTimeout(() => {
      if (!orgId) return;
      setLoading(true);

      const params = new URLSearchParams({
        page_size: "15",
      });
      if (search.trim()) params.set("search", search.trim());

      fetch(`${API_BASE}/api/v1/organisations/${orgId}/contacts?${params.toString()}`, {
        credentials: "include",
      })
        .then((res) => (res.ok ? res.json() : { items: [] }))
        .then((data) => {
          const list: Supplier[] = data.items || [];
          // Filter to only SUPPLIER or BOTH
          const suppliersOnly = list.filter(
            (c) => c.contact_type === "SUPPLIER" || c.contact_type === "BOTH"
          );
          setResults(suppliersOnly);
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 200);

    return () => clearTimeout(delay);
  }, [search, orgId, open]);

  // Handle Quick Create Supplier
  const handleQuickCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickForm.business_name.trim()) {
      setCreateError("Supplier business name is required.");
      return;
    }

    setCreating(true);
    setCreateError("");

    try {
      const payload: any = {
        business_name: quickForm.business_name.trim(),
        contact_type: "SUPPLIER",
        email: quickForm.email.trim() || undefined,
        phone: quickForm.phone.trim() || undefined,
        vat_number: quickForm.vat_number.trim() || undefined,
        payment_terms_id: quickForm.payment_terms_id || undefined,
      };

      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/contacts/quick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || "Failed to create supplier");
      }

      const newSupplier: Supplier = await res.json();
      onChange(newSupplier);
      setShowQuickCreate(false);
      setOpen(false);
      setQuickForm({
        business_name: "",
        email: "",
        phone: "",
        vat_number: "",
        payment_terms_id: "",
      });
    } catch (err: any) {
      setCreateError(err.message || "Could not create supplier.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      {/* ── Trigger Button ── */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg border bg-white text-left transition-colors ${
          disabled ? "bg-slate-50 text-slate-400 cursor-not-allowed border-slate-200" : ""
        } ${
          error
            ? "border-rose-400 focus:ring-rose-200"
            : "border-slate-300 hover:border-slate-400 focus:border-sky-500 focus:ring-sky-100"
        } focus:outline-none focus:ring-2`}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
          {value ? (
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-slate-800 block truncate">
                {value.business_name}
              </span>
              {value.email && (
                <span className="text-[11px] text-slate-400 block truncate">{value.email}</span>
              )}
            </div>
          ) : (
            <span className="text-slate-400">Select an existing supplier...</span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-2">
          {value && !disabled && (
            <span
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
              className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"
              title="Clear selection"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          )}
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </div>
      </button>

      {error && <p className="mt-1 text-[11px] text-rose-500">{error}</p>}

      {/* ── Dropdown Panel ── */}
      {open && (
        <div className="absolute left-0 top-full mt-1.5 w-full min-w-[320px] rounded-xl bg-white border border-slate-200 shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
          {/* Search Header */}
          <div className="p-2 border-b border-slate-100 bg-slate-50/70">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Search suppliers by name, email, VAT..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white placeholder-slate-400 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          {/* Quick Create CTA */}
          <div className="px-2 py-1.5 bg-sky-50/60 border-b border-sky-100 flex items-center justify-between">
            <span className="text-[11px] text-slate-600 font-medium">Supplier not found?</span>
            <button
              type="button"
              onClick={() => {
                setQuickForm({
                  business_name: search.trim(),
                  email: "",
                  phone: "",
                  vat_number: "",
                  payment_terms_id: "",
                });
                setShowQuickCreate(true);
              }}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-700 hover:text-sky-800 bg-white px-2 py-1 rounded-md border border-sky-200 shadow-xs hover:bg-sky-50 transition-colors"
            >
              <Plus className="h-3 w-3" />
              Add Supplier
            </button>
          </div>

          {/* Result List */}
          <div className="max-h-60 overflow-y-auto divide-y divide-slate-50 p-1">
            {loading ? (
              <div className="py-6 text-center text-xs text-slate-400">Searching suppliers...</div>
            ) : results.length === 0 ? (
              <div className="py-6 text-center">
                <p className="text-xs text-slate-500 font-medium">No suppliers match your search</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Click "Add Supplier" above to create one</p>
              </div>
            ) : (
              results.map((supplier) => {
                const isSelected = value?.id === supplier.id;
                return (
                  <div
                    key={supplier.id}
                    onClick={() => {
                      onChange(supplier);
                      setOpen(false);
                    }}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors text-xs ${
                      isSelected ? "bg-sky-50 text-sky-900" : "hover:bg-slate-50 text-slate-800"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate flex items-center gap-1.5">
                        <span>{supplier.business_name}</span>
                        {supplier.contact_type === "BOTH" && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-slate-100 text-slate-500 border border-slate-200">
                            Both
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 truncate mt-0.5">
                        {supplier.email && <span>{supplier.email}</span>}
                        {supplier.vat_number && <span>VAT: {supplier.vat_number}</span>}
                      </div>
                    </div>
                    {isSelected && <Check className="h-4 w-4 text-sky-600 shrink-0 ml-2" />}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ── Quick Create Modal ── */}
      {showQuickCreate && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
                  <Building2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-none">Add New Supplier</h3>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Quickly create a supplier without leaving this bill
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowQuickCreate(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {createError && (
              <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2 text-rose-700 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleQuickCreate} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Supplier Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Microsoft Limited"
                  value={quickForm.business_name}
                  onChange={(e) => setQuickForm({ ...quickForm, business_name: e.target.value })}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Billing Email
                  </label>
                  <input
                    type="email"
                    placeholder="accounts@supplier.com"
                    value={quickForm.email}
                    onChange={(e) => setQuickForm({ ...quickForm, email: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    placeholder="+44 20 7946 0912"
                    value={quickForm.phone}
                    onChange={(e) => setQuickForm({ ...quickForm, phone: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    VAT / Tax Number
                  </label>
                  <input
                    type="text"
                    placeholder="GB 123 4567 89"
                    value={quickForm.vat_number}
                    onChange={(e) => setQuickForm({ ...quickForm, vat_number: e.target.value })}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Payment Terms
                  </label>
                  <select
                    value={quickForm.payment_terms_id}
                    onChange={(e) =>
                      setQuickForm({ ...quickForm, payment_terms_id: e.target.value })
                    }
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:border-sky-500"
                  >
                    <option value="">Default (30 Days)</option>
                    {paymentTerms.map((pt) => (
                      <option key={pt.id} value={pt.id}>
                        {pt.name} ({pt.days} days)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowQuickCreate(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-sm transition-colors disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create & Select"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
