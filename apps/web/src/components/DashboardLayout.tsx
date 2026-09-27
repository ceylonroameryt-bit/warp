"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Users,
  Building2,
  FileText,
  CreditCard,
  Settings,
  Plus,
  Search,
  ChevronDown,
  UploadCloud,
  Menu,
  X,
  Bell,
  HelpCircle,
  TrendingUp,
  Receipt,
  Sparkles,
  LogOut,
  ShieldCheck,
  Check,
  Percent,
  BookOpen,
  Layers,
  FileSpreadsheet,
} from "lucide-react";

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeOrgName?: string;
}

export default function DashboardLayout({
  children,
  activeOrgName = "Acme Corp UK Ltd",
}: DashboardLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();

  // Dropdown states
  const [orgDropdownOpen, setOrgDropdownOpen] = useState(false);
  const [quickCreateOpen, setQuickCreateOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchFocused, setSearchFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const orgRef = useRef<HTMLDivElement>(null);
  const createRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (orgRef.current && !orgRef.current.contains(event.target as Node)) {
        setOrgDropdownOpen(false);
      }
      if (createRef.current && !createRef.current.contains(event.target as Node)) {
        setQuickCreateOpen(false);
      }
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Top Nav Items (Xero Modern Accounting Hierarchy)
  interface NavTab {
    name: string;
    href: string;
    active: boolean;
    badge?: string;
  }

  const topNavTabs: NavTab[] = [
    {
      name: "Dashboard",
      href: "/app/dashboard",
      active: pathname === "/app/dashboard" || pathname === "/app",
    },
    {
      name: "Business (Sales)",
      href: "/app/sales/invoices",
      active: pathname.startsWith("/app/sales"),
    },
    {
      name: "Purchases (Bills)",
      href: "/app/purchases/bills",
      active: pathname.startsWith("/app/purchases"),
    },
    {
      name: "Payments",
      href: "/app/payments",
      active: pathname.startsWith("/app/payments"),
    },
    {
      name: "Documents",
      href: "/app/documents",
      active: pathname.startsWith("/app/documents"),
      badge: "Smart AI",
    },
    {
      name: "Contacts",
      href: "/app/contacts",
      active: pathname.startsWith("/app/contacts"),
    },
    {
      name: "Accounting",
      href: "/app/accounting/chart-of-accounts",
      active: pathname.startsWith("/app/accounting"),
    },
    {
      name: "Reports",
      href: "/app/reports",
      active: pathname.startsWith("/app/reports"),
    },
    {
      name: "Accounting Settings",
      href: "/app/settings/payment-terms",
      active: pathname.startsWith("/app/settings"),
    },
  ];

  return (
    <div className="min-h-screen bg-[#F4F6F9] text-slate-800 flex flex-col font-sans antialiased">
      {/* ── TOP NAVIGATION BAR (Signature Xero / Deep Navy Header) ── */}
      <header className="bg-[#0A2540] text-white sticky top-0 z-40 shadow-sm">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          {/* Left: Brand + Org Switcher + Main Nav */}
          <div className="flex items-center gap-6">
            {/* Logo */}
            <Link
              href="/app/dashboard"
              className="flex items-center gap-2 group py-1"
              title="Warp Ladger Commercial Accounting"
            >
              <div className="h-8 w-8 rounded-lg bg-[#00A3C4] flex items-center justify-center font-black text-white text-base shadow-sm group-hover:bg-[#00bfe6] transition-colors">
                L
              </div>
              <div className="flex flex-col">
                <span className="font-bold tracking-tight text-white text-sm leading-tight">
                  Ladger
                </span>
                <span className="text-[10px] text-sky-300 font-medium tracking-wide">
                  ACCOUNTING
                </span>
              </div>
            </Link>

            {/* Vertical Divider */}
            <div className="h-6 w-[1px] bg-slate-700/60 hidden sm:block" />

            {/* Organisation Selector Dropdown */}
            <div className="relative" ref={orgRef}>
              <button
                type="button"
                onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-slate-800/70 text-slate-100 transition-colors text-xs font-semibold"
              >
                <div className="h-5 w-5 rounded bg-sky-600/30 text-sky-300 border border-sky-400/30 flex items-center justify-center text-[10px] font-bold">
                  AC
                </div>
                <span className="max-w-[150px] truncate">{activeOrgName}</span>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </button>

              {orgDropdownOpen && (
                <div className="absolute left-0 mt-2 w-64 rounded-lg bg-white border border-slate-200 shadow-xl py-2 z-50 text-slate-800 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1.5 border-b border-slate-100">
                    <p className="text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
                      Current Organisation
                    </p>
                    <p className="text-xs font-bold text-slate-900 mt-0.5">{activeOrgName}</p>
                    <p className="text-[10px] text-slate-500">Co. No: 12345678 · VAT: GB123456789</p>
                  </div>
                  <div className="py-1">
                    <div className="px-3 py-1.5 flex items-center justify-between text-xs hover:bg-slate-50 cursor-pointer">
                      <span className="font-medium text-slate-700">Acme Holdings Ltd</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        Holding
                      </span>
                    </div>
                  </div>
                  <div className="pt-1 mt-1 border-t border-slate-100 px-3">
                    <Link
                      href="/app/settings/payment-terms"
                      onClick={() => setOrgDropdownOpen(false)}
                      className="text-xs text-sky-600 hover:text-sky-700 font-medium py-1 block"
                    >
                      Organisation Settings
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Main Navigation Tabs */}
            <nav className="hidden lg:flex items-center gap-1">
              {topNavTabs.map((tab) => (
                <Link
                  key={tab.name}
                  href={tab.href}
                  className={`px-3 py-4 text-xs font-medium transition-all relative flex items-center gap-1.5 ${
                    tab.active
                      ? "text-white font-semibold after:content-[''] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#00A3C4]"
                      : "text-slate-300 hover:text-white hover:bg-slate-800/40"
                  }`}
                >
                  {tab.name}
                  {tab.badge && (
                    <span className="text-[9px] font-semibold bg-[#00A3C4]/30 text-sky-200 border border-[#00A3C4]/40 px-1 py-0.2 rounded">
                      {tab.badge}
                    </span>
                  )}
                </Link>
              ))}
            </nav>
          </div>

          {/* Right: Quick Action "+" + Search + Help + User */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Search Input */}
            <div className="relative hidden md:block">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search Ladger... (/)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setSearchFocused(false)}
                className={`pl-8 pr-3 py-1.5 text-xs rounded-md bg-slate-800/80 border border-slate-700 text-white placeholder-slate-400 focus:outline-none focus:bg-slate-800 focus:border-[#00A3C4] transition-all ${
                  searchFocused ? "w-64" : "w-48"
                }`}
              />
            </div>

            {/* Quick Create "+" Dropdown (Vibrant Xero Cyan) */}
            <div className="relative" ref={createRef}>
              <button
                type="button"
                onClick={() => setQuickCreateOpen(!quickCreateOpen)}
                className="h-8 w-8 rounded-md bg-[#00A3C4] hover:bg-[#008ba8] text-white flex items-center justify-center shadow-sm transition-colors"
                title="Create New..."
              >
                <Plus className="h-5 w-5" />
              </button>

              {quickCreateOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-lg bg-white border border-slate-200 shadow-xl py-2 z-50 text-slate-800 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1 text-[11px] font-semibold uppercase text-slate-400 tracking-wider">
                    Invoicing & Transactions
                  </div>
                  <Link
                    href="/app/sales/invoices/new"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <FileText className="h-4 w-4 text-[#0073B7]" />
                    New Sales Invoice
                  </Link>
                  <Link
                    href="/app/purchases/bills/new"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <Receipt className="h-4 w-4 text-[#0073B7]" />
                    New Supplier Bill
                  </Link>
                  <Link
                    href="/app/documents?upload=true"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <Sparkles className="h-4 w-4 text-[#00A3C4]" />
                    Capture Invoice / Receipt
                  </Link>
                  <Link
                    href="/app/payments/new"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <CreditCard className="h-4 w-4 text-emerald-600" />
                    Record Payment
                  </Link>

                  <Link
                    href="/app/accounting/journals/new"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <BookOpen className="h-4 w-4 text-[#0073B7]" />
                    New Manual Journal
                  </Link>

                  <div className="px-3 py-1 mt-1 border-t border-slate-100 text-[11px] font-semibold uppercase text-slate-400 tracking-wider">
                    Contacts & Directory
                  </div>
                  <Link
                    href="/app/contacts/new"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <Users className="h-4 w-4 text-[#0073B7]" />
                    New Contact
                  </Link>
                  <Link
                    href="/app/contacts/import"
                    onClick={() => setQuickCreateOpen(false)}
                    className="flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-sky-50 hover:text-sky-700 transition-colors"
                  >
                    <UploadCloud className="h-4 w-4 text-slate-600" />
                    Import Contacts CSV
                  </Link>
                </div>
              )}
            </div>

            {/* Notifications */}
            <button
              type="button"
              className="h-8 w-8 rounded-md hover:bg-slate-800/80 text-slate-300 hover:text-white flex items-center justify-center transition-colors relative"
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-[#00A3C4]" />
            </button>

            {/* Help / Support */}
            <button
              type="button"
              className="h-8 w-8 rounded-md hover:bg-slate-800/80 text-slate-300 hover:text-white flex items-center justify-center transition-colors hidden sm:flex"
              title="Help & Support"
            >
              <HelpCircle className="h-4 w-4" />
            </button>

            {/* User Profile Avatar */}
            <div className="relative" ref={userRef}>
              <button
                type="button"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-1.5 p-1 rounded-md hover:bg-slate-800/80 transition-colors"
              >
                <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-[#00A3C4] to-blue-700 text-white flex items-center justify-center text-xs font-bold shadow-inner">
                  PS
                </div>
                <ChevronDown className="h-3 w-3 text-slate-400 hidden sm:block" />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 rounded-lg bg-white border border-slate-200 shadow-xl py-2 z-50 text-slate-800 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1.5 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900">Poorna Sujampathi</p>
                    <p className="text-[11px] text-slate-500 truncate">owner@warpladger.com</p>
                    <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                      Organisation Owner
                    </span>
                  </div>
                  <div className="py-1">
                    <Link
                      href="/app/settings/payment-terms"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      <CreditCard className="h-3.5 w-3.5 text-slate-400" />
                      Payment Terms
                    </Link>
                    <Link
                      href="/app/settings/tax-rates"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                    >
                      <Percent className="h-3.5 w-3.5 text-slate-400" />
                      Tax Rates
                    </Link>
                  </div>
                  <div className="pt-1 border-t border-slate-100">
                    <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50 cursor-pointer font-medium">
                      <LogOut className="h-3.5 w-3.5 text-rose-500" />
                      Sign Out
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Mobile Hamburger */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden h-8 w-8 rounded-md hover:bg-slate-800 text-slate-300 flex items-center justify-center"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Slide-down Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden bg-slate-900 border-t border-slate-800 px-4 py-3 space-y-2 animate-in slide-in-from-top-2 duration-150">
            {topNavTabs.map((tab) => (
              <Link
                key={tab.name}
                href={tab.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-md text-xs font-medium ${
                  tab.active ? "bg-[#00A3C4] text-white font-bold" : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                {tab.name}
              </Link>
            ))}
          </div>
        )}
      </header>

      {/* ── SECONDARY SUB-HEADER / WORKSPACE BAR (Context-sensitive Xero Header) ── */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between py-2.5 overflow-x-auto gap-4">
            
            {/* Dynamic Context Tabs */}
            <div className="flex items-center gap-1 text-xs">
              {/* Dashboard Sub-nav */}
              {(pathname === "/app/dashboard" || pathname === "/app") && (
                <>
                  <Link
                    href="/app/dashboard"
                    className="px-3 py-1.5 rounded-md font-semibold bg-slate-100 text-[#0073B7] transition-colors"
                  >
                    Dashboard Overview
                  </Link>
                  <Link
                    href="/app/sales/invoices"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Invoices
                  </Link>
                  <Link
                    href="/app/purchases/bills"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Bills to Pay
                  </Link>
                  <Link
                    href="/app/documents"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center gap-1"
                  >
                    <Sparkles className="h-3 w-3 text-sky-500" />
                    AI Hubdoc Inbox
                  </Link>
                </>
              )}

              {/* Sales Sub-nav */}
              {pathname.startsWith("/app/sales") && (
                <>
                  <Link
                    href="/app/sales/invoices"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/sales/invoices")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Invoices
                  </Link>
                  <Link
                    href="/app/contacts/customers"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Customers
                  </Link>
                  <Link
                    href="/app/sales"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/sales"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Sales Overview
                  </Link>
                </>
              )}

              {/* Purchases Sub-nav */}
              {pathname.startsWith("/app/purchases") && (
                <>
                  <Link
                    href="/app/purchases/bills"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/purchases/bills")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Bills to Pay
                  </Link>
                  <Link
                    href="/app/purchases/approvals"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/purchases/approvals")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Awaiting Approval
                  </Link>
                  <Link
                    href="/app/contacts/suppliers"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Suppliers
                  </Link>
                  <Link
                    href="/app/purchases"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/purchases"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Purchases Overview
                  </Link>
                </>
              )}

              {/* Documents Sub-nav */}
              {pathname.startsWith("/app/documents") && (
                <>
                  <Link
                    href="/app/documents"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/documents"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    All Captured Documents
                  </Link>
                  <Link
                    href="/app/documents?filter=needs_review"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Needs Review
                  </Link>
                  <Link
                    href="/app/documents?filter=ready"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Ready for Draft Bill
                  </Link>
                  <Link
                    href="/app/documents?filter=completed"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Completed
                  </Link>
                </>
              )}

              {/* Contacts Sub-nav */}
              {pathname.startsWith("/app/contacts") && (
                <>
                  <Link
                    href="/app/contacts"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/contacts"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    All Contacts
                  </Link>
                  <Link
                    href="/app/contacts/customers"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/contacts/customers"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Customers
                  </Link>
                  <Link
                    href="/app/contacts/suppliers"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/contacts/suppliers"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Suppliers
                  </Link>
                  <Link
                    href="/app/contacts/import"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/contacts/import"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Import
                  </Link>
                </>
              )}

              {/* Settings Sub-nav */}
              {pathname.startsWith("/app/settings") && (
                <>
                  <Link
                    href="/app/settings/payment-terms"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/settings/payment-terms")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Payment Terms
                  </Link>
                  <Link
                    href="/app/settings/tax-rates"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/settings/tax-rates")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Tax Rates
                  </Link>
                  <Link
                    href="/app/settings/accounting-periods"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/settings/accounting-periods")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Period Locking
                  </Link>
                </>
              )}

              {/* Accounting Sub-nav */}
              {pathname.startsWith("/app/accounting") && (
                <>
                  <Link
                    href="/app/accounting/chart-of-accounts"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/accounting/chart-of-accounts")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Chart of Accounts
                  </Link>
                  <Link
                    href="/app/accounting/journals"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/accounting/journals")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Manual Journals
                  </Link>
                  <Link
                    href="/app/accounting/trial-balance"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/accounting/trial-balance")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Trial Balance
                  </Link>
                  <Link
                    href="/app/settings/accounting-periods"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Periods & Locks
                  </Link>
                </>
              )}

              {/* Reports Sub-nav */}
              {pathname.startsWith("/app/reports") && (
                <>
                  <Link
                    href="/app/reports"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname === "/app/reports"
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Reports Hub
                  </Link>
                  <Link
                    href="/app/reports/profit-and-loss"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/reports/profit-and-loss")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Profit & Loss
                  </Link>
                  <Link
                    href="/app/reports/balance-sheet"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/reports/balance-sheet")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Balance Sheet
                  </Link>
                  <Link
                    href="/app/reports/aged-receivables"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/reports/aged-receivables")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Aged Receivables
                  </Link>
                  <Link
                    href="/app/reports/aged-payables"
                    className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
                      pathname.startsWith("/app/reports/aged-payables")
                        ? "bg-slate-100 text-[#0073B7]"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    Aged Payables
                  </Link>
                  <Link
                    href="/app/accounting/trial-balance"
                    className="px-3 py-1.5 rounded-md font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                  >
                    Trial Balance
                  </Link>
                </>
              )}
            </div>

            {/* Context Primary Action Button (Xero Style) */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {pathname.startsWith("/app/reports") && (
                <Link
                  href="/app/accounting/journals/new"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Journal
                </Link>
              )}
              {pathname.startsWith("/app/sales") && (
                <Link
                  href="/app/sales/invoices/new"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Invoice
                </Link>
              )}

              {pathname.startsWith("/app/purchases") && (
                <Link
                  href="/app/purchases/bills/new"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Bill
                </Link>
              )}

              {pathname.startsWith("/app/accounting/journals") && (
                <Link
                  href="/app/accounting/journals/new"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Journal
                </Link>
              )}

              {pathname.startsWith("/app/documents") && (
                <Link
                  href="/app/documents?upload=true"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <UploadCloud className="h-3.5 w-3.5" />
                  Capture Invoice / Receipt
                </Link>
              )}

              {pathname.startsWith("/app/contacts") && (
                <Link
                  href="/app/contacts/new"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Contact
                </Link>
              )}

              {(pathname === "/app/dashboard" || pathname === "/app") && (
                <Link
                  href="/app/documents?upload=true"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Smart Upload
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT AREA ── */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-6">
        {children}
      </main>

      {/* ── FOOTER ── */}
      <footer className="border-t border-slate-200 bg-white py-4 text-xs text-slate-500">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Warp Ladger</span>
            <span>·</span>
            <span>Commercial Accounting Platform</span>
            <span>·</span>
            <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
              v0.3.0
            </span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span className="hover:text-slate-700 cursor-pointer">Security & Compliance</span>
            <span className="hover:text-slate-700 cursor-pointer">Audit Logging</span>
            <span className="hover:text-slate-700 cursor-pointer">Support</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
