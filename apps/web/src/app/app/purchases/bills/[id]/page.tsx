"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  Edit3,
  ExternalLink,
  Eye,
  FileCheck,
  FileCode,
  FileText,
  HelpCircle,
  History,
  Info,
  Layers,
  Paperclip,
  Plus,
  Receipt,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Upload,
  X,
  XCircle,
  CreditCard,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import BillStatusBadge from "@/components/BillStatusBadge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface BillLine {
  id: string;
  position: number;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  discount_type?: string;
  discount_value?: string | number;
  net_amount: string | number;
  tax_amount: string | number;
  gross_amount: string | number;
  tax_rate_snapshot?: string | number;
  purchase_category?: string;
}

interface BillDocument {
  id: string;
  bill_id: string;
  file_id: string;
  document_type: string;
  checksum_sha256?: string;
  filename?: string;
  content_type?: string;
  size_bytes?: number;
  download_url?: string;
  created_at: string;
}

interface BillApprovalEvent {
  id: string;
  actor_user_id?: string;
  actor_name?: string;
  action: "SUBMITTED" | "APPROVED" | "REJECTED" | "RESUBMITTED";
  comment?: string;
  created_at: string;
}

interface BillDetail {
  id: string;
  organisation_id: string;
  supplier_id: string;
  supplier_name_snapshot?: string;
  supplier_email_snapshot?: string;
  supplier_vat_number_snapshot?: string;
  supplier_address_snapshot?: any;
  supplier_invoice_number: string;
  internal_bill_number?: string;
  status: string;
  effective_status: string;
  bill_date: string;
  due_date: string;
  currency: string;
  supplier_reference?: string;
  purchase_order_reference?: string;
  payment_terms_id?: string;
  subtotal: string | number;
  discount_total: string | number;
  tax_total: string | number;
  total: string | number;
  amount_paid: string | number;
  amount_due: string | number;
  notes?: string;
  internal_notes?: string;
  submitted_for_approval_at?: string;
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  voided_at?: string;
  void_reason?: string;
  created_at: string;
  updated_at: string;
  version: number;
  lines: BillLine[];
  documents: BillDocument[];
  approval_events: BillApprovalEvent[];
}

