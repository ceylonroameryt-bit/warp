"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import DashboardLayout from "@/components/DashboardLayout";
import BillStatusBadge from "@/components/BillStatusBadge";
import {
  Building2,
  Truck,
  Users,
  Mail,
  Phone,
  Globe,
  MapPin,
  CreditCard,
  FileText,
  Paperclip,
  Clock,
  Edit,
  Archive,
  RotateCcw,
  ArrowLeft,
  Plus,
  Trash2,
  CheckCircle2,
  ShieldCheck,
  Send,
  Download,
  Building,
  User,
  MoreVertical,
  ChevronDown,
  Receipt,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

export default function ContactDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [activeTab, setActiveTab] = useState<
    "overview" | "people" | "addresses" | "financial" | "documents" | "notes" | "activity" | "bills"
  >("overview");

  const [supplierBills, setSupplierBills] = useState<any[]>([]);
  const [loadingBills, setLoadingBills] = useState(false);

  // Sample contact data state
  const [contact, setContact] = useState({
    id: id || "c1-apex",
    contact_type: "CUSTOMER" as "CUSTOMER" | "SUPPLIER" | "BOTH",
    business_name: "Apex Innovations Ltd",
    legal_name: "Apex Innovations Limited",
    email: "accounts@apexinnovations.co.uk",
    phone: "+44 20 7946 0912",
    mobile: "+44 7700 900123",
    website: "https://apexinnovations.co.uk",
    company_number: "12345678",
    vat_number: "GB123456789",
    tax_identifier: "UTR-88271109",
    currency: "GBP",
    payment_terms_name: "30 days",
    reference: "CUS-00128",
    credit_limit: 10000,
    status: "ACTIVE" as "ACTIVE" | "ARCHIVED",
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-17T14:30:00Z",
    people: [
      {
        id: "p1",
        first_name: "Jane",
        last_name: "Doe",
        job_title: "Finance Director",
        email: "jane@apexinnovations.co.uk",
        phone: "+44 20 7946 0913",
        is_primary: true,
      },
      {
        id: "p2",
        first_name: "Arthur",
        last_name: "Pendleton",
        job_title: "Managing Director",
        email: "arthur@apexinnovations.co.uk",
        phone: "+44 20 7946 0910",
        is_primary: false,
      },
    ],
    addresses: [
      {
        id: "a1",
        address_type: "BILLING",
        line1: "100 Bishopsgate",
        line2: "Floor 14",
        city: "London",
        county: "Greater London",
        postcode: "EC2N 4AG",
        country: "GB",
      },
      {
        id: "a2",
        address_type: "SHIPPING",
        line1: "Unit 3, Apex Logistics Park",
        city: "Dartford",
        county: "Kent",
        postcode: "DA1 5FS",
        country: "GB",
      },
    ],
    notes: [
      {
        id: "n1",
        content: "Customer requested all invoices be sent with Purchase Order numbers attached.",
        author: "Alice Owner",
        created_at: "2026-09-05T11:20:00Z",
      },
      {
        id: "n2",
        content: "Credit limit verified via Companies House search. Approved up to £10,000.",
        author: "Bob Accountant",
        created_at: "2026-09-02T09:15:00Z",
      },
    ],
    documents: [
      {
        id: "d1",
        filename: "Apex_NDA_Signed_2026.pdf",
        size: "245 KB",
        created_at: "2026-09-01T14:00:00Z",
      },
    ],
    activity: [
      {
        id: "act-1",
        action: "Updated contact details",
        user: "Bob Accountant",
        timestamp: "Yesterday at 14:30",
      },
      {
        id: "act-2",
        action: "Added billing address: 100 Bishopsgate, London",
        user: "Alice Owner",
        timestamp: "Sep 01, 2026 at 10:15",
      },
      {
        id: "act-3",
        action: "Contact created",
        user: "Alice Owner",
        timestamp: "Sep 01, 2026 at 10:00",
      },
    ],
  });

  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);

  // Load active organisation
  useEffect(() => {
    async function loadOrg() {
      try {
        const res = await fetch("/api/v1/organisations/");
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) setActiveOrgId(orgs[0].id);
        }
      } catch {
        // Fallback
      }
    }
    loadOrg();
  }, []);

  // Fetch live contact details
  useEffect(() => {
    async function fetchContact() {
      if (!activeOrgId || !id || id.startsWith("c")) return;
      try {
        const res = await fetch(`/api/v1/organisations/${activeOrgId}/contacts/${id}`);
        if (res.ok) {
          const data = await res.json();
          setContact((prev) => ({
            ...prev,
            ...data,
            people: data.people || [],
            addresses: data.addresses || [],
            notes: (data.internal_notes || []).map((n: any) => ({
              id: n.id,
              content: n.content,
              author: n.created_by_name || "Team Member",
              created_at: n.created_at,
            })),
          }));
        }
      } catch {
        // Fallback to initial demo data
      }
    }
    fetchContact();
  }, [activeOrgId, id]);

  const [newNote, setNewNote] = useState("");

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;

    const noteContent = newNote.trim();
    setNewNote("");

    // Optimistic local add
    const tempNote = {
      id: `n-${Date.now()}`,
      content: noteContent,
      author: "You",
      created_at: new Date().toISOString(),
    };

    setContact((prev) => ({
      ...prev,
      notes: [tempNote, ...prev.notes],
    }));

    if (activeOrgId && !id.startsWith("c")) {
      try {
        await fetch(`/api/v1/organisations/${activeOrgId}/contacts/${id}/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: noteContent }),
        });
      } catch {
        // Ignored
      }
    }
  };

  const toggleArchive = async () => {
    const isArchived = contact.status === "ARCHIVED";
    const endpoint = isArchived ? "restore" : "archive";

    setContact((prev) => ({
      ...prev,
      status: isArchived ? "ACTIVE" : "ARCHIVED",
    }));

    if (activeOrgId && !id.startsWith("c")) {
      try {
        await fetch(`/api/v1/organisations/${activeOrgId}/contacts/${id}/${endpoint}`, {
          method: "POST",
        });
      } catch {
        // Ignored
      }
    }
  };

  useEffect(() => {
    async function fetchBills() {
      if (!activeOrgId || !id || id.startsWith("c")) return;
      setLoadingBills(true);
      try {
        const res = await fetch(`/api/v1/organisations/${activeOrgId}/bills?supplier_id=${id}&page_size=50`);
        if (res.ok) {
          const data = await res.json();
          setSupplierBills(data.items || []);
        }
      } catch {
        // Fallback
      } finally {
        setLoadingBills(false);
      }
    }
    fetchBills();
  }, [activeOrgId, id]);

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-5">
        {/* Back Link */}
        <Link
          href="/app/contacts"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Contacts
        </Link>

        {/* ── Contact Header Banner (Xero style profile card) ── */}
        <div className="p-6 rounded-lg border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="h-14 w-14 rounded-full bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center font-bold text-xl flex-shrink-0">
              {contact.business_name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  {contact.business_name}
                </h1>
                {contact.contact_type === "CUSTOMER" && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                    Customer
                  </span>
                )}
                {contact.contact_type === "SUPPLIER" && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                    Supplier
                  </span>
                )}
                {contact.contact_type === "BOTH" && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Customer & Supplier
                  </span>
                )}
                {contact.status === "ACTIVE" ? (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-amber-700 font-medium">
                    <span className="h-2 w-2 rounded-full bg-amber-500" />
                    Archived
                  </span>
                )}
              </div>
              {contact.legal_name && (
                <p className="text-xs text-slate-500 mt-0.5">{contact.legal_name}</p>
              )}
              <div className="flex items-center gap-4 mt-2.5 text-xs text-slate-600 flex-wrap">
                {contact.email && (
                  <span className="flex items-center gap-1 text-slate-600">
                    <Mail className="h-3.5 w-3.5 text-slate-400" />
                    {contact.email}
                  </span>
                )}
                {contact.phone && (
                  <span className="flex items-center gap-1 text-slate-600">
                    <Phone className="h-3.5 w-3.5 text-slate-400" />
                    {contact.phone}
                  </span>
                )}
                {contact.reference && (
                  <span className="font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px]">
                    Ref: {contact.reference}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleArchive}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-colors"
            >
              {contact.status === "ACTIVE" ? (
                <>
                  <Archive className="h-3.5 w-3.5 text-amber-600" />
                  Archive
                </>
              ) : (
                <>
                  <RotateCcw className="h-3.5 w-3.5 text-emerald-600" />
                  Restore
                </>
              )}
            </button>
            <Link
              href={`/app/contacts/${id}/edit`}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all"
            >
              <Edit className="h-3.5 w-3.5" />
              Edit Contact
            </Link>
          </div>
        </div>

        {/* ── Sub-navigation Horizontal Tabs (Signature Xero Contact Tabs) ── */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <div className="flex items-center border-b border-slate-200 px-4 bg-white overflow-x-auto">
            {[
              { id: "overview", label: "Overview" },
              ...(contact.contact_type === "SUPPLIER" || contact.contact_type === "BOTH"
                ? [{ id: "bills", label: `Bills (${supplierBills.length})` }]
                : []),
              { id: "people", label: `People (${contact.people.length})` },
              { id: "addresses", label: `Addresses (${contact.addresses.length})` },
              { id: "financial", label: "Financial Details" },
              { id: "documents", label: `Files (${contact.documents.length})` },
              { id: "notes", label: `Notes (${contact.notes.length})` },
              { id: "activity", label: "History" },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-3 px-3.5 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 flex-shrink-0 ${
                    isActive
                      ? "border-[#0073B7] text-[#0073B7]"
                      : "border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="p-6">
            {/* TAB: Overview */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Card: Business Details */}
                <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Company & Registration
                  </h3>
                  <dl className="grid grid-cols-2 gap-y-2 text-xs">
                    <dt className="text-slate-500 font-medium">Company Reg No:</dt>
                    <dd className="text-slate-900 font-mono">{contact.company_number || "-"}</dd>
                    <dt className="text-slate-500 font-medium">VAT Number:</dt>
                    <dd className="text-slate-900 font-mono">{contact.vat_number || "-"}</dd>
                    <dt className="text-slate-500 font-medium">Tax Identifier (UTR):</dt>
                    <dd className="text-slate-900 font-mono">{contact.tax_identifier || "-"}</dd>
                    <dt className="text-slate-500 font-medium">Website:</dt>
                    <dd className="text-[#0073B7] truncate">
                      <a href={contact.website} target="_blank" rel="noreferrer">
                        {contact.website || "-"}
                      </a>
                    </dd>
                  </dl>
                </div>

                {/* Right Card: Financial Terms */}
                <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Credit & Payment Terms
                  </h3>
                  <dl className="grid grid-cols-2 gap-y-2 text-xs">
                    <dt className="text-slate-500 font-medium">Default Currency:</dt>
                    <dd className="text-slate-900 font-semibold">{contact.currency}</dd>
                    <dt className="text-slate-500 font-medium">Payment Terms:</dt>
                    <dd className="text-slate-900 font-medium">{contact.payment_terms_name}</dd>
                    <dt className="text-slate-500 font-medium">Credit Limit:</dt>
                    <dd className="text-slate-900 font-medium">
                      £{contact.credit_limit.toLocaleString()}
                    </dd>
                    <dt className="text-slate-500 font-medium">Account Code:</dt>
                    <dd className="text-slate-900 font-mono">{contact.reference}</dd>
                  </dl>
                </div>

                {/* Primary Person Preview */}
                <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Primary Contact Person
                  </h3>
                  {contact.people[0] ? (
                    <div className="text-xs space-y-1">
                      <p className="font-bold text-slate-900">
                        {contact.people[0].first_name} {contact.people[0].last_name}
                      </p>
                      <p className="text-slate-500">{contact.people[0].job_title}</p>
                      <p className="text-slate-700">{contact.people[0].email}</p>
                      <p className="text-slate-700">{contact.people[0].phone}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No primary person assigned.</p>
                  )}
                </div>

                {/* Billing Address Preview */}
                <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Postal / Billing Address
                  </h3>
                  {contact.addresses[0] ? (
                    <div className="text-xs text-slate-700 space-y-0.5">
                      <p className="font-semibold text-slate-900">{contact.addresses[0].line1}</p>
                      {contact.addresses[0].line2 && <p>{contact.addresses[0].line2}</p>}
                      <p>
                        {contact.addresses[0].city}, {contact.addresses[0].postcode}
                      </p>
                      <p className="text-slate-500">{contact.addresses[0].country}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No address on file.</p>
                  )}
                </div>
              </div>
            )}

            {/* TAB: Supplier Bills */}
            {activeTab === "bills" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Supplier Bills & Payables</h3>
                    <p className="text-xs text-slate-500">
                      All purchase invoices recorded for {contact.business_name}
                    </p>
                  </div>
                  <Link
                    href={`/app/purchases/bills/new?supplier_id=${id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    New Bill
                  </Link>
                </div>

                {loadingBills ? (
                  <div className="py-12 text-center text-xs text-slate-500">Loading supplier bills...</div>
                ) : supplierBills.length === 0 ? (
                  <div className="py-12 text-center border-2 border-dashed border-slate-200 rounded-lg space-y-2">
                    <Receipt className="h-8 w-8 text-slate-300 mx-auto" />
                    <p className="text-xs font-semibold text-slate-700">No bills recorded for this supplier</p>
                    <p className="text-[11px] text-slate-400">
                      Create a supplier bill to track expenses and payments owed.
                    </p>
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                        <tr>
                          <th className="py-2.5 px-3">Bill #</th>
                          <th className="py-2.5 px-3">Supplier Inv #</th>
                          <th className="py-2.5 px-3">Bill Date</th>
                          <th className="py-2.5 px-3">Due Date</th>
                          <th className="py-2.5 px-3 text-right">Total</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {supplierBills.map((b) => (
                          <tr key={b.id} className="hover:bg-slate-50">
                            <td className="py-2.5 px-3 font-mono font-medium text-slate-900">
                              {b.internal_bill_number || "Draft"}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-slate-700">{b.supplier_invoice_number}</td>
                            <td className="py-2.5 px-3 text-slate-600">{b.bill_date ? b.bill_date.split("T")[0] : "—"}</td>
                            <td className="py-2.5 px-3 text-slate-600">{b.due_date ? b.due_date.split("T")[0] : "—"}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                              £{parseFloat(b.total).toFixed(2)}
                            </td>
                            <td className="py-2.5 px-3">
                              <BillStatusBadge status={b.status} effectiveStatus={b.effective_status} />
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <Link
                                href={`/app/purchases/bills/${b.id}`}
                                className="text-xs font-semibold text-[#0073B7] hover:underline"
                              >
                                View
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* TAB: People */}
            {activeTab === "people" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Contact Persons</h3>
                  <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-sm">
                    <Plus className="h-3.5 w-3.5 text-slate-500" />
                    Add Person
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {contact.people.map((p) => (
                    <div
                      key={p.id}
                      className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2 relative"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-bold text-slate-900 text-sm">
                          {p.first_name} {p.last_name}
                        </p>
                        {p.is_primary && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 font-semibold border border-sky-200">
                            Primary Contact
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500">{p.job_title}</p>
                      <div className="text-xs text-slate-700 space-y-1 pt-2 border-t border-slate-200">
                        <p className="flex items-center gap-1.5">
                          <Mail className="h-3.5 w-3.5 text-slate-400" />
                          {p.email}
                        </p>
                        <p className="flex items-center gap-1.5">
                          <Phone className="h-3.5 w-3.5 text-slate-400" />
                          {p.phone}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: Addresses */}
            {activeTab === "addresses" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Addresses</h3>
                  <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-sm">
                    <Plus className="h-3.5 w-3.5 text-slate-500" />
                    Add Address
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {contact.addresses.map((a) => (
                    <div
                      key={a.id}
                      className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                          {a.address_type} Address
                        </span>
                      </div>
                      <div className="text-xs text-slate-700 space-y-0.5 pt-1">
                        <p className="font-bold text-slate-900">{a.line1}</p>
                        {a.line2 && <p>{a.line2}</p>}
                        <p>
                          {a.city}, {a.county && `${a.county}, `}
                          {a.postcode}
                        </p>
                        <p className="text-slate-500">{a.country}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: Financial Details */}
            {activeTab === "financial" && (
              <div className="space-y-4 max-w-xl">
                <h3 className="text-sm font-bold text-slate-900">Accounting & Financial Settings</h3>
                <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-slate-200">
                    <span className="text-slate-500">Default Currency</span>
                    <span className="font-semibold text-slate-900">{contact.currency}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-200">
                    <span className="text-slate-500">Payment Terms</span>
                    <span className="font-semibold text-slate-900">{contact.payment_terms_name}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-200">
                    <span className="text-slate-500">Credit Limit</span>
                    <span className="font-semibold text-slate-900">
                      £{contact.credit_limit.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-slate-500">Accounting Reference</span>
                    <span className="font-mono font-semibold text-slate-900">
                      {contact.reference}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: Documents / Files */}
            {activeTab === "documents" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Files & Attachments</h3>
                  <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-sm">
                    <Paperclip className="h-3.5 w-3.5 text-slate-500" />
                    Attach File
                  </button>
                </div>

                <div className="space-y-2">
                  {contact.documents.map((d) => (
                    <div
                      key={d.id}
                      className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-slate-400" />
                        <div>
                          <p className="font-semibold text-slate-900">{d.filename}</p>
                          <p className="text-[11px] text-slate-400">{d.size}</p>
                        </div>
                      </div>
                      <button className="px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium">
                        Download
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: Notes */}
            {activeTab === "notes" && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-900">Internal Notes</h3>

                <form onSubmit={handleAddNote} className="space-y-2">
                  <textarea
                    rows={2}
                    placeholder="Add an internal note about this contact..."
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                  <button
                    type="submit"
                    className="px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm"
                  >
                    Add Note
                  </button>
                </form>

                <div className="space-y-3 pt-2">
                  {contact.notes.map((n) => (
                    <div
                      key={n.id}
                      className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between text-slate-400 text-[11px]">
                        <span className="font-semibold text-slate-700">{n.author}</span>
                        <span>{new Date(n.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-800">{n.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB: Activity History */}
            {activeTab === "activity" && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-900">Audit & Change History</h3>
                <div className="space-y-3">
                  {contact.activity.map((act) => (
                    <div
                      key={act.id}
                      className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs"
                    >
                      <div>
                        <p className="font-medium text-slate-900">{act.action}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">By {act.user}</p>
                      </div>
                      <span className="text-[11px] text-slate-400">{act.timestamp}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
