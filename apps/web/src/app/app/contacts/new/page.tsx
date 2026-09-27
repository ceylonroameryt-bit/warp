"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  HelpCircle,
} from "lucide-react";

export default function NewContactPage() {
  const router = useRouter();
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [contactType, setContactType] = useState<"CUSTOMER" | "SUPPLIER" | "BOTH">("CUSTOMER");
  const [isQuickCreate, setIsQuickCreate] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Form Fields
  const [businessName, setBusinessName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [companyNumber, setCompanyNumber] = useState("");
  const [vatNumber, setVatNumber] = useState("");
  const [currency, setCurrency] = useState("GBP");
  const [paymentTerms, setPaymentTerms] = useState("30 days");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

  // Primary Contact
  const [personFirstName, setPersonFirstName] = useState("");
  const [personLastName, setPersonLastName] = useState("");
  const [personJobTitle, setPersonJobTitle] = useState("");
  const [personEmail, setPersonEmail] = useState("");

  // Billing Address
  const [addressLine1, setAddressLine1] = useState("");
  const [addressCity, setAddressCity] = useState("");
  const [addressPostcode, setAddressPostcode] = useState("");
  const [addressCountry, setAddressCountry] = useState("GB");

  // Duplicate warning state
  const [duplicateWarning, setDuplicateWarning] = useState<{
    found: boolean;
    name?: string;
    reason?: string;
  }>({ found: false });

  // Resolve active organisation
  React.useEffect(() => {
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

  // Real-time backend duplicate detection
  const runDuplicateCheck = async (name: string, vat: string, comp: string) => {
    if (!activeOrgId || (!name.trim() && !vat.trim() && !comp.trim())) {
      setDuplicateWarning({ found: false });
      return;
    }

    try {
      const res = await fetch(`/api/v1/organisations/${activeOrgId}/contacts/check-duplicates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: name.trim() || "Unspecified",
          vat_number: vat.trim() || null,
          company_number: comp.trim() || null,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.has_duplicates && data.matches.length > 0) {
          const m = data.matches[0];
          setDuplicateWarning({
            found: true,
            name: m.business_name,
            reason: m.message,
          });
          return;
        }
      }
      setDuplicateWarning({ found: false });
    } catch {
      // Ignored in preview
    }
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setBusinessName(val);
    runDuplicateCheck(val, vatNumber, companyNumber);
  };

  const handleVatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setVatNumber(val);
    runDuplicateCheck(businessName, val, companyNumber);
  };

  const handleCompanyNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setCompanyNumber(val);
    runDuplicateCheck(businessName, vatNumber, val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName.trim()) {
      setSubmitError("Please enter a Contact Name.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    if (activeOrgId) {
      try {
        const payload: any = {
          contact_type: contactType,
          business_name: businessName.trim(),
          legal_name: legalName.trim() || null,
          email: email.trim() || null,
          phone: phone.trim() || null,
          website: website.trim() || null,
          company_number: companyNumber.trim() || null,
          vat_number: vatNumber.trim() || null,
          currency: currency.trim() || "GBP",
          reference: reference.trim() || null,
          notes: notes.trim() || null,
        };

        if (personFirstName.trim()) {
          payload.primary_contact = {
            first_name: personFirstName.trim(),
            last_name: personLastName.trim() || null,
            job_title: personJobTitle.trim() || null,
            email: personEmail.trim() || null,
            is_primary: true,
          };
        }

        if (addressLine1.trim() && addressCity.trim()) {
          payload.billing_address = {
            address_type: "BILLING",
            line1: addressLine1.trim(),
            city: addressCity.trim(),
            postcode: addressPostcode.trim() || null,
            country_code: addressCountry.trim() || "GB",
            is_primary: true,
          };
        }

        const res = await fetch(`/api/v1/organisations/${activeOrgId}/contacts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.message || "Failed to create contact.");
        }

        router.push("/app/contacts");
      } catch (err: any) {
        setSubmitError(err.message || "Error submitting contact form.");
      } finally {
        setIsSubmitting(false);
      }
    } else {
      router.push("/app/contacts");
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Breadcrumb & Title */}
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/app/contacts"
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors mb-1.5"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Contacts
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Add New Contact</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Add a customer, supplier, or dual-purpose business partner.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsQuickCreate(!isQuickCreate)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                isQuickCreate
                  ? "bg-sky-50 border-sky-300 text-[#0073B7]"
                  : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {isQuickCreate ? "Switch to Full Form" : "Quick Add Mode"}
            </button>
          </div>
        </div>

        {/* Duplicate Warning Banner */}
        {duplicateWarning.found && (
          <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-3 shadow-sm">
            <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-amber-800">Duplicate Contact Warning</p>
              <p className="text-amber-700 mt-0.5">{duplicateWarning.reason}</p>
              <p className="text-slate-600 text-[11px] mt-1">
                Existing record:{" "}
                <strong className="text-slate-800 underline">{duplicateWarning.name}</strong>.
              </p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {submitError && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs shadow-sm">
            <p className="font-semibold">{submitError}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Section 1: Relationship Type */}
          <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-3">
            <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
              Relationship Type
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                {
                  type: "CUSTOMER" as const,
                  title: "Customer",
                  desc: "Send sales invoices and receive payments.",
                  icon: Users,
                  color: "text-blue-600 bg-blue-50 border-blue-200",
                },
                {
                  type: "SUPPLIER" as const,
                  title: "Supplier",
                  desc: "Receive bills, upload receipts and pay vendors.",
                  icon: Truck,
                  color: "text-amber-600 bg-amber-50 border-amber-200",
                },
                {
                  type: "BOTH" as const,
                  title: "Both (Customer & Supplier)",
                  desc: "Dual relationship for partners and subcontractors.",
                  icon: Building2,
                  color: "text-purple-600 bg-purple-50 border-purple-200",
                },
              ].map((t) => {
                const isSelected = contactType === t.type;
                const Icon = t.icon;
                return (
                  <button
                    key={t.type}
                    type="button"
                    onClick={() => setContactType(t.type)}
                    className={`p-3.5 rounded-lg border text-left transition-all relative ${
                      isSelected
                        ? "border-[#0073B7] bg-sky-50/50 shadow-sm ring-1 ring-[#0073B7]"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-3 right-3 h-4 w-4 rounded-full bg-[#0073B7] text-white flex items-center justify-center">
                        <Check className="h-2.5 w-2.5" />
                      </div>
                    )}
                    <div>
                      <div
                        className={`h-7 w-7 rounded-md flex items-center justify-center ${t.color}`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <p className="font-bold text-xs mt-2 text-slate-900">{t.title}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{t.desc}</p>
                    </div>
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
                  placeholder="e.g. Acme Corp Ltd"
                  value={businessName}
                  onChange={handleNameChange}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Legal / Registered Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Corporation Limited"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Account Number / Code
                </label>
                <input
                  type="text"
                  placeholder="e.g. ACME-001"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 font-mono focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Primary Email
                </label>
                <input
                  type="email"
                  placeholder="accounts@acme.co.uk"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Telephone
                </label>
                <input
                  type="tel"
                  placeholder="+44 20 7946 0000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Website</label>
                <input
                  type="url"
                  placeholder="https://acme.co.uk"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Company Registration Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. 12345678"
                  value={companyNumber}
                  onChange={handleCompanyNumberChange}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  VAT Registration Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. GB123456789"
                  value={vatNumber}
                  onChange={handleVatChange}
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Primary Contact Person (Hidden in Quick Add) */}
          {!isQuickCreate && (
            <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Primary Person
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    First Name
                  </label>
                  <input
                    type="text"
                    placeholder="John"
                    value={personFirstName}
                    onChange={(e) => setPersonFirstName(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Last Name
                  </label>
                  <input
                    type="text"
                    placeholder="Smith"
                    value={personLastName}
                    onChange={(e) => setPersonLastName(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Job Title
                  </label>
                  <input
                    type="text"
                    placeholder="Director"
                    value={personJobTitle}
                    onChange={(e) => setPersonJobTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Direct Email
                  </label>
                  <input
                    type="email"
                    placeholder="john@acme.co.uk"
                    value={personEmail}
                    onChange={(e) => setPersonEmail(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Section 4: Address (Postal / Billing) */}
          {!isQuickCreate && (
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
                    placeholder="100 High Street"
                    value={addressLine1}
                    onChange={(e) => setAddressLine1(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    City / Town
                  </label>
                  <input
                    type="text"
                    placeholder="London"
                    value={addressCity}
                    onChange={(e) => setAddressCity(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    placeholder="EC1A 1BB"
                    value={addressPostcode}
                    onChange={(e) => setAddressPostcode(e.target.value)}
                    className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Section 5: Financial Details */}
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
                  placeholder="0.00"
                  className="w-full px-3 py-2 rounded-md bg-white border border-slate-300 text-xs text-slate-900 focus:outline-none focus:border-[#0073B7] focus:ring-1 focus:ring-[#0073B7] shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* Form Actions (Signature Xero bottom bar) */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              href="/app/contacts"
              className="px-4 py-2 rounded-md border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-sm"
            >
              Cancel
            </Link>
            <button
              type="submit"
              className="px-5 py-2 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              Save Contact
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