function fmt(val: string | number | undefined, currency = "GBP"): string {
  if (val === undefined || val === null) return "—";
  const num = typeof val === "string" ? parseFloat(val) : val;
  const sym = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${sym}${num.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function fmtDateTime(d: string | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtBytes(bytes?: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export default function BillDetailPage() {
  const params = useParams();
  const router = useRouter();
  const billId = params?.id as string;

  const [bill, setBill] = useState<BillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "lines" | "documents" | "approval" | "activity">("overview");

  // Document preview state
  const [activePreviewDoc, setActivePreviewDoc] = useState<BillDocument | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Workflow modals
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [submitComment, setSubmitComment] = useState("");

  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [approveComment, setApproveComment] = useState("");

  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const [voidModalOpen, setVoidModalOpen] = useState(false);
  const [voidReason, setVoidReason] = useState("");

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState<string>("ORIGINAL_INVOICE");
  const [uploading, setUploading] = useState(false);

  const [actionInProgress, setActionInProgress] = useState(false);
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  useEffect(() => {
    async function resolveOrg() {
      try {
        const res = await fetch("/api/v1/organisations/", { credentials: "include" });
        if (res.ok) {
          const orgs = await res.json();
          if (orgs.length > 0) {
            setActiveOrgId(orgs[0].id);
          }
        }
      } catch {
        // Fallback
      }
    }
    resolveOrg();
  }, []);

  const orgId = activeOrgId || ORG_ID;

  const fetchBill = async () => {
    if (!billId || !orgId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}`, {
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error("Failed to load bill");
      }
      const data: BillDetail = await res.json();
      setBill(data);

      // Select initial preview doc: prefer ORIGINAL_INVOICE, else first doc
      if (data.documents && data.documents.length > 0) {
        const orig = data.documents.find((d) => d.document_type === "ORIGINAL_INVOICE") || data.documents[0];
        setActivePreviewDoc(orig);
        fetchDocumentUrl(orig);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while loading this bill.");
    } finally {
      setLoading(false);
    }
  };

  const fetchDocumentUrl = async (doc: BillDocument) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/documents/${doc.id}/download`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setPreviewUrl(data.url);
      }
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    if (orgId) {
      fetchBill();
    }
  }, [billId, orgId]);

  // Handle Workflow Actions
  const handleSubmit = async () => {
    setActionInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ comment: submitComment || null }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to submit bill for approval");
        return;
      }
      setSubmitModalOpen(false);
      setSubmitComment("");
      await fetchBill();
    } catch {
      alert("Error submitting bill");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleApprove = async () => {
    setActionInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ comment: approveComment || null }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to approve bill");
        return;
      }
      setApproveModalOpen(false);
      setApproveComment("");
      await fetchBill();
    } catch {
      alert("Error approving bill");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert("Rejection reason is required.");
      return;
    }
    setActionInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to reject bill");
        return;
      }
      setRejectModalOpen(false);
      setRejectReason("");
      await fetchBill();
    } catch {
      alert("Error rejecting bill");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleVoid = async () => {
    if (!voidReason.trim()) {
      alert("Void reason is required.");
      return;
    }
    setActionInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/void`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ reason: voidReason }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to void bill");
        return;
      }
      setVoidModalOpen(false);
      setVoidReason("");
      await fetchBill();
    } catch {
      alert("Error voiding bill");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDeleteDraft = async () => {
    setActionInProgress(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to delete bill");
        return;
      }
      router.push("/app/purchases/bills");
    } catch {
      alert("Error deleting bill");
    } finally {
      setActionInProgress(false);
    }
  };

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("upload", uploadFile);
      formData.append("document_type", uploadDocType);

      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/documents`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to upload document");
        return;
      }

      setUploadModalOpen(false);
      setUploadFile(null);
      await fetchBill();
    } catch {
      alert("Error uploading document");
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm("Are you sure you want to remove this document?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/bills/${billId}/documents/${docId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || err.message || "Failed to remove document");
        return;
      }
      await fetchBill();
    } catch {
      alert("Error deleting document");
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#0073B7] border-t-transparent mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading supplier bill...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !bill) {
    return (
      <DashboardLayout>
        <div className="max-w-2xl mx-auto mt-12 p-8 bg-white border border-slate-200 rounded-lg text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto">
            <XCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Unable to load bill</h2>
          <p className="text-xs text-slate-600">{error || "The requested bill could not be found."}</p>
          <Link
            href="/app/purchases/bills"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Bills
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  const effectiveStatus = bill.effective_status || bill.status;
  const isDraft = bill.status === "DRAFT";
  const isAwaitingApproval = bill.status === "AWAITING_APPROVAL";
  const isRejected = bill.status === "REJECTED";
  const isApproved = bill.status === "APPROVED";
  const isVoid = bill.status === "VOID";
  const canVoid = isApproved && !isVoid;

  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto space-y-5 pb-12">
        {/* Back Link */}
        <div className="flex items-center justify-between">
          <Link
            href="/app/purchases/bills"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Supplier Bills
          </Link>
          <span className="text-[11px] text-slate-400 font-mono">ID: {bill.id}</span>
        </div>

        {/* Rejection Alert Banner */}
        {isRejected && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <p className="font-bold text-red-900">Bill Rejected</p>
              <p className="text-red-700">
                <span className="font-medium">Reason:</span> {bill.rejection_reason || "No reason specified"}
              </p>
              {bill.rejected_at && (
                <p className="text-[11px] text-red-600">Rejected on {fmtDateTime(bill.rejected_at)}</p>
              )}
            </div>
          </div>
        )}

        {/* Void Alert Banner */}
        {isVoid && (
          <div className="p-4 rounded-lg bg-slate-100 border border-slate-300 flex items-start gap-3">
            <XCircle className="h-5 w-5 text-slate-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <p className="font-bold text-slate-900">Bill Voided</p>
              <p className="text-slate-700">
                <span className="font-medium">Reason:</span> {bill.void_reason || "No reason specified"}
              </p>
              {bill.voided_at && (
                <p className="text-[11px] text-slate-500">Voided on {fmtDateTime(bill.voided_at)}</p>
              )}
            </div>
          </div>
        )}

        {/* ── Header Card ────────────────────────────────────── */}
        <div className="p-6 rounded-lg border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-lg bg-purple-50 border border-purple-100 text-purple-700 flex items-center justify-center flex-shrink-0">
              <Receipt className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                  {bill.internal_bill_number || "Draft Bill"}
                </h1>
                <BillStatusBadge status={bill.status} effectiveStatus={bill.effective_status} />
              </div>
              <div className="flex items-center gap-4 mt-2 text-xs text-slate-600 flex-wrap">
                <span className="font-semibold text-slate-900">
                  Supplier: {bill.supplier_name_snapshot || "Supplier"}
                </span>
                <span className="text-slate-300">•</span>
                <span>
                  Supplier Inv #: <strong className="font-mono text-slate-900">{bill.supplier_invoice_number}</strong>
                </span>
                <span className="text-slate-300">•</span>
                <span>Due: {fmtDate(bill.due_date)}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Draft Actions */}
            {isDraft && (
              <>
                <Link
                  href={`/app/purchases/bills/${bill.id}/edit`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
                >
                  <Edit3 className="h-3.5 w-3.5 text-slate-500" />
                  Edit Draft
                </Link>
                <button
                  onClick={() => setSubmitModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all"
                >
                  <Send className="h-3.5 w-3.5" />
                  Submit for Approval
                </button>
                <button
                  onClick={() => setDeleteModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white hover:bg-red-50 text-xs font-semibold text-red-600 border border-red-200 shadow-sm transition-all"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </>
            )}

            {/* Awaiting Approval Actions */}
            {isAwaitingApproval && (
              <>
                <Link
                  href={`/app/purchases/bills/${bill.id}/edit`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
                >
                  <Edit3 className="h-3.5 w-3.5 text-slate-500" />
                  Edit
                </Link>
                <button
                  onClick={() => setRejectModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-red-50 text-xs font-semibold text-red-600 border border-red-300 shadow-sm transition-all"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject
                </button>
                <button
                  onClick={() => setApproveModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white shadow-sm transition-all"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Approve Bill
                </button>
              </>
            )}

            {/* Rejected Actions */}
            {isRejected && (
              <>
                <Link
                  href={`/app/purchases/bills/${bill.id}/edit`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
                >
                  <Edit3 className="h-3.5 w-3.5 text-slate-500" />
                  Modify & Fix
                </Link>
                <button
                  onClick={() => setSubmitModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white shadow-sm transition-all"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Resubmit
                </button>
              </>
            )}

            {/* Approved / Payable Actions */}
            {(isApproved || bill.status === "PARTIALLY_PAID") && (
              <Link
                href={`/app/payments/new?type=OUTGOING&contact_id=${bill.supplier_id || ""}&bill_id=${bill.id}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white shadow-sm transition-all"
              >
                <CreditCard className="h-3.5 w-3.5" />
                Pay Bill
              </Link>
            )}
            {canVoid && (
              <button
                onClick={() => setVoidModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
              >
                <XCircle className="h-3.5 w-3.5 text-slate-400" />
                Void Bill
              </button>
            )}
          </div>
        </div>

        {/* ── Split Layout: Left Preview + Right Details ──────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Original Supplier Invoice Document Preview (5 cols) */}
          <div className="lg:col-span-5 bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden sticky top-6">
            <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Paperclip className="h-4 w-4 text-slate-500" />
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Original Supplier Document
                </h3>
              </div>
              <div className="flex items-center gap-1">
                {bill.documents && bill.documents.length > 0 && (
                  <span className="text-[11px] font-medium bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">
                    {bill.documents.length} {bill.documents.length === 1 ? "file" : "files"}
                  </span>
                )}
                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="p-1 text-slate-500 hover:text-slate-800 rounded transition-colors"
                  title="Attach another document"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Document Selector Tabs if multiple */}
            {bill.documents && bill.documents.length > 1 && (
              <div className="flex items-center gap-1 p-2 bg-slate-100/70 border-b border-slate-200 overflow-x-auto text-xs">
                {bill.documents.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => {
                      setActivePreviewDoc(doc);
                      fetchDocumentUrl(doc);
                    }}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium truncate max-w-[140px] transition-colors ${
                      activePreviewDoc?.id === doc.id
                        ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {doc.filename || "Document"}
                  </button>
                ))}
              </div>
            )}

            {/* Preview Box */}
            <div className="p-4">
              {activePreviewDoc ? (
                <div className="space-y-3">
                  {/* File Metadata Header */}
                  <div className="flex items-center justify-between text-xs bg-slate-50 p-2.5 rounded-md border border-slate-200">
                    <div className="truncate pr-2">
                      <p className="font-semibold text-slate-900 truncate">
                        {activePreviewDoc.filename || "Invoice Document"}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {activePreviewDoc.document_type} • {fmtBytes(activePreviewDoc.size_bytes)}
                      </p>
                    </div>
                    {previewUrl && (
                      <a
                        href={previewUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0073B7] hover:underline flex-shrink-0"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Open
                      </a>
                    )}
                  </div>

                  {/* Document View Canvas */}
                  <div className="rounded-lg border border-slate-200 overflow-hidden bg-slate-100 min-h-[380px] max-h-[500px] flex items-center justify-center relative">
                    {previewUrl ? (
                      activePreviewDoc.content_type?.includes("image") ? (
                        <img
                          src={previewUrl}
                          alt="Supplier Invoice Document"
                          className="max-h-[480px] w-auto object-contain mx-auto"
                        />
                      ) : activePreviewDoc.content_type?.includes("pdf") ? (
                        <iframe
                          src={`${previewUrl}#toolbar=0`}
                          title="Supplier Invoice Preview"
                          className="w-full h-[480px] border-none"
                        />
                      ) : (
                        <div className="text-center p-6 space-y-2">
                          <FileText className="h-12 w-12 text-slate-400 mx-auto" />
                          <p className="text-xs font-semibold text-slate-700">Preview not supported for this file type</p>
                          <a
                            href={previewUrl}
                            download={activePreviewDoc.filename}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-900 text-white text-xs font-semibold"
                          >
                            <Download className="h-3.5 w-3.5" />
                            Download File
                          </a>
                        </div>
                      )
                    ) : (
                      <div className="text-center p-6 space-y-2">
                        <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-400 border-t-transparent mx-auto" />
                        <p className="text-xs text-slate-500">Loading document preview...</p>
                      </div>
                    )}
                  </div>

                  {/* SHA-256 Checksum Card */}
                  {activePreviewDoc.checksum_sha256 && (
                    <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 text-[11px] space-y-1">
                      <div className="flex items-center gap-1 text-slate-500 font-medium">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                        <span>SHA-256 Verification Hash</span>
                      </div>
                      <p className="font-mono text-[10px] text-slate-700 break-all select-all">
                        {activePreviewDoc.checksum_sha256}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                /* Empty Document Placeholder */
                <div className="text-center py-12 px-4 space-y-3 border-2 border-dashed border-slate-200 rounded-lg">
                  <Receipt className="h-10 w-10 text-slate-300 mx-auto" />
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-slate-700">No original document attached</p>
                    <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                      Attach the supplier&apos;s invoice or receipt (PDF, JPG, PNG) for verification.
                    </p>
                  </div>
                  <button
                    onClick={() => setUploadModalOpen(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 border border-slate-300 shadow-sm transition-all"
                  >
                    <Upload className="h-3.5 w-3.5 text-slate-500" />
                    Attach Invoice
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Bill Details, Tabs & Line Items (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            {/* Navigation Tabs */}
            <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
              <div className="flex items-center border-b border-slate-200 px-4 bg-white overflow-x-auto">
                {[
                  { id: "overview", label: "Overview" },
                  { id: "lines", label: `Line Items (${bill.lines.length})` },
                  { id: "documents", label: `Documents (${bill.documents.length})` },
                  { id: "approval", label: `Approval History (${bill.approval_events.length})` },
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
                {/* ── TAB 1: OVERVIEW ──────────────────────────────── */}
                {activeTab === "overview" && (
                  <div className="space-y-6">
                    {/* Supplier Snapshot Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Supplier Information */}
                      <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2.5">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                          Supplier Information
                        </h4>
                        <div className="space-y-1 text-xs">
                          <p className="font-semibold text-slate-900 text-sm">
                            {bill.supplier_name_snapshot || "Supplier"}
                          </p>
                          {bill.supplier_email_snapshot && (
                            <p className="text-slate-600">{bill.supplier_email_snapshot}</p>
                          )}
                          {bill.supplier_vat_number_snapshot && (
                            <p className="text-slate-600">
                              VAT: <span className="font-mono">{bill.supplier_vat_number_snapshot}</span>
                            </p>
                          )}
                          {bill.supplier_address_snapshot && (
                            <p className="text-[11px] text-slate-500 pt-1">
                              {[
                                bill.supplier_address_snapshot.line1,
                                bill.supplier_address_snapshot.city,
                                bill.supplier_address_snapshot.postcode,
                              ]
                                .filter(Boolean)
                                .join(", ")}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Bill References & Terms */}
                      <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2.5">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                          Dates & References
                        </h4>
                        <dl className="grid grid-cols-2 gap-y-1.5 text-xs">
                          <dt className="text-slate-500">Bill Date:</dt>
                          <dd className="text-slate-900 font-medium">{fmtDate(bill.bill_date)}</dd>
                          <dt className="text-slate-500">Due Date:</dt>
                          <dd className="text-slate-900 font-medium">{fmtDate(bill.due_date)}</dd>
                          <dt className="text-slate-500">Supplier Inv #:</dt>
                          <dd className="font-mono text-slate-900">{bill.supplier_invoice_number}</dd>
                          {bill.purchase_order_reference && (
                            <>
                              <dt className="text-slate-500">PO Ref:</dt>
                              <dd className="font-mono text-slate-900">{bill.purchase_order_reference}</dd>
                            </>
                          )}
                          {bill.supplier_reference && (
                            <>
                              <dt className="text-slate-500">Supplier Ref:</dt>
                              <dd className="text-slate-900">{bill.supplier_reference}</dd>
                            </>
                          )}
                        </dl>
                      </div>
                    </div>

                    {/* Financial Summary Card */}
                    <div className="p-4 rounded-lg border border-slate-200 bg-white space-y-3">
                      <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                        Financial Totals
                      </h4>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between text-slate-600">
                          <span>Subtotal (Net)</span>
                          <span>{fmt(bill.subtotal, bill.currency)}</span>
                        </div>
                        {parseFloat(String(bill.discount_total || 0)) > 0 && (
                          <div className="flex justify-between text-emerald-600">
                            <span>Discount Total</span>
                            <span>-{fmt(bill.discount_total, bill.currency)}</span>
                          </div>
                        )}
                        <div className="flex justify-between text-slate-600">
                          <span>Tax / VAT</span>
                          <span>{fmt(bill.tax_total, bill.currency)}</span>
                        </div>
                        <div className="border-t border-slate-200 pt-2 flex justify-between text-base font-bold text-slate-900">
                          <span>Total Amount</span>
                          <span>{fmt(bill.total, bill.currency)}</span>
                        </div>
                        <div className="border-t border-dashed border-slate-200 pt-2 flex justify-between text-xs font-semibold text-slate-700">
                          <span>Amount Due</span>
                          <span className={parseFloat(String(bill.amount_due || 0)) > 0 ? "text-amber-700" : "text-emerald-600"}>
                            {fmt(bill.amount_due, bill.currency)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Notes */}
                    {bill.notes && (
                      <div className="space-y-1">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Notes</h4>
                        <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-200 whitespace-pre-wrap">
                          {bill.notes}
                        </p>
                      </div>
                    )}

                    {bill.internal_notes && (
                      <div className="space-y-1">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                          Internal Notes (Finance Only)
                        </h4>
                        <p className="text-xs text-amber-900 bg-amber-50/60 p-3 rounded border border-amber-200/80 whitespace-pre-wrap">
                          {bill.internal_notes}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* ── TAB 2: LINE ITEMS ────────────────────────────── */}
                {activeTab === "lines" && (
                  <div className="space-y-4">
                    <div className="overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                          <tr>
                            <th className="py-2.5 px-3">#</th>
                            <th className="py-2.5 px-3">Description</th>
                            <th className="py-2.5 px-3">Category</th>
                            <th className="py-2.5 px-3 text-right">Qty</th>
                            <th className="py-2.5 px-3 text-right">Unit Price</th>
                            <th className="py-2.5 px-3 text-right">Tax Rate</th>
                            <th className="py-2.5 px-3 text-right">Net</th>
                            <th className="py-2.5 px-3 text-right">Tax</th>
                            <th className="py-2.5 px-3 text-right">Gross</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {bill.lines.map((line, idx) => (
                            <tr key={line.id || idx} className="hover:bg-slate-50/50">
                              <td className="py-2.5 px-3 text-slate-400 font-mono">{idx + 1}</td>
                              <td className="py-2.5 px-3 font-medium text-slate-900">{line.description}</td>
                              <td className="py-2.5 px-3 text-slate-600">
                                {line.purchase_category ? (
                                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px]">
                                    {line.purchase_category}
                                  </span>
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono text-slate-700">{line.quantity}</td>
                              <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                                {fmt(line.unit_price, bill.currency)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-slate-600">
                                {line.tax_rate_snapshot !== undefined ? `${line.tax_rate_snapshot}%` : "—"}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                                {fmt(line.net_amount, bill.currency)}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono text-slate-500">
                                {fmt(line.tax_amount, bill.currency)}
                              </td>
                              <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-900">
                                {fmt(line.gross_amount, bill.currency)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Line totals recap */}
                    <div className="flex justify-end">
                      <div className="w-64 space-y-1.5 text-xs text-right">
                        <div className="flex justify-between text-slate-600">
                          <span>Subtotal:</span>
                          <span className="font-mono">{fmt(bill.subtotal, bill.currency)}</span>
                        </div>
                        <div className="flex justify-between text-slate-600">
                          <span>Tax Total:</span>
                          <span className="font-mono">{fmt(bill.tax_total, bill.currency)}</span>
                        </div>
                        <div className="flex justify-between font-bold text-slate-900 border-t border-slate-200 pt-1.5 text-sm">
                          <span>Total:</span>
                          <span className="font-mono">{fmt(bill.total, bill.currency)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── TAB 3: DOCUMENTS ────────────────────────────── */}
                {activeTab === "documents" && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-700">Attached Documents</h4>
                      <button
                        onClick={() => setUploadModalOpen(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#0073B7] hover:bg-[#005f96] text-xs font-semibold text-white transition-all shadow-xs"
                      >
                        <Upload className="h-3.5 w-3.5" />
                        Attach Document
                      </button>
                    </div>

                    {bill.documents && bill.documents.length > 0 ? (
                      <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
                        {bill.documents.map((doc) => (
                          <div
                            key={doc.id}
                            className="p-3.5 flex items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
                          >
                            <div className="flex items-start gap-3 min-w-0">
                              <FileText className="h-5 w-5 text-slate-400 flex-shrink-0 mt-0.5" />
                              <div className="min-w-0 space-y-0.5">
                                <p className="text-xs font-semibold text-slate-900 truncate">
                                  {doc.filename || "Document"}
                                </p>
                                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                                  <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-medium">
                                    {doc.document_type}
                                  </span>
                                  <span>{fmtBytes(doc.size_bytes)}</span>
                                  <span>•</span>
                                  <span>Attached {fmtDate(doc.created_at)}</span>
                                </div>
                                {doc.checksum_sha256 && (
                                  <p className="text-[10px] font-mono text-slate-400 truncate max-w-sm">
                                    SHA-256: {doc.checksum_sha256}
                                  </p>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 flex-shrink-0">
                              <button
                                onClick={() => {
                                  setActivePreviewDoc(doc);
                                  fetchDocumentUrl(doc);
                                }}
                                className="px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200/60 rounded transition-colors"
                              >
                                Preview
                              </button>
                              {isDraft && (
                                <button
                                  onClick={() => handleDeleteDocument(doc.id)}
                                  className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                                  title="Delete document"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-xs text-slate-500">
                        No documents attached to this bill.
                      </div>
                    )}
                  </div>
                )}

                {/* ── TAB 4: APPROVAL HISTORY ──────────────────────── */}
                {activeTab === "approval" && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-700">Approval Workflow Events</h4>
                    {bill.approval_events && bill.approval_events.length > 0 ? (
                      <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                        {bill.approval_events.map((ev, idx) => {
                          const actionColors = {
                            SUBMITTED: "bg-sky-500",
                            APPROVED: "bg-emerald-500",
                            REJECTED: "bg-red-500",
                            RESUBMITTED: "bg-purple-500",
                          }[ev.action] || "bg-slate-400";

                          return (
                            <div key={ev.id || idx} className="flex items-start gap-4 relative pl-7">
                              <div
                                className={`absolute left-1.5 top-1.5 h-3.5 w-3.5 rounded-full ${actionColors} ring-4 ring-white`}
                              />
                              <div className="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1 text-xs">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-900">{ev.action}</span>
                                  <span className="text-[11px] text-slate-400">{fmtDateTime(ev.created_at)}</span>
                                </div>
                                <p className="text-slate-600">
                                  By: <span className="font-medium text-slate-800">{ev.actor_name || "User"}</span>
                                </p>
                                {ev.comment && (
                                  <p className="text-slate-700 bg-white p-2 rounded border border-slate-200 text-[11px] mt-1 italic">
                                    &ldquo;{ev.comment}&rdquo;
                                  </p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-xs text-slate-500">
                        No approval actions recorded yet.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── SUBMIT MODAL ─────────────────────────────────────── */}
      {submitModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Submit Bill for Approval</h3>
              <button onClick={() => setSubmitModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Submitting will move this bill to the approval queue for review by an authorized manager.
            </p>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-700">Comment / Note (Optional)</label>
              <textarea
                value={submitComment}
                onChange={(e) => setSubmitComment(e.target.value)}
                placeholder="e.g. Monthly cloud hosting invoice verified against budget."
                rows={3}
                className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSubmitModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={actionInProgress}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0073B7] hover:bg-[#005f96] rounded-md transition-all"
              >
                {actionInProgress ? "Submitting..." : "Confirm & Submit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── APPROVE MODAL ────────────────────────────────────── */}
      {approveModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Approve Supplier Bill</h3>
              <button onClick={() => setApproveModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Approving will lock the financial totals and move this bill to{" "}
              <strong className="text-slate-800">Awaiting Payment</strong>.
            </p>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-700">Approval Comment (Optional)</label>
              <textarea
                value={approveComment}
                onChange={(e) => setApproveComment(e.target.value)}
                placeholder="e.g. Verified against supplier contract and PO."
                rows={3}
                className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setApproveModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={actionInProgress}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition-all"
              >
                {actionInProgress ? "Approving..." : "Confirm Approval"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── REJECT MODAL ─────────────────────────────────────── */}
      {rejectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Reject Supplier Bill</h3>
              <button onClick={() => setRejectModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Please provide a clear reason for the rejection so the submitter can make corrections.
            </p>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Invoice line price does not match the agreed contract rate."
                rows={3}
                className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setRejectModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={actionInProgress}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md transition-all"
              >
                {actionInProgress ? "Rejecting..." : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── VOID MODAL ───────────────────────────────────────── */}
      {voidModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Void Bill</h3>
              <button onClick={() => setVoidModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Voiding an approved bill is permanent and cannot be undone. An audit record will be created.
            </p>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-800">
                Void Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
                placeholder="e.g. Supplier issued credit note and cancelled original invoice."
                rows={3}
                className="w-full text-xs rounded-md border border-slate-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-slate-700"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setVoidModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleVoid}
                disabled={actionInProgress}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-md transition-all"
              >
                {actionInProgress ? "Voiding..." : "Confirm Void"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DELETE DRAFT MODAL ───────────────────────────────── */}
      {deleteModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-sm w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Delete Draft Bill</h3>
              <button onClick={() => setDeleteModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Are you sure you want to permanently delete this draft bill? This action cannot be reversed.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeleteModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteDraft}
                disabled={actionInProgress}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-md transition-all"
              >
                {actionInProgress ? "Deleting..." : "Delete Bill"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── ATTACH DOCUMENT MODAL ────────────────────────────── */}
      {uploadModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <form
            onSubmit={handleUploadDocument}
            className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Attach Document</h3>
              <button
                type="button"
                onClick={() => setUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Document Type</label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="w-full text-xs rounded-md border border-slate-300 p-2 focus:outline-none focus:ring-1 focus:ring-[#0073B7]"
                >
                  <option value="ORIGINAL_INVOICE">Original Supplier Invoice</option>
                  <option value="SUPPORTING_DOCUMENT">Supporting Document</option>
                  <option value="PURCHASE_ORDER">Purchase Order</option>
                  <option value="RECEIPT">Receipt</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-slate-700">Select File (PDF, JPG, PNG, HEIC)</label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  required
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs border border-slate-300 rounded-md p-1.5 file:mr-3 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setUploadModalOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading || !uploadFile}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0073B7] hover:bg-[#005f96] rounded-md transition-all disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Upload & Attach"}
              </button>
            </div>
          </form>
        </div>
      )}
    </DashboardLayout>
  );
}
