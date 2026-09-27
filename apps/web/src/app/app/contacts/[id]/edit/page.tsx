"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import DashboardLayout from "@/components/DashboardLayout";
import {
  Building2,
  Truck,
  Users,
  AlertTriangle,
  ArrowLeft,
  Check,
  CreditCard,
  MapPin,
  User,
  ShieldCheck,
  FileText,
  Save,
  Archive,
  RotateCcw,
} from "lucide-react";

export default function EditContactPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [contactType, setContactType] = useState<"CUSTOMER" | "SUPPLIER" | "BOTH">("CUSTOMER");
  const [status, setStatus] = useState<"ACTIVE" | "ARCHIVED">("ACTIVE");

  // Basic Information
  const [businessName, setBusinessName] = useState("Apex Innovations Ltd");
  const [legalName, setLegalName] = useState("Apex Innovations Limited");
  const [reference, setReference] = useState("CUS-00128");
  const [email, setEmail] = useState("accounts@apexinnovations.co.uk");
  const [phone, setPhone] = useState("+44 20 7946 0912");
  const [mobile, setMobile] = useState("+44 7700 900123");
  const [website, setWebsite] = useState("https://apexinnovations.co.uk");

  // Company & Tax Details
  const [companyNumber, setCompanyNumber] = useState("12345678");
  const [vatNumber, setVatNumber] = useState("GB123456789");
  const [taxIdentifier, setTaxIdentifier] = useState("UTR-88271109");

  // Financial Settings
  const [currency, setCurrency] = useState("GBP");
  const [paymentTerms, setPaymentTerms] = useState("30 days");
  const [creditLimit, setCreditLimit] = useState("10000");

  // Primary Contact Person
  const [personFirstName, setPersonFirstName] = useState("Jane");
  const [personLastName, setPersonLastName] = useState("Doe");
  const [personJobTitle, setPersonJobTitle] = useState("Finance Director");
  const [personEmail, setPersonEmail] = useState("jane@apexinnovations.co.uk");
  const [personPhone, setPersonPhone] = useState("+44 20 7946 0913");

  // Addresses
  const [billingLine1, setBillingLine1] = useState("100 Bishopsgate");
  const [billingLine2, setBillingLine2] = useState("Floor 14");
  const [billingCity, setBillingCity] = useState("London");
  const [billingPostcode, setBillingPostcode] = useState("EC2N 4AG");
  const [billingCountry, setBillingCountry] = useState("GB");

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName.trim()) {
      alert("Contact Name is required.");
      return;
    }

    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setSavedNotice(true);
      setTimeout(() => {
        router.push(`/app/contacts/${id}`);
      }, 800);
    }, 500);
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Breadcrumb & Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Link
              href={`/app/contacts/${id}`}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors mb-1.5"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Contact
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
              Edit Contact: {businessName}
              {status === "ARCHIVED" && (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-normal">
                  Archived
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Update organization contact details, payment terms, and addresses.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setStatus(status === "ACTIVE" ? "ARCHIVED" : "ACTIVE")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-colors"
            >
              {status === "ACTIVE" ? (
                <>
                  <Archive className="h-3.5 w-3.5 text-amber-600" />
                  Archive Contact
                </>
              ) : (
                <>
                  <RotateCcw className="h-3.5 w-3.5 text-emerald-600" />
                  Restore to Active
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all disabled:opacity-50"
            >
              {isSaving ? "Saving..." : savedNotice ? "Saved!" : "Save Changes"}
            </button>
          </div>
        </div>

        {savedNotice && (
          <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
            <Check className="h-4 w-4" />
            Contact updated successfully. Redirecting...
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-5">
          {/* Section 1: Relationship Type */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-3">
            <label className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Contact Type
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: "CUSTOMER", title: "Customer", desc: "Sales invoices & receipts", icon: Building2 },
                { id: "SUPPLIER", title: "Supplier", desc: "Purchase bills & expenses", icon: Truck },
                { id: "BOTH", title: "Both (Dual Purpose)", desc: "Two-way trading partner", icon: Users },
              ].map((t) => {
                const Icon = t.icon;
                const isSelected = contactType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setContactType(t.id as any)}
                    className={`p-3.5 rounded-lg border text-left transition-all ${
                      isSelected
                        ? "bg-sky-50/70 border-[#0073B7] ring-1 ring-[#0073B7]"
                        : "bg-white border-slate-200 text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <Icon className={`h-4 w-4 ${isSelected ? "text-[#0073B7]" : "text-slate-400"}`} />
                      {isSelected && <Check className="h-4 w-4 text-[#0073B7]" />}
                    </div>
                    <p className="font-bold text-xs mt-2 text-slate-900">{t.title}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{t.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: Contact Details */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Contact Details
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Contact Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Legal / Registered Name
                </label>
                <input
                  type="text"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Account Number / Code
                </label>
                <input
                  type="text"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 font-mono focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Telephone</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Website</label>
                <input
                  type="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Company Registration Number
                </label>
                <input
                  type="text"
                  value={companyNumber}
                  onChange={(e) => setCompanyNumber(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  VAT Registration Number
                </label>
                <input
                  type="text"
                  value={vatNumber}
                  onChange={(e) => setVatNumber(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Financial Details */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Financial & Payment Terms
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                >
                  <option value="GBP">GBP - British Pound (£)</option>
                  <option value="USD">USD - US Dollar ($)</option>
                  <option value="EUR">EUR - Euro (€)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Payment Terms
                </label>
                <select
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                >
                  <option value="Due immediately">Due immediately</option>
                  <option value="7 days">Net 7 Days</option>
                  <option value="14 days">Net 14 Days</option>
                  <option value="30 days">Net 30 Days (Standard)</option>
                  <option value="60 days">Net 60 Days</option>
                  <option value="End of next month">End of next month</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Credit Limit (£)
                </label>
                <input
                  type="number"
                  value={creditLimit}
                  onChange={(e) => setCreditLimit(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Section 4: Primary Person */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Primary Contact Person
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">First Name</label>
                <input
                  type="text"
                  value={personFirstName}
                  onChange={(e) => setPersonFirstName(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Last Name</label>
                <input
                  type="text"
                  value={personLastName}
                  onChange={(e) => setPersonLastName(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Job Title</label>
                <input
                  type="text"
                  value={personJobTitle}
                  onChange={(e) => setPersonJobTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Direct Email</label>
                <input
                  type="email"
                  value={personEmail}
                  onChange={(e) => setPersonEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Section 5: Postal Address */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Postal / Billing Address
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Street Address
                </label>
                <input
                  type="text"
                  value={billingLine1}
                  onChange={(e) => setBillingLine1(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">City / Town</label>
                <input
                  type="text"
                  value={billingCity}
                  onChange={(e) => setBillingCity(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Postal Code</label>
                <input
                  type="text"
                  value={billingPostcode}
                  onChange={(e) => setBillingPostcode(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              href={`/app/contacts/${id}`}
              className="px-4 py-2 rounded-md border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-sm"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isSaving}
              className="px-5 py-2 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
