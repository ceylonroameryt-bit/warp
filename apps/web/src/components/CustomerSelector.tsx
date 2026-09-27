"use client";

import React, { useState, useEffect, useRef } from "react";
import { Search, Plus, X, Building2, ChevronDown } from "lucide-react";

interface Customer {
  id: string;
  business_name: string;
  email?: string;
  reference?: string;
  contact_type: string;
}

interface Props {
  orgId: string;
  value?: Customer | null;
  onChange: (customer: Customer | null) => void;
  disabled?: boolean;
  error?: string;
}

interface QuickCreateForm {
  business_name: string;
  email: string;
  phone: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function CustomerSelector({
  orgId,
  value,
  onChange,
  disabled = false,
  error,
}: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [quickForm, setQuickForm] = useState<QuickCreateForm>({
    business_name: "",
    email: "",
    phone: "",
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    const delay = setTimeout(() => {
      if (search.length >= 1) {
        fetchCustomers(search);
      } else if (search === "") {
        fetchCustomers("");
      }
    }, 250);
    return () => clearTimeout(delay);
  }, [search, orgId]);

  async function fetchCustomers(q: string) {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        contact_type: "CUSTOMER",
        search: q,
        page_size: "10",
        status: "ACTIVE",
      });
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/contacts?${params}`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setResults(data.items ?? []);
      }
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleQuickCreate() {
    if (!quickForm.business_name.trim()) {
      setCreateError("Business name is required.");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/contacts/quick-create`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            ...quickForm,
            contact_type: "CUSTOMER",
          }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        setCreateError(data?.detail || "Failed to create customer.");
        return;
      }
      const newCustomer: Customer = await res.json();
      onChange(newCustomer);
      setShowQuickCreate(false);
      setOpen(false);
      setSearch("");
    } catch {
      setCreateError("Network error. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      {/* Selected value display */}
      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border text-sm transition-all ${
          error
            ? "border-red-300 bg-red-50"
            : "border-slate-200 bg-white hover:border-sky-300"
        } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
      >
        {value ? (
          <span className="flex items-center gap-2 flex-1 min-w-0">
            <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
            <span className="font-medium text-slate-800 truncate">
              {value.business_name}
            </span>
            {value.email && (
              <span className="text-slate-400 text-xs truncate">{value.email}</span>
            )}
          </span>
        ) : (
          <span className="flex items-center gap-2 text-slate-400">
            <Building2 className="h-4 w-4" />
            Select customer…
          </span>
        )}
        <div className="flex items-center gap-1">
          {value && (
            <span
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
              className="p-0.5 hover:text-red-500 text-slate-400 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          )}
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </div>
      </button>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden">
          {/* Search */}
          <div className="p-2 border-b border-slate-100">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Search by name, email or reference…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
              />
            </div>
          </div>

          {/* Results */}
          <div className="max-h-52 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-3 text-xs text-slate-400">Searching…</div>
            ) : results.length === 0 ? (
              <div className="px-4 py-3 text-xs text-slate-500">
                No customers found.
              </div>
            ) : (
              results.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    onChange(c);
                    setOpen(false);
                    setSearch("");
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-sky-50 text-left transition-colors"
                >
                  <div className="h-7 w-7 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center text-xs font-bold shrink-0">
                    {c.business_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">
                      {c.business_name}
                    </p>
                    {c.email && (
                      <p className="text-xs text-slate-400 truncate">{c.email}</p>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Quick Create */}
          <div className="border-t border-slate-100">
            {!showQuickCreate ? (
              <button
                type="button"
                onClick={() => setShowQuickCreate(true)}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-sky-600 hover:bg-sky-50 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                Add New Customer
              </button>
            ) : (
              <div className="p-3 space-y-2">
                <p className="text-xs font-semibold text-slate-600">Quick Create Customer</p>
                <input
                  type="text"
                  placeholder="Business Name *"
                  value={quickForm.business_name}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, business_name: e.target.value })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={quickForm.email}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, email: e.target.value })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
                />
                <input
                  type="tel"
                  placeholder="Phone"
                  value={quickForm.phone}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, phone: e.target.value })
                  }
                  className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400"
                />
                {createError && (
                  <p className="text-xs text-red-500">{createError}</p>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleQuickCreate}
                    disabled={creating}
                    className="flex-1 py-1.5 bg-sky-600 text-white text-xs font-semibold rounded-lg hover:bg-sky-700 disabled:opacity-60 transition-colors"
                  >
                    {creating ? "Creating…" : "Create & Select"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowQuickCreate(false)}
                    className="px-3 py-1.5 border border-slate-200 text-xs rounded-lg hover:bg-slate-50 text-slate-600 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
