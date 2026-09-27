"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  CreditCard,
  Plus,
  Search,
  Filter,
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Eye,
  Trash2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Wallet,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { PaymentStatusBadge, PaymentTypeBadge } from "@/components/PaymentStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "00000000-0000-0000-0000-000000000001";

interface Allocation {
  id: string;
  target_type: "INVOICE" | "BILL";
  invoice_id?: string;
  bill_id?: string;
  invoice_number?: string;
  bill_number?: string;
  amount: number | string;
  created_at: string;
}

interface Payment {
  id: string;
  payment_number: string;
  payment_type: "INCOMING" | "OUTGOING";
  contact_id?: string;
  contact_name?: string;
  bank_account_id?: string;
  bank_account_name?: string;
  payment_date: string;
  amount: number | string;
  allocated_amount: number | string;
  unallocated_amount: number | string;
  currency: string;
  payment_method: string;
  reference?: string;
  status: "DRAFT" | "POSTED" | "VOIDED" | "REFUNDED";
  void_reason?: string;
  voided_at?: string;
  allocations: Allocation[];
}

interface BankAccount {
  id: string;
  account_name: string;
  account_type: string;
  currency: string;
  account_number?: string;
  sort_code?: string;
  current_balance: number | string;
  opening_balance: number | string;
  is_default: boolean;
  active: boolean;
}

interface PaymentMetrics {
  total_incoming: number;
  total_outgoing: number;
  unallocated_incoming: number;
  unallocated_outgoing: number;
  payment_count: number;
}

