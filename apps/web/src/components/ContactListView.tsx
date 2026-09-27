"use client";

import React, { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Plus,
  Filter,
  Download,
  Upload,
  MoreHorizontal,
  Building2,
  Truck,
  Users,
  Archive,
  RotateCcw,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  CheckSquare,
  Square,
  FileSpreadsheet,
  Check,
  Building,
  Mail,
  Phone,
  ArrowUpDown,
  CreditCard,
  Eye,
  Edit2,
  ShieldCheck,
} from "lucide-react";

interface Contact {
  id: string;
  contact_type: "CUSTOMER" | "SUPPLIER" | "BOTH";
  business_name: string;
  legal_name?: string;
  email?: string;
  phone?: string;
  primary_contact_name?: string;
  primary_contact_email?: string;
  payment_terms_name?: string;
  status: "ACTIVE" | "ARCHIVED";
  currency: string;
  updated_at: string;
  reference?: string;
}

interface ContactListViewProps {
  initialType?: "CUSTOMER" | "SUPPLIER" | "BOTH" | "ALL";
  pageTitle: string;
  subtitle: string;
}

const DEMO_CONTACTS: Contact[] = [
  {
    id: "c1-apex",
    contact_type: "CUSTOMER",
    business_name: "Apex Innovations Ltd",
    legal_name: "Apex Innovations Limited",
    email: "accounts@apexinnovations.co.uk",
    phone: "+44 20 7946 0912",
    primary_contact_name: "Jane Doe",
    primary_contact_email: "jane@apexinnovations.co.uk",
    payment_terms_name: "30 days",
    status: "ACTIVE",
    currency: "GBP",
    reference: "CUS-00128",
    updated_at: new Date().toISOString(),
  },
  {
    id: "c2-quickparts",
    contact_type: "SUPPLIER",
    business_name: "Quick Parts Supply Co",
    legal_name: "Quick Parts International Ltd",
    email: "billing@quickparts.co.uk",
    phone: "+44 161 496 0872",
    primary_contact_name: "Mark Reynolds",
    primary_contact_email: "mark@quickparts.co.uk",
    payment_terms_name: "14 days",
    status: "ACTIVE",
    currency: "GBP",
    reference: "SUP-00045",
    updated_at: new Date().toISOString(),
  },
  {
    id: "c3-globaltrade",
    contact_type: "BOTH",
    business_name: "Global Trade Logistics",
    legal_name: "Global Trade & Logistics PLC",
    email: "finance@globaltrade.com",
    phone: "+44 20 8946 0123",
    primary_contact_name: "Sarah Jenkins",
    primary_contact_email: "s.jenkins@globaltrade.com",
    payment_terms_name: "End of next month",
    status: "ACTIVE",
    currency: "GBP",
    reference: "PAR-00009",
    updated_at: new Date().toISOString(),
  },
  {
    id: "c4-archived",
    contact_type: "CUSTOMER",
    business_name: "Old Legacy Ventures Ltd",
    legal_name: "Old Legacy Ventures Limited",
    email: "info@legacyventures.co.uk",
    phone: "+44 113 496 0541",
    primary_contact_name: "Tom Vance",
    primary_contact_email: "tom@legacyventures.co.uk",
    payment_terms_name: "Due immediately",
    status: "ARCHIVED",
    currency: "GBP",
    reference: "CUS-00012",
    updated_at: new Date(Date.now() - 86400000 * 30).toISOString(),
  },
];

