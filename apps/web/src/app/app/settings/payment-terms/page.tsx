"use client";

import React, { useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/DashboardLayout";
import {
  CreditCard,
  Plus,
  Check,
  Calendar,
  Clock,
  Edit2,
  ArrowLeft,
  Info,
  Building2,
  Truck,
  X,
  Lock,
} from "lucide-react";

interface PaymentTermItem {
  id: string;
  name: string;
  term_type: "NET_DAYS" | "END_OF_MONTH" | "END_OF_NEXT_MONTH" | "SPECIFIC_DAY_OF_MONTH";
  days: number;
  is_default_customer: boolean;
  is_default_supplier: boolean;
  is_active: boolean;
  is_system?: boolean;
}

export default function PaymentTermsSettingsPage() {
  const [terms, setTerms] = useState<PaymentTermItem[]>([
    {
      id: "pt-1",
      name: "Due immediately",
      term_type: "NET_DAYS",
      days: 0,
      is_default_customer: false,
      is_default_supplier: false,
      is_active: true,
      is_system: true,
    },
    {
      id: "pt-2",
      name: "7 days",
      term_type: "NET_DAYS",
      days: 7,
      is_default_customer: false,
      is_default_supplier: false,
      is_active: true,
      is_system: true,
    },
    {
      id: "pt-3",
      name: "14 days",
      term_type: "NET_DAYS",
      days: 14,
      is_default_customer: false,
      is_default_supplier: false,
      is_active: true,
      is_system: true,
    },
    {
      id: "pt-4",
      name: "30 days",
      term_type: "NET_DAYS",
      days: 30,
      is_default_customer: true,
      is_default_supplier: true,
      is_active: true,
      is_system: true,
    },
    {
      id: "pt-5",
      name: "60 days",
      term_type: "NET_DAYS",
      days: 60,
      is_default_customer: false,
      is_default_supplier: false,
      is_active: true,
      is_system: true,
    },
    {
      id: "pt-6",
      name: "End of next month",
      term_type: "END_OF_NEXT_MONTH",
      days: 0,
      is_default_customer: false,
      is_default_supplier: false,
      is_active: true,
      is_system: true,
    },
  ]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState<
    "NET_DAYS" | "END_OF_MONTH" | "END_OF_NEXT_MONTH" | "SPECIFIC_DAY_OF_MONTH"
  >("NET_DAYS");
  const [formDays, setFormDays] = useState<number>(30);
  const [formDefaultCustomer, setFormDefaultCustomer] = useState(false);
  const [formDefaultSupplier, setFormDefaultSupplier] = useState(false);

  const openCreateModal = () => {
    setEditingId(null);
    setFormName("");
    setFormType("NET_DAYS");
    setFormDays(30);
    setFormDefaultCustomer(false);
    setFormDefaultSupplier(false);
    setModalOpen(true);
  };

  const openEditModal = (term: PaymentTermItem) => {
    setEditingId(term.id);
    setFormName(term.name);
    setFormType(term.term_type);
    setFormDays(term.days);
    setFormDefaultCustomer(term.is_default_customer);
    setFormDefaultSupplier(term.is_default_supplier);
    setModalOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    setTerms((prev) => {
      let updated = [...prev];

      if (formDefaultCustomer) {
        updated = updated.map((t) => ({ ...t, is_default_customer: false }));
      }
      if (formDefaultSupplier) {
        updated = updated.map((t) => ({ ...t, is_default_supplier: false }));
      }

      if (editingId) {
        return updated.map((t) =>
          t.id === editingId
            ? {
                ...t,
                name: formName,
                term_type: formType,
                days: formDays,
                is_default_customer: formDefaultCustomer,
                is_default_supplier: formDefaultSupplier,
              }
            : t
        );
      } else {
        const newTerm: PaymentTermItem = {
          id: `pt-${Date.now()}`,
          name: formName,
          term_type: formType,
          days: formDays,
          is_default_customer: formDefaultCustomer,
          is_default_supplier: formDefaultSupplier,
          is_active: true,
          is_system: false,
        };
        return [...updated, newTerm];
      }
    });

    setModalOpen(false);
  };

  const toggleActive = (id: string) => {
    setTerms((prev) =>
      prev.map((t) => (t.id === id ? { ...t, is_active: !t.is_active } : t))
    );
  };

  const setDefault = (id: string, type: "customer" | "supplier") => {
    setTerms((prev) =>
      prev.map((t) => {
        if (type === "customer") {
          return { ...t, is_default_customer: t.id === id };
        } else {
          return { ...t, is_default_supplier: t.id === id };
        }
      })
    );
  };

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Link
              href="/app/contacts"
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors mb-1.5"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Contacts
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Payment Terms</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Set up credit and payment rules applied automatically to sales invoices and purchase bills.
            </p>
          </div>

          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all self-start sm:self-auto"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Payment Term
          </button>
        </div>

        {/* Info Box */}
        <div className="p-4 rounded-lg bg-sky-50 border border-sky-200 text-xs text-sky-900 flex items-start gap-3">
          <Info className="h-4 w-4 text-[#0073B7] flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-sky-950">Default Organization Terms:</span> The selected defaults apply automatically when adding new customers or suppliers. Individual contacts can override these defaults at any time.
          </div>
        </div>

        {/* Table of Terms */}
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[11px] font-semibold tracking-wider">
                <tr>
                  <th className="px-4 py-3">Term Name</th>
                  <th className="px-4 py-3">Calculation Rule</th>
                  <th className="px-4 py-3">Days</th>
                  <th className="px-4 py-3 text-center">Customer Default</th>
                  <th className="px-4 py-3 text-center">Supplier Default</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {terms.map((term) => (
                  <tr key={term.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{term.name}</span>
                        {term.is_system && (
                          <span title="Standard system term" className="text-slate-400">
                            <Lock className="h-3 w-3" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px]">
                        {term.term_type === "NET_DAYS" && "Net Days from Invoice Date"}
                        {term.term_type === "END_OF_MONTH" && "End of Current Month"}
                        {term.term_type === "END_OF_NEXT_MONTH" && "End of Following Month"}
                        {term.term_type === "SPECIFIC_DAY_OF_MONTH" && "Specific Day of Next Month"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-800">
                      {term.term_type === "NET_DAYS" ? `${term.days} days` : "-"}
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      {term.is_default_customer ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                          <Building2 className="h-3 w-3" />
                          Default
                        </span>
                      ) : (
                        <button
                          onClick={() => setDefault(term.id, "customer")}
                          className="text-[10px] text-slate-400 hover:text-[#0073B7] transition-colors underline"
                        >
                          Set default
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      {term.is_default_supplier ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                          <Truck className="h-3 w-3" />
                          Default
                        </span>
                      ) : (
                        <button
                          onClick={() => setDefault(term.id, "supplier")}
                          className="text-[10px] text-slate-400 hover:text-purple-600 transition-colors underline"
                        >
                          Set default
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      {term.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-slate-400 font-medium">
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => openEditModal(term)}
                          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                          title="Edit Term"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => toggleActive(term.id)}
                          className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                            term.is_active
                              ? "text-slate-500 hover:text-amber-700 hover:bg-amber-50"
                              : "text-slate-500 hover:text-emerald-700 hover:bg-emerald-50"
                          }`}
                        >
                          {term.is_active ? "Disable" : "Enable"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150">
            <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  {editingId ? "Edit Payment Term" : "Add Payment Term"}
                </h3>
                <button
                  onClick={() => setModalOpen(false)}
                  className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleSave} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Term Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Net 45 Days"
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Calculation Type
                  </label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  >
                    <option value="NET_DAYS">Net Days from Invoice Date</option>
                    <option value="END_OF_MONTH">End of Current Month</option>
                    <option value="END_OF_NEXT_MONTH">End of Following Month</option>
                    <option value="SPECIFIC_DAY_OF_MONTH">Specific Day of Next Month</option>
                  </select>
                </div>

                {formType === "NET_DAYS" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Number of Days
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="365"
                      value={formDays}
                      onChange={(e) => setFormDays(parseInt(e.target.value) || 0)}
                      className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                    />
                  </div>
                )}

                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formDefaultCustomer}
                      onChange={(e) => setFormDefaultCustomer(e.target.checked)}
                      className="rounded border-slate-300 text-[#0073B7] focus:ring-[#0073B7]"
                    />
                    <span className="text-xs text-slate-700">
                      Set as default for new customers
                    </span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formDefaultSupplier}
                      onChange={(e) => setFormDefaultSupplier(e.target.checked)}
                      className="rounded border-slate-300 text-[#0073B7] focus:ring-[#0073B7]"
                    />
                    <span className="text-xs text-slate-700">
                      Set as default for new suppliers
                    </span>
                  </label>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="px-3 py-1.5 rounded-md border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm"
                  >
                    {editingId ? "Save Changes" : "Create Term"}
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