function fmt(v: string | number | undefined, currency = "GBP") {
  if (v === undefined || v === null) return "£0.00";
  const n = typeof v === "string" ? parseFloat(v) : v;
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function PaymentsHubContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<"all" | "incoming" | "outgoing" | "banks">("all");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [metrics, setMetrics] = useState<PaymentMetrics>({
    total_incoming: 42500.0,
    total_outgoing: 18200.0,
    unallocated_incoming: 850.0,
    unallocated_outgoing: 0.0,
    payment_count: 24,
  });
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState<string>("");

  // Modals state
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [allocModalOpen, setAllocModalOpen] = useState(false);
  const [voidModalOpen, setVoidModalOpen] = useState(false);
  const [voidReason, setVoidReason] = useState("");
  const [voiding, setVoiding] = useState(false);
  const [voidError, setVoidError] = useState("");

  // Add Bank Modal state
  const [addBankModalOpen, setAddBankModalOpen] = useState(false);
  const [bankFormData, setBankFormData] = useState({
    account_name: "",
    account_type: "CHECKING",
    account_number: "",
    sort_code: "",
    currency: "GBP",
    opening_balance: 0,
    is_default: false,
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // 1. Fetch payments
      let url = `${API_BASE}/api/v1/organisations/${ORG_ID}/payments?limit=100`;
      if (activeTab === "incoming") url += `&payment_type=INCOMING`;
      if (activeTab === "outgoing") url += `&payment_type=OUTGOING`;
      if (statusFilter) url += `&status=${statusFilter}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;

      const resPay = await fetch(url, { headers });
      if (resPay.ok) {
        const data = await resPay.json();
        setPayments(data.items || []);
      } else {
        // Fallback demo dataset for visual demonstration
        setPayments([
          {
            id: "p-01",
            payment_number: "PAY-000001",
            payment_type: "INCOMING",
            contact_name: "Acme Corporation Ltd",
            bank_account_name: "Main Business Checking",
            payment_date: new Date().toISOString(),
            amount: 600.0,
            allocated_amount: 600.0,
            unallocated_amount: 0.0,
            currency: "GBP",
            payment_method: "BANK_TRANSFER",
            reference: "INV-101-SETTLED",
            status: "POSTED",
            allocations: [
              {
                id: "al-1",
                target_type: "INVOICE",
                invoice_number: "INV-000101",
                amount: 600.0,
                created_at: new Date().toISOString(),
              },
            ],
          },
          {
            id: "p-02",
            payment_number: "PAY-000002",
            payment_type: "OUTGOING",
            contact_name: "Consolidated Supplies PLC",
            bank_account_name: "Main Business Checking",
            payment_date: new Date(Date.now() - 86400000 * 2).toISOString(),
            amount: 750.0,
            allocated_amount: 750.0,
            unallocated_amount: 0.0,
            currency: "GBP",
            payment_method: "BANK_TRANSFER",
            reference: "BILL-PAY-001",
            status: "POSTED",
            allocations: [
              {
                id: "al-2",
                target_type: "BILL",
                bill_number: "BILL-000201",
                amount: 750.0,
                created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
              },
            ],
          },
          {
            id: "p-03",
            payment_number: "PAY-000003",
            payment_type: "INCOMING",
            contact_name: "Global Tech Services",
            bank_account_name: "Main Business Checking",
            payment_date: new Date(Date.now() - 86400000 * 4).toISOString(),
            amount: 1500.0,
            allocated_amount: 1000.0,
            unallocated_amount: 500.0,
            currency: "GBP",
            payment_method: "BANK_TRANSFER",
            reference: "ADVANCE-DEPOSIT",
            status: "POSTED",
            allocations: [
              {
                id: "al-3",
                target_type: "INVOICE",
                invoice_number: "INV-000105",
                amount: 1000.0,
                created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
              },
            ],
          },
        ]);
      }

      // 2. Fetch Bank Accounts
      const resBank = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/bank-accounts`, { headers });
      if (resBank.ok) {
        const bData = await resBank.json();
        setBankAccounts(bData || []);
      } else {
        setBankAccounts([
          {
            id: "bank-1",
            account_name: "Main Business Checking",
            account_type: "CHECKING",
            currency: "GBP",
            account_number: "•••• 5678",
            sort_code: "20-00-00",
            current_balance: 24850.0,
            opening_balance: 10000.0,
            is_default: true,
            active: true,
          },
          {
            id: "bank-2",
            account_name: "Corporate Reserve Savings",
            account_type: "SAVINGS",
            currency: "GBP",
            account_number: "•••• 8912",
            sort_code: "20-00-05",
            current_balance: 75000.0,
            opening_balance: 50000.0,
            is_default: false,
            active: true,
          },
        ]);
      }

      // 3. Fetch Metrics
      const resMet = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/payments/metrics`, { headers });
      if (resMet.ok) {
        const mData = await resMet.json();
        setMetrics(mData);
      }
    } catch (err) {
      console.error("Failed to load payments data:", err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, statusFilter, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleVoidPayment = async () => {
    if (!selectedPayment) return;
    if (!voidReason.trim()) {
      setVoidError("A clear audit void reason is mandatory.");
      return;
    }

    setVoiding(true);
    setVoidError("");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/payments/${selectedPayment.id}/void`, {
        method: "POST",
        headers,
        body: JSON.stringify({ reason: voidReason.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to void payment");
      }

      setVoidModalOpen(false);
      setSelectedPayment(null);
      setVoidReason("");
      fetchData();
    } catch (err: any) {
      setVoidError(err.message || "Failed to void payment");
    } finally {
      setVoiding(false);
    }
  };

  const handleCreateBankAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/v1/organisations/${ORG_ID}/bank-accounts`, {
        method: "POST",
        headers,
        body: JSON.stringify(bankFormData),
      });

      if (res.ok) {
        setAddBankModalOpen(false);
        setBankFormData({
          account_name: "",
          account_type: "CHECKING",
          account_number: "",
          sort_code: "",
          currency: "GBP",
          opening_balance: 0,
          is_default: false,
        });
        fetchData();
      }
    } catch (err) {
      console.error("Error creating bank account:", err);
    }
  };

  const totalBankBalance = bankAccounts.reduce((acc, b) => acc + (parseFloat(String(b.current_balance)) || 0), 0);

  return (
    <DashboardLayout>
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* ── HEADER ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                Phase 6 Commercial
              </span>
              <span className="text-xs text-slate-500">• Dual Ledger Settled</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">Payments & Allocations</h1>
            <p className="text-sm text-slate-500">
              Manage incoming customer receipts, outgoing supplier disbursements, and bank account balances.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setAddBankModalOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition shadow-sm"
            >
              <Building2 className="w-4 h-4 text-slate-500" />
              Add Bank Account
            </button>
            <Link
              href="/app/payments/new"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0A2540] hover:bg-[#081d33] rounded-lg shadow-sm transition"
            >
              <Plus className="w-4 h-4" />
              Record Payment
            </Link>
          </div>
        </div>

        {/* ── METRIC CARDS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Inflows */}
          <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Total Received</span>
              <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
                <ArrowDownLeft className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">{fmt(metrics.total_incoming)}</div>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-teal-700 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-teal-500" />
              Customer Sales Invoices Settled
            </div>
          </div>

          {/* Total Outflows */}
          <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Total Disbursed</span>
              <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">{fmt(metrics.total_outgoing)}</div>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-indigo-700 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Supplier Bills Disbursed
            </div>
          </div>

          {/* Unallocated Credit */}
          <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Unallocated Credits</span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                <Wallet className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">{fmt(metrics.unallocated_incoming)}</div>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-amber-700 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500" />
              Available Customer Prepayments
            </div>
          </div>

          {/* Bank Accounts Total */}
          <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Liquid Cash Balances</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
                <Building2 className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">{fmt(totalBankBalance)}</div>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-700 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Across {bankAccounts.length} Connected Accounts
            </div>
          </div>
        </div>

        {/* ── TABS & FILTERS ── */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-4 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-3">
            {/* Tabs */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab("all")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                  activeTab === "all" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                All Payments
              </button>
              <button
                onClick={() => setActiveTab("incoming")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "incoming" ? "bg-white text-teal-800 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <ArrowDownLeft className="w-3.5 h-3.5 text-teal-600" />
                Customer Receipts
              </button>
              <button
                onClick={() => setActiveTab("outgoing")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "outgoing" ? "bg-white text-indigo-800 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <ArrowUpRight className="w-3.5 h-3.5 text-indigo-600" />
                Supplier Payments
              </button>
              <button
                onClick={() => setActiveTab("banks")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "banks" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Building2 className="w-3.5 h-3.5 text-slate-600" />
                Bank Accounts ({bankAccounts.length})
              </button>
            </div>

            {/* Status Filter */}
            {activeTab !== "banks" && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="">All Statuses</option>
                  <option value="POSTED">Posted</option>
                  <option value="VOIDED">Voided</option>
                  <option value="DRAFT">Draft</option>
                </select>
              </div>
            )}
          </div>

          {/* Search bar */}
          {activeTab !== "banks" && (
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search by payment reference, number, or contact name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500 bg-slate-50/50"
              />
            </div>
          )}

          {/* ── PAYMENTS TABLE ── */}
          {activeTab !== "banks" ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-600 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-3">Payment #</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">Contact</th>
                    <th className="py-3 px-3">Bank Account</th>
                    <th className="py-3 px-3">Reference</th>
                    <th className="py-3 px-3 text-right">Amount</th>
                    <th className="py-3 px-3 text-right">Allocated</th>
                    <th className="py-3 px-3 text-right">Unallocated</th>
                    <th className="py-3 px-3 text-center">Status</th>
                    <th className="py-3 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {loading ? (
                    <tr>
                      <td colSpan={11} className="py-8 text-center text-slate-400">
                        Loading payments...
                      </td>
                    </tr>
                  ) : payments.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="py-8 text-center text-slate-500">
                        No payments found matching your criteria.
                      </td>
                    </tr>
                  ) : (
                    payments.map((p) => {
                      const unalloc = parseFloat(String(p.unallocated_amount)) || 0;
                      return (
                        <tr key={p.id} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-3 px-3 font-semibold text-slate-900 font-mono">
                            {p.payment_number}
                          </td>
                          <td className="py-3 px-3">
                            <PaymentTypeBadge type={p.payment_type} />
                          </td>
                          <td className="py-3 px-3 text-slate-600 whitespace-nowrap">
                            {fmtDate(p.payment_date)}
                          </td>
                          <td className="py-3 px-3 font-medium text-slate-800">
                            {p.contact_name || "—"}
                          </td>
                          <td className="py-3 px-3 text-slate-600">
                            {p.bank_account_name || "Cash / Direct"}
                          </td>
                          <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                            {p.reference || "—"}
                          </td>
                          <td className="py-3 px-3 text-right font-bold text-slate-900">
                            {fmt(p.amount, p.currency)}
                          </td>
                          <td className="py-3 px-3 text-right text-emerald-700 font-medium">
                            {fmt(p.allocated_amount, p.currency)}
                          </td>
                          <td className="py-3 px-3 text-right">
                            {unalloc > 0 ? (
                              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                {fmt(unalloc, p.currency)} Credit
                              </span>
                            ) : (
                              <span className="text-slate-400">£0.00</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <PaymentStatusBadge status={p.status} />
                          </td>
                          <td className="py-3 px-3 text-right whitespace-nowrap space-x-1">
                            {/* View Allocations */}
                            <button
                              onClick={() => {
                                setSelectedPayment(p);
                                setAllocModalOpen(true);
                              }}
                              className="p-1 text-slate-500 hover:text-sky-600 rounded hover:bg-slate-100 transition"
                              title="View Document Allocations"
                            >
                              <Eye className="w-4 h-4 inline" />
                            </button>

                            {/* Void Payment (Strictly for Posted payments) */}
                            {p.status === "POSTED" && (
                              <button
                                onClick={() => {
                                  setSelectedPayment(p);
                                  setVoidReason("");
                                  setVoidError("");
                                  setVoidModalOpen(true);
                                }}
                                className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition"
                                title="Void Payment & Rollback Allocations"
                              >
                                <Trash2 className="w-4 h-4 inline" />
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            /* ── BANK ACCOUNTS VIEW ── */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
              {bankAccounts.map((b) => (
                <div key={b.id} className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 relative">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-100 text-sky-800">
                      {b.account_type}
                    </span>
                    {b.is_default && (
                      <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Default Account
                      </span>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 text-sm">{b.account_name}</h3>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                      {b.sort_code ? `Sort: ${b.sort_code} • ` : ""}
                      {b.account_number ? `Account: ${b.account_number}` : ""}
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                    <span className="text-xs text-slate-500">Current Balance:</span>
                    <span className="text-base font-bold text-slate-900">{fmt(b.current_balance, b.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── ALLOCATIONS MODAL ── */}
        {allocModalOpen && selectedPayment && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Payment Allocations — {selectedPayment.payment_number}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Settled documents and target allocation audit trail.
                  </p>
                </div>
                <button
                  onClick={() => setAllocModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
                >
                  ✕
                </button>
              </div>

              <div className="bg-slate-50 rounded-lg p-3 text-xs space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Payment Amount:</span>
                  <span className="font-bold text-slate-900">{fmt(selectedPayment.amount, selectedPayment.currency)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Allocated:</span>
                  <span className="font-semibold text-emerald-700">{fmt(selectedPayment.allocated_amount, selectedPayment.currency)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Unallocated Credit:</span>
                  <span className="font-semibold text-amber-700">{fmt(selectedPayment.unallocated_amount, selectedPayment.currency)}</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Allocated Documents</h4>
                {selectedPayment.allocations && selectedPayment.allocations.length > 0 ? (
                  <div className="space-y-2">
                    {selectedPayment.allocations.map((a) => (
                      <div
                        key={a.id}
                        className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded-lg text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              a.target_type === "INVOICE" ? "bg-teal-50 text-teal-700" : "bg-indigo-50 text-indigo-700"
                            }`}
                          >
                            {a.target_type}
                          </span>
                          <span className="font-mono font-semibold text-slate-800">
                            {a.invoice_number || a.bill_number || "Document"}
                          </span>
                        </div>
                        <span className="font-bold text-slate-900">{fmt(a.amount, selectedPayment.currency)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 py-3 text-center bg-slate-50 rounded-lg">
                    This payment is currently held as an unallocated advance payment / credit.
                  </p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setAllocModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── VOID PAYMENT MODAL ── */}
        {voidModalOpen && selectedPayment && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-rose-100 space-y-4">
              <div className="flex items-center gap-3 text-rose-600">
                <div className="w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5 text-rose-600" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Void Payment</h3>
                  <p className="text-xs text-slate-500">Atomic allocation reversal</p>
                </div>
              </div>

              <div className="text-xs text-slate-600 bg-rose-50/50 p-3 rounded-lg border border-rose-100 leading-relaxed">
                Voiding <strong>{selectedPayment.payment_number}</strong> will automatically rollback{" "}
                <strong>{selectedPayment.allocations?.length || 0} allocation(s)</strong> and restore all target invoice
                and bill balances to their previous unpaid status.
              </div>

              {voidError && (
                <div className="p-3 bg-rose-50 text-rose-700 text-xs rounded-lg border border-rose-200">
                  {voidError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Reason for Voiding <span className="text-rose-500">*</span>
                </label>
                <textarea
                  value={voidReason}
                  onChange={(e) => setVoidReason(e.target.value)}
                  placeholder="e.g. Cheque returned unpaid by bank / Duplicate entry / Wrong customer"
                  rows={3}
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setVoidModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleVoidPayment}
                  disabled={voiding || !voidReason.trim()}
                  className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition disabled:opacity-50"
                >
                  {voiding ? "Voiding..." : "Confirm Void & Revert"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── ADD BANK ACCOUNT MODAL ── */}
        {addBankModalOpen && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900">Add Bank Account</h3>
                <button
                  onClick={() => setAddBankModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateBankAccount} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Account Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Barclays Current Account"
                    value={bankFormData.account_name}
                    onChange={(e) => setBankFormData({ ...bankFormData, account_name: e.target.value })}
                    className="w-full p-2 border border-slate-300 rounded-lg"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Account Type</label>
                    <select
                      value={bankFormData.account_type}
                      onChange={(e) => setBankFormData({ ...bankFormData, account_type: e.target.value })}
                      className="w-full p-2 border border-slate-300 rounded-lg bg-white"
                    >
                      <option value="CHECKING">Checking / Current</option>
                      <option value="SAVINGS">Savings</option>
                      <option value="CREDIT_CARD">Credit Card</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Currency</label>
                    <select
                      value={bankFormData.currency}
                      onChange={(e) => setBankFormData({ ...bankFormData, currency: e.target.value })}
                      className="w-full p-2 border border-slate-300 rounded-lg bg-white"
                    >
                      <option value="GBP">GBP (£)</option>
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Sort Code</label>
                    <input
                      type="text"
                      placeholder="20-00-00"
                      value={bankFormData.sort_code}
                      onChange={(e) => setBankFormData({ ...bankFormData, sort_code: e.target.value })}
                      className="w-full p-2 border border-slate-300 rounded-lg font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Account Number</label>
                    <input
                      type="text"
                      placeholder="12345678"
                      value={bankFormData.account_number}
                      onChange={(e) => setBankFormData({ ...bankFormData, account_number: e.target.value })}
                      className="w-full p-2 border border-slate-300 rounded-lg font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Opening Balance</label>
                  <input
                    type="number"
                    step="0.01"
                    value={bankFormData.opening_balance}
                    onChange={(e) =>
                      setBankFormData({ ...bankFormData, opening_balance: parseFloat(e.target.value) || 0 })
                    }
                    className="w-full p-2 border border-slate-300 rounded-lg"
                  />
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="checkbox"
                    id="is_default"
                    checked={bankFormData.is_default}
                    onChange={(e) => setBankFormData({ ...bankFormData, is_default: e.target.checked })}
                    className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <label htmlFor="is_default" className="text-slate-700 font-medium cursor-pointer">
                    Set as default business bank account
                  </label>
                </div>

                <div className="flex justify-end gap-2 pt-4">
                  <button
                    type="button"
                    onClick={() => setAddBankModalOpen(false)}
                    className="px-4 py-2 font-semibold text-slate-600 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 font-semibold text-white bg-[#0A2540] hover:bg-[#081d33] rounded-lg shadow-sm"
                  >
                    Save Bank Account
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

export default function PaymentsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Payments...</div>}>
      <PaymentsHubContent />
    </Suspense>
  );
}