export default function ContactListView({
  initialType = "ALL",
  pageTitle,
  subtitle,
}: ContactListViewProps) {
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [contacts, setContacts] = useState<Contact[]>(DEMO_CONTACTS);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"ALL" | "CUSTOMER" | "SUPPLIER" | "BOTH" | "ARCHIVED">(
    initialType === "ALL" ? "ALL" : initialType
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [actionMenuOpenId, setActionMenuOpenId] = useState<string | null>(null);

  // Fetch active organisation
  useEffect(() => {
    async function loadOrg() {
      try {
        const res = await fetch("/api/v1/organisations/");
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) {
            setActiveOrgId(orgs[0].id);
          }
        }
      } catch {
        // Fallback to demo mode
      }
    }
    loadOrg();
  }, []);

  // Fetch live contacts from backend
  const fetchContacts = async (orgId: string) => {
    setLoading(true);
    try {
      const typeParam = activeTab === "ALL" || activeTab === "ARCHIVED" ? "" : `contact_type=${activeTab}&`;
      const statusParam = activeTab === "ARCHIVED" ? "status=ARCHIVED&" : "status=ACTIVE&";
      const searchParam = searchQuery.trim() ? `search=${encodeURIComponent(searchQuery.trim())}&` : "";
      const url = `/api/v1/organisations/${orgId}/contacts?${typeParam}${statusParam}${searchParam}page_size=100`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          setContacts(data.items);
        } else if (!searchQuery.trim() && activeTab === "ALL") {
          // If the org has no contacts yet, show demo contacts as starting sample
          setContacts(DEMO_CONTACTS);
        } else {
          setContacts([]);
        }
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrgId) {
      fetchContacts(activeOrgId);
    }
  }, [activeOrgId, activeTab, searchQuery]);

  // Tab counts
  const allCount = contacts.filter((c) => c.status === "ACTIVE").length;
  const customerCount = contacts.filter((c) => c.contact_type === "CUSTOMER" && c.status === "ACTIVE").length;
  const supplierCount = contacts.filter((c) => c.contact_type === "SUPPLIER" && c.status === "ACTIVE").length;
  const bothCount = contacts.filter((c) => c.contact_type === "BOTH" && c.status === "ACTIVE").length;
  const archivedCount = contacts.filter((c) => c.status === "ARCHIVED").length;

  // Filtered contacts
  const filteredContacts = useMemo(() => {
    return contacts.filter((c) => {
      // Tab filtering
      if (activeTab === "ARCHIVED") {
        if (c.status !== "ARCHIVED") return false;
      } else {
        if (c.status === "ARCHIVED") return false;
        if (activeTab !== "ALL" && c.contact_type !== activeTab) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = c.business_name.toLowerCase().includes(q);
        const matchEmail = c.email?.toLowerCase().includes(q) || false;
        const matchPerson = c.primary_contact_name?.toLowerCase().includes(q) || false;
        const matchRef = c.reference?.toLowerCase().includes(q) || false;
        if (!matchName && !matchEmail && !matchPerson && !matchRef) return false;
      }

      return true;
    });
  }, [contacts, activeTab, searchQuery]);

  // Selection
  const isAllSelected =
    filteredContacts.length > 0 &&
    filteredContacts.every((c) => selectedIds.has(c.id));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredContacts.map((c) => c.id)));
    }
  };

  const toggleSelectOne = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleArchiveToggle = async (id: string) => {
    const contact = contacts.find((c) => c.id === id);
    const isArchived = contact?.status === "ARCHIVED";
    const endpoint = isArchived ? "restore" : "archive";

    // Optimistic local update
    setContacts((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, status: isArchived ? "ACTIVE" : "ARCHIVED" }
          : c
      )
    );
    setActionMenuOpenId(null);

    if (activeOrgId && !id.startsWith("c")) {
      try {
        await fetch(`/api/v1/organisations/${activeOrgId}/contacts/${id}/${endpoint}`, {
          method: "POST",
        });
      } catch {
        // Revert on failure
        if (activeOrgId) fetchContacts(activeOrgId);
      }
    }
  };

  const handleBatchArchive = async () => {
    const idsToArchive = Array.from(selectedIds);
    setContacts((prev) =>
      prev.map((c) => (selectedIds.has(c.id) ? { ...c, status: "ARCHIVED" } : c))
    );
    setSelectedIds(new Set());

    if (activeOrgId) {
      for (const id of idsToArchive) {
        if (!id.startsWith("c")) {
          fetch(`/api/v1/organisations/${activeOrgId}/contacts/${id}/archive`, { method: "POST" }).catch(() => {});
        }
      }
    }
  };

  const handleBatchExport = () => {
    const csvContent =
      "data:text/csv;charset=utf-8,ID,Business Name,Type,Email,Phone,Primary Contact,Payment Terms,Status\n" +
      filteredContacts
        .filter((c) => selectedIds.size === 0 || selectedIds.has(c.id))
        .map(
          (c) =>
            `"${c.id}","${c.business_name}","${c.contact_type}","${c.email || ""}","${
              c.phone || ""
            }","${c.primary_contact_name || ""}","${c.payment_terms_name || ""}","${c.status}"`
        )
        .join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `contacts_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-5">
      {/* ── Page Header (Xero Title + Action Buttons) ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{pageTitle}</h1>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/app/contacts/import"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
          >
            <Upload className="h-3.5 w-3.5 text-slate-500" />
            Import CSV
          </Link>
          <button
            type="button"
            onClick={handleBatchExport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-colors"
          >
            <Download className="h-3.5 w-3.5 text-slate-500" />
            Export CSV
          </button>
          <Link
            href="/app/contacts/new"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Contact
          </Link>
        </div>
      </div>

      {/* ── Summary KPI Cards (Xero-style KPI Metrics) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Total Contacts
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{contacts.length}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{allCount} active relations</p>
          </div>
          <div className="h-9 w-9 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center">
            <Users className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-sky-600 uppercase tracking-wider">
              Customers
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{customerCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Sales invoice recipients</p>
          </div>
          <div className="h-9 w-9 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
            <Building2 className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-purple-600 uppercase tracking-wider">
              Suppliers
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{supplierCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Bill & expense payees</p>
          </div>
          <div className="h-9 w-9 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
            <Truck className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">
              Dual Purpose
            </p>
            <p className="text-xl font-bold text-slate-900 mt-1">{bothCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Two-way trade partners</p>
          </div>
          <div className="h-9 w-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Building className="h-4 w-4" />
          </div>
        </div>
      </div>

      {/* ── Main Data Workspace Card ── */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
        {/* Horizontal Navigation Sub-Tabs (Signature Xero Contact Tabs) */}
        <div className="flex items-center border-b border-slate-200 px-4 pt-1 bg-white overflow-x-auto">
          {[
            { id: "ALL", label: "All Contacts", count: allCount },
            { id: "CUSTOMER", label: "Customers", count: customerCount },
            { id: "SUPPLIER", label: "Suppliers", count: supplierCount },
            { id: "BOTH", label: "Dual Purpose", count: bothCount },
            { id: "ARCHIVED", label: "Archived", count: archivedCount },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id as any);
                  setSelectedIds(new Set());
                }}
                className={`py-3 px-3.5 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 flex-shrink-0 ${
                  isActive
                    ? "border-[#0073B7] text-[#0073B7] font-bold"
                    : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`text-[11px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Toolbar (Search, Filters & Batch Action Bar) */}
        <div className="p-3.5 border-b border-slate-200 bg-slate-50/60 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-72">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search contacts by name, email, or ref..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-md bg-white border border-slate-300 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-sm transition-all"
              />
            </div>

            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2 animate-in fade-in duration-150">
                <span className="text-xs font-semibold text-slate-700 bg-sky-50 border border-sky-200 px-2.5 py-1 rounded-md">
                  {selectedIds.size} selected
                </span>
                {activeTab !== "ARCHIVED" ? (
                  <button
                    type="button"
                    onClick={handleBatchArchive}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 hover:bg-slate-50 text-xs font-medium text-amber-700 shadow-sm transition-colors"
                  >
                    <Archive className="h-3.5 w-3.5 text-amber-600" />
                    Archive
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleBatchArchive}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 hover:bg-slate-50 text-xs font-medium text-emerald-700 shadow-sm transition-colors"
                  >
                    <RotateCcw className="h-3.5 w-3.5 text-emerald-600" />
                    Restore
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleBatchExport}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-slate-300 hover:bg-slate-50 text-xs font-medium text-slate-700 shadow-sm transition-colors"
                >
                  <Download className="h-3.5 w-3.5 text-slate-500" />
                  Export
                </button>
              </div>
            )}
          </div>

          <div className="text-xs text-slate-500">
            Showing <strong className="text-slate-800">{filteredContacts.length}</strong> of{" "}
            {contacts.length} contacts
          </div>
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-[11px] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={toggleSelectAll}
                    className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                  />
                </th>
                <th className="px-4 py-3">Contact Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Primary Contact</th>
                <th className="px-4 py-3">Email & Telephone</th>
                <th className="px-4 py-3">Payment Terms</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredContacts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <Users className="h-8 w-8 mx-auto text-slate-300 mb-2" />
                    <p className="font-semibold text-slate-700">No contacts found</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {searchQuery
                        ? "Try clearing your search query."
                        : "No contacts in this directory yet."}
                    </p>
                    <Link
                      href="/app/contacts/new"
                      className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 rounded-md bg-[#0073B7] text-white text-xs font-semibold"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Add Contact
                    </Link>
                  </td>
                </tr>
              ) : (
                filteredContacts.map((contact) => {
                  const isSelected = selectedIds.has(contact.id);
                  const isMenuOpen = actionMenuOpenId === contact.id;

                  return (
                    <tr
                      key={contact.id}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isSelected ? "bg-sky-50/40" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="px-4 py-3.5 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelectOne(contact.id)}
                          className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                        />
                      </td>

                      {/* Business Name with Avatar */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                            {contact.business_name.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <Link
                              href={`/app/contacts/${contact.id}`}
                              className="font-semibold text-slate-900 hover:text-[#0073B7] transition-colors"
                            >
                              {contact.business_name}
                            </Link>
                            {contact.reference && (
                              <p className="text-[10px] text-slate-400 font-mono">
                                Ref: {contact.reference}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Relationship Type */}
                      <td className="px-4 py-3.5">
                        {contact.contact_type === "CUSTOMER" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                            <Building2 className="h-3 w-3" />
                            Customer
                          </span>
                        )}
                        {contact.contact_type === "SUPPLIER" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                            <Truck className="h-3 w-3" />
                            Supplier
                          </span>
                        )}
                        {contact.contact_type === "BOTH" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <Users className="h-3 w-3" />
                            Dual-Purpose
                          </span>
                        )}
                      </td>

                      {/* Primary Person */}
                      <td className="px-4 py-3.5">
                        <div className="text-slate-800 font-medium">
                          {contact.primary_contact_name || "-"}
                        </div>
                        {contact.primary_contact_email && (
                          <div className="text-[11px] text-slate-400">
                            {contact.primary_contact_email}
                          </div>
                        )}
                      </td>

                      {/* Email & Phone */}
                      <td className="px-4 py-3.5">
                        {contact.email && (
                          <div className="text-slate-700 flex items-center gap-1">
                            <Mail className="h-3 w-3 text-slate-400" />
                            {contact.email}
                          </div>
                        )}
                        {contact.phone && (
                          <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                            <Phone className="h-3 w-3 text-slate-400" />
                            {contact.phone}
                          </div>
                        )}
                      </td>

                      {/* Payment Terms */}
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center gap-1 text-[11px] text-slate-700 font-mono bg-slate-100 px-2 py-0.5 rounded">
                          <CreditCard className="h-3 w-3 text-slate-500" />
                          {contact.payment_terms_name || "30 days"}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5">
                        {contact.status === "ACTIVE" ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-medium text-xs">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-700 font-medium text-xs">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                            Archived
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right relative">
                        <button
                          type="button"
                          onClick={() =>
                            setActionMenuOpenId(isMenuOpen ? null : contact.id)
                          }
                          className="p-1 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>

                        {isMenuOpen && (
                          <div className="absolute right-4 mt-1 w-36 rounded-md bg-white border border-slate-200 shadow-lg py-1 z-30 text-left animate-in fade-in duration-100">
                            <Link
                              href={`/app/contacts/${contact.id}`}
                              className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                            >
                              <Eye className="h-3.5 w-3.5 text-slate-400" />
                              View Details
                            </Link>
                            <Link
                              href={`/app/contacts/${contact.id}/edit`}
                              className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                            >
                              <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                              Edit Contact
                            </Link>
                            <button
                              type="button"
                              onClick={() => handleArchiveToggle(contact.id)}
                              className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                            >
                              {contact.status === "ACTIVE" ? (
                                <>
                                  <Archive className="h-3.5 w-3.5 text-amber-500" />
                                  Archive
                                </>
                              ) : (
                                <>
                                  <RotateCcw className="h-3.5 w-3.5 text-emerald-500" />
                                  Restore
                                </>
                              )}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Pagination Bar */}
        <div className="p-3.5 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing <strong className="text-slate-800">1</strong> to{" "}
            <strong className="text-slate-800">{filteredContacts.length}</strong> of{" "}
            {filteredContacts.length} results
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled
              className="px-2.5 py-1 rounded border border-slate-200 text-slate-400 cursor-not-allowed bg-slate-50"
            >
              Previous
            </button>
            <button
              type="button"
              className="px-2.5 py-1 rounded border border-sky-500 bg-sky-50 text-[#0073B7] font-semibold"
            >
              1
            </button>
            <button
              type="button"
              disabled
              className="px-2.5 py-1 rounded border border-slate-200 text-slate-400 cursor-not-allowed bg-slate-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
