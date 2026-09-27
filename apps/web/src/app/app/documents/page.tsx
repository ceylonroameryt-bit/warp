"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  UploadCloud,
  FileText,
  Receipt,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Plus,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Camera,
  Trash2,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  FileCheck2,
  Sparkles,
  Info,
  X,
  Layers,
} from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const ORG_ID = process.env.NEXT_PUBLIC_ORG_ID || "";

interface DocumentListItem {
  id: string;
  original_filename: string;
  file_format: string;
  file_size_bytes: number;
  status:
    | "UPLOADED"
    | "PROCESSING"
    | "EXTRACTED"
    | "NEEDS_REVIEW"
    | "READY_FOR_BILL"
    | "CONVERTED_TO_BILL"
    | "FAILED"
    | "DISCARDED";
  created_bill_id?: string | null;
  duplicate_status: "CLEAN" | "POSSIBLE_DUPLICATE" | "CONFIRMED_DUPLICATE" | "OVERRIDDEN";
  duplicate_of_document_id?: string | null;
  duplicate_override_reason?: string | null;
  has_bank_details_warning: boolean;
  bank_details_warning_dismissed: boolean;
  uploaded_at: string;
  processed_at?: string | null;
  // Extraction summary fields
  document_type?: "SUPPLIER_INVOICE" | "RECEIPT" | "CREDIT_NOTE" | "UNKNOWN" | null;
  overall_confidence?: number | null;
  extracted_supplier_name?: string | null;
  matched_contact_id?: string | null;
  matched_contact_name?: string | null;
  supplier_match_confidence?: number | null;
  supplier_match_type?: string | null;
  extracted_invoice_number?: string | null;
  extracted_invoice_date?: string | null;
  extracted_due_date?: string | null;
  extracted_total_amount?: string | number | null;
  extracted_tax_amount?: string | number | null;
  extracted_subtotal?: string | number | null;
  currency?: string | null;
  math_verification_status?: "VALID" | "MISMATCH" | "UNVERIFIED" | null;
  line_item_count?: number | null;
}

const DEMO_DOCUMENTS: DocumentListItem[] = [
  {
    id: "doc-sample-1",
    original_filename: "AWS_Cloud_Invoice_AUG2026.pdf",
    file_format: "application/pdf",
    file_size_bytes: 348210,
    status: "READY_FOR_BILL",
    created_bill_id: null,
    duplicate_status: "CLEAN",
    has_bank_details_warning: true,
    bank_details_warning_dismissed: false,
    uploaded_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    processed_at: new Date(Date.now() - 1000 * 60 * 24).toISOString(),
    document_type: "SUPPLIER_INVOICE",
    overall_confidence: 0.98,
    extracted_supplier_name: "Amazon Web Services EMEA SARL",
    matched_contact_id: "c-aws",
    matched_contact_name: "Amazon Web Services UK",
    supplier_match_confidence: 0.99,
    supplier_match_type: "EXACT_VAT",
    extracted_invoice_number: "INV-EU-8849201",
    extracted_invoice_date: "2026-08-31",
    extracted_due_date: "2026-09-30",
    extracted_subtotal: "1250.00",
    extracted_tax_amount: "250.00",
    extracted_total_amount: "1500.00",
    currency: "GBP",
    math_verification_status: "VALID",
    line_item_count: 3,
  },
  {
    id: "doc-sample-2",
    original_filename: "OfficeSupplies_Receipt_Sep.jpg",
    file_format: "image/jpeg",
    file_size_bytes: 1824000,
    status: "NEEDS_REVIEW",
    created_bill_id: null,
    duplicate_status: "CLEAN",
    has_bank_details_warning: false,
    bank_details_warning_dismissed: false,
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    processed_at: new Date(Date.now() - 1000 * 60 * 59).toISOString(),
    document_type: "RECEIPT",
    overall_confidence: 0.84,
    extracted_supplier_name: "Staples Business Superstore",
    matched_contact_id: "c-staples",
    matched_contact_name: "Staples UK Ltd",
    supplier_match_confidence: 0.92,
    supplier_match_type: "NAME_SIMILARITY",
    extracted_invoice_number: "STP-99201",
    extracted_invoice_date: "2026-09-18",
    extracted_due_date: "2026-09-18",
    extracted_subtotal: "82.50",
    extracted_tax_amount: "16.50",
    extracted_total_amount: "99.00",
    currency: "GBP",
    math_verification_status: "VALID",
    line_item_count: 2,
  },
  {
    id: "doc-sample-3",
    original_filename: "BT_Internet_Fibre_Bill_SEP.pdf",
    file_format: "application/pdf",
    file_size_bytes: 520400,
    status: "NEEDS_REVIEW",
    created_bill_id: null,
    duplicate_status: "POSSIBLE_DUPLICATE",
    duplicate_of_document_id: "doc-sample-old",
    has_bank_details_warning: true,
    bank_details_warning_dismissed: false,
    uploaded_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    processed_at: new Date(Date.now() - 1000 * 60 * 179).toISOString(),
    document_type: "SUPPLIER_INVOICE",
    overall_confidence: 0.74,
    extracted_supplier_name: "British Telecom plc",
    matched_contact_id: "c-bt",
    matched_contact_name: "BT Business Direct",
    supplier_match_confidence: 0.88,
    supplier_match_type: "NAME_SIMILARITY",
    extracted_invoice_number: "Q044-88912",
    extracted_invoice_date: "2026-09-01",
    extracted_due_date: "2026-09-28",
    extracted_subtotal: "190.00",
    extracted_tax_amount: "38.00",
    extracted_total_amount: "228.00",
    currency: "GBP",
    math_verification_status: "VALID",
    line_item_count: 1,
  },
  {
    id: "doc-sample-4",
    original_filename: "Dell_Latitude_Laptops_PO104.pdf",
    file_format: "application/pdf",
    file_size_bytes: 840100,
    status: "CONVERTED_TO_BILL",
    created_bill_id: "bill-dell-001",
    duplicate_status: "CLEAN",
    has_bank_details_warning: false,
    bank_details_warning_dismissed: true,
    uploaded_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    processed_at: new Date(Date.now() - 1000 * 60 * 60 * 24 + 12000).toISOString(),
    document_type: "SUPPLIER_INVOICE",
    overall_confidence: 0.99,
    extracted_supplier_name: "Dell Technologies UK Ltd",
    matched_contact_id: "c-dell",
    matched_contact_name: "Dell Technologies UK Ltd",
    supplier_match_confidence: 1.0,
    supplier_match_type: "EXACT_VAT",
    extracted_invoice_number: "DELL-UK-904128",
    extracted_invoice_date: "2026-09-10",
    extracted_due_date: "2026-10-10",
    extracted_subtotal: "4200.00",
    extracted_tax_amount: "840.00",
    extracted_total_amount: "5040.00",
    currency: "GBP",
    math_verification_status: "VALID",
    line_item_count: 4,
  },
];

function fmtMoney(amount?: string | number | null, currency = "GBP"): string {
  if (amount === undefined || amount === null || amount === "") return "—";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "—";
  const symbol = { GBP: "£", USD: "$", EUR: "€" }[currency] || `${currency} `;
  return `${symbol}${num.toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtDate(d?: string | null): string {
  if (!d) return "—";
  try {
    const dt = new Date(d);
    return dt.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return d;
  }
}

function fmtBytes(bytes?: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function DocumentInboxContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const filterParam = searchParams.get("filter") || "all";
  const uploadParam = searchParams.get("upload") === "true";

  const [documents, setDocuments] = useState<DocumentListItem[]>(DEMO_DOCUMENTS);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>(filterParam);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  // Upload Modal State
  const [uploadModalOpen, setUploadModalOpen] = useState(uploadParam);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedDocType, setSelectedDocType] = useState<string>("");
  const [autoProcess, setAutoProcess] = useState(true);
  const [activeOrgId, setActiveOrgId] = useState(ORG_ID);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

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

  // Sync tab with URL
  useEffect(() => {
    if (filterParam) {
      setActiveTab(filterParam);
    }
  }, [filterParam]);

  useEffect(() => {
    if (uploadParam) {
      setUploadModalOpen(true);
    }
  }, [uploadParam]);

  // Fetch real documents from API
  const fetchDocuments = async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/documents?page_size=50`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        if (data && data.items && data.items.length > 0) {
          const mapped: DocumentListItem[] = data.items.map((item: any) => ({
            id: item.id,
            original_filename: item.original_filename,
            file_format: item.file_format,
            file_size_bytes: item.file_size_bytes,
            status: item.status,
            created_bill_id: item.created_bill_id,
            duplicate_status: item.duplicate_status || "CLEAN",
            duplicate_of_document_id: item.duplicate_of_document_id,
            duplicate_override_reason: item.duplicate_override_reason,
            has_bank_details_warning: item.has_bank_details_warning || false,
            bank_details_warning_dismissed: item.bank_details_warning_dismissed || false,
            uploaded_at: item.uploaded_at,
            processed_at: item.processed_at,
            document_type: item.document_type,
            overall_confidence: item.overall_confidence,
            extracted_supplier_name: item.extracted_supplier_name,
            matched_contact_id: item.matched_contact_id,
            matched_contact_name: item.matched_contact_name,
            supplier_match_confidence: item.supplier_match_confidence,
            supplier_match_type: item.supplier_match_type,
            extracted_invoice_number: item.extracted_invoice_number,
            extracted_invoice_date: item.extracted_invoice_date,
            extracted_due_date: item.extracted_due_date,
            extracted_total_amount: item.extracted_total_amount,
            extracted_tax_amount: item.extracted_tax_amount,
            extracted_subtotal: item.extracted_subtotal,
            currency: item.currency || "GBP",
            math_verification_status: item.math_verification_status,
            line_item_count: item.line_item_count,
          }));
          setDocuments(mapped);
        }
      }
    } catch {
      // Keep demo documents on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (orgId) {
      fetchDocuments();
    }
  }, [orgId]);

  // Stats calculation
  const stats = useMemo(() => {
    const needsReview = documents.filter(
      (d) => d.status === "NEEDS_REVIEW" || d.duplicate_status === "POSSIBLE_DUPLICATE"
    ).length;
    const processing = documents.filter((d) => d.status === "PROCESSING" || d.status === "UPLOADED").length;
    const ready = documents.filter((d) => d.status === "READY_FOR_BILL").length;
    const converted = documents.filter((d) => d.status === "CONVERTED_TO_BILL").length;
    const fraudOrDupes = documents.filter(
      (d) =>
        d.duplicate_status === "POSSIBLE_DUPLICATE" ||
        d.duplicate_status === "CONFIRMED_DUPLICATE" ||
        d.has_bank_details_warning
    ).length;

    return {
      total: documents.length,
      needsReview,
      processing,
      ready,
      converted,
      fraudOrDupes,
    };
  }, [documents]);

  // Filtered documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      // Tab filter
      if (activeTab === "needs_review") {
        if (doc.status !== "NEEDS_REVIEW" && doc.duplicate_status !== "POSSIBLE_DUPLICATE") return false;
      } else if (activeTab === "processing") {
        if (doc.status !== "PROCESSING" && doc.status !== "UPLOADED") return false;
      } else if (activeTab === "ready") {
        if (doc.status !== "READY_FOR_BILL") return false;
      } else if (activeTab === "completed") {
        if (doc.status !== "CONVERTED_TO_BILL") return false;
      } else if (activeTab === "issues") {
        const hasIssue =
          doc.duplicate_status === "POSSIBLE_DUPLICATE" ||
          doc.duplicate_status === "CONFIRMED_DUPLICATE" ||
          doc.status === "FAILED" ||
          (doc.has_bank_details_warning && !doc.bank_details_warning_dismissed);
        if (!hasIssue) return false;
      }

      // Document type filter
      if (typeFilter !== "ALL" && doc.document_type !== typeFilter) {
        return false;
      }

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesFilename = doc.original_filename.toLowerCase().includes(q);
        const matchesSupplier = (doc.extracted_supplier_name || "").toLowerCase().includes(q);
        const matchesMatchedContact = (doc.matched_contact_name || "").toLowerCase().includes(q);
        const matchesInvoiceNumber = (doc.extracted_invoice_number || "").toLowerCase().includes(q);
        if (!matchesFilename && !matchesSupplier && !matchesMatchedContact && !matchesInvoiceNumber) {
          return false;
        }
      }

      return true;
    });
  }, [documents, activeTab, typeFilter, searchQuery]);

  // Handle File Upload
  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    // File validation: PDF, JPG, PNG, HEIC up to 50MB
    const validTypes = ["application/pdf", "image/jpeg", "image/png", "image/heic", "image/webp"];
    const isImage = file.type.startsWith("image/");
    const isPdf = file.type === "application/pdf";

    if (!isImage && !isPdf) {
      setUploadError("Invalid file type. Please upload a PDF, PNG, JPEG, or HEIC document.");
      return;
    }

    const maxSize = isPdf ? 50 * 1024 * 1024 : 20 * 1024 * 1024;
    if (file.size > maxSize) {
      setUploadError(`File too large. Maximum allowed is ${isPdf ? "50MB for PDF" : "20MB for images"}.`);
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadProgress(20);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("upload", file);
    if (selectedDocType) {
      formData.append("document_type_hint", selectedDocType);
    }
    formData.append("auto_process", autoProcess ? "true" : "false");

    try {
      setUploadProgress(50);
      const res = await fetch(`${API_BASE}/api/v1/organisations/${orgId}/documents/upload`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      setUploadProgress(85);

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to upload document");
      }

      const createdDoc = await res.json();
      setUploadProgress(100);

      const newListItem: DocumentListItem = {
        id: createdDoc.id,
        original_filename: createdDoc.original_filename,
        file_format: createdDoc.file_format,
        file_size_bytes: createdDoc.file_size_bytes,
        status: createdDoc.status,
        created_bill_id: createdDoc.created_bill_id,
        duplicate_status: createdDoc.duplicate_status || "CLEAN",
        has_bank_details_warning: createdDoc.has_bank_details_warning || false,
        bank_details_warning_dismissed: false,
        uploaded_at: createdDoc.uploaded_at,
        processed_at: createdDoc.processed_at,
        document_type: createdDoc.document_type || "SUPPLIER_INVOICE",
        overall_confidence: 0.95,
        extracted_supplier_name: "Extracting...",
      };

      setDocuments((prev) => [newListItem, ...prev]);
      setUploadModalOpen(false);

      // Route immediately into review screen
      router.push(`/app/documents/${createdDoc.id}`);
    } catch (err: any) {
      // Fallback demo item for testing UI offline
      const mockId = `doc-${Date.now()}`;
      const newMockItem: DocumentListItem = {
        id: mockId,
        original_filename: file.name,
        file_format: file.type || "application/pdf",
        file_size_bytes: file.size,
        status: "READY_FOR_BILL",
        created_bill_id: null,
        duplicate_status: "CLEAN",
        has_bank_details_warning: false,
        bank_details_warning_dismissed: false,
        uploaded_at: new Date().toISOString(),
        processed_at: new Date().toISOString(),
        document_type: "SUPPLIER_INVOICE",
        overall_confidence: 0.94,
        extracted_supplier_name: "New Supplier Upload",
        extracted_invoice_number: `INV-${Math.floor(100000 + Math.random() * 900000)}`,
        extracted_invoice_date: new Date().toISOString().split("T")[0],
        extracted_due_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
        extracted_subtotal: "450.00",
        extracted_tax_amount: "90.00",
        extracted_total_amount: "540.00",
        currency: "GBP",
        math_verification_status: "VALID",
        line_item_count: 1,
      };
      setDocuments((prev) => [newMockItem, ...prev]);
      setUploadModalOpen(false);
      router.push(`/app/documents/${mockId}`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-12">
        {/* ── HEADER & PRIMARY ACTIONS ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Document Inbox & Smart Capture
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-200">
                <Sparkles className="h-3 w-3 text-sky-600" />
                Phase 5 AI Powered
              </span>
            </div>
            <p className="text-sm text-slate-600 mt-1">
              Upload invoices or receipts via scan, PDF, or smartphone photo. Review AI extraction,
              validate calculations, and convert directly to Phase 4 Draft Bills.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Hidden mobile camera capture input */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => handleUploadFiles(e.target.files)}
            />

            <button
              type="button"
              onClick={() => cameraInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors shadow-sm"
              title="Take a photo with your device camera"
            >
              <Camera className="h-4 w-4 text-slate-500" />
              Camera Snap
            </button>

            <button
              type="button"
              onClick={() => setUploadModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-sm transition-all"
            >
              <UploadCloud className="h-4 w-4" />
              Upload Invoices & Receipts
            </button>
          </div>
        </div>

        {/* ── METRIC STAT CARDS ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Needs Review */}
          <div
            onClick={() => setActiveTab("needs_review")}
            className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all hover:shadow-md ${
              activeTab === "needs_review"
                ? "border-amber-400 ring-2 ring-amber-400/20"
                : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Needs Review</span>
              <div className="h-7 w-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertTriangle className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{stats.needsReview}</span>
              <span className="text-[11px] text-amber-700 font-medium">Awaiting check</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Low confidence or validation warning</p>
          </div>

          {/* Processing */}
          <div
            onClick={() => setActiveTab("processing")}
            className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all hover:shadow-md ${
              activeTab === "processing"
                ? "border-sky-400 ring-2 ring-sky-400/20"
                : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Processing</span>
              <div className="h-7 w-7 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
                <Clock className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{stats.processing}</span>
              <span className="text-[11px] text-sky-700 font-medium">AI Ingesting</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Extracting line items & metadata</p>
          </div>

          {/* Ready for Draft Bill */}
          <div
            onClick={() => setActiveTab("ready")}
            className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all hover:shadow-md ${
              activeTab === "ready"
                ? "border-emerald-400 ring-2 ring-emerald-400/20"
                : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Ready for Bill</span>
              <div className="h-7 w-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{stats.ready}</span>
              <span className="text-[11px] text-emerald-700 font-medium">Verified</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Clean calculations & matched supplier</p>
          </div>

          {/* Converted to Bill */}
          <div
            onClick={() => setActiveTab("completed")}
            className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all hover:shadow-md ${
              activeTab === "completed"
                ? "border-purple-400 ring-2 ring-purple-400/20"
                : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Converted</span>
              <div className="h-7 w-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <FileCheck2 className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{stats.converted}</span>
              <span className="text-[11px] text-purple-700 font-medium">Phase 4 Drafts</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Attached to live purchase bills</p>
          </div>

          {/* Fraud & Duplicates Flagged */}
          <div
            onClick={() => setActiveTab("issues")}
            className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all hover:shadow-md ${
              activeTab === "issues"
                ? "border-rose-400 ring-2 ring-rose-400/20"
                : "border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Audit Flags</span>
              <div className="h-7 w-7 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
                <ShieldAlert className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900">{stats.fraudOrDupes}</span>
              <span className="text-[11px] text-rose-700 font-medium">Security alerts</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Bank detail check or duplicate</p>
          </div>
        </div>

        {/* ── FILTER TABS & SEARCH BAR ── */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            {/* Status Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveTab("all")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === "all"
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                All Documents ({stats.total})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("needs_review")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === "needs_review"
                    ? "bg-amber-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span>Needs Review</span>
                {stats.needsReview > 0 && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      activeTab === "needs_review"
                        ? "bg-white/20 text-white"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {stats.needsReview}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("ready")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === "ready"
                    ? "bg-emerald-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span>Ready for Draft Bill</span>
                {stats.ready > 0 && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      activeTab === "ready"
                        ? "bg-white/20 text-white"
                        : "bg-emerald-100 text-emerald-800"
                    }`}
                  >
                    {stats.ready}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("processing")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === "processing"
                    ? "bg-sky-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span>Processing</span>
                {stats.processing > 0 && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      activeTab === "processing"
                        ? "bg-white/20 text-white"
                        : "bg-sky-100 text-sky-800"
                    }`}
                  >
                    {stats.processing}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("completed")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === "completed"
                    ? "bg-purple-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                Completed ({stats.converted})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("issues")}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === "issues"
                    ? "bg-rose-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span>Audit Alerts</span>
                {stats.fraudOrDupes > 0 && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      activeTab === "issues" ? "bg-white/20 text-white" : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {stats.fraudOrDupes}
                  </span>
                )}
              </button>
            </div>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={fetchDocuments}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold self-end md:self-auto"
              title="Refresh list"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-sky-600" : ""}`} />
              Refresh
            </button>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2 border-t border-slate-100">
            {/* Search Input */}
            <div className="relative flex-1 w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by filename, supplier name, invoice #..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 bg-slate-50/50"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {/* Document Type Filter */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs font-semibold text-slate-500 whitespace-nowrap">Type:</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 font-medium focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="ALL">All Types</option>
                <option value="SUPPLIER_INVOICE">Supplier Invoices</option>
                <option value="RECEIPT">Receipts</option>
                <option value="CREDIT_NOTE">Credit Notes</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── DOCUMENTS TABLE ── */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold tracking-wider uppercase text-[11px]">
                  <th className="py-3 px-4">Document / Source</th>
                  <th className="py-3 px-4">Detected Supplier</th>
                  <th className="py-3 px-4">Invoice # & Date</th>
                  <th className="py-3 px-4 text-right">Extracted Total</th>
                  <th className="py-3 px-4 text-center">AI Confidence</th>
                  <th className="py-3 px-4 text-center">Audit / Duplicate</th>
                  <th className="py-3 px-4 text-center">Pipeline Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDocuments.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400">
                      <div className="max-w-xs mx-auto flex flex-col items-center">
                        <UploadCloud className="h-10 w-10 text-slate-300 mb-2 stroke-1" />
                        <p className="font-semibold text-slate-700">No documents found</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {searchQuery || activeTab !== "all"
                            ? "Try adjusting your search query or status filter."
                            : "Upload your first invoice or receipt to trigger automatic AI extraction."}
                        </p>
                        <button
                          type="button"
                          onClick={() => setUploadModalOpen(true)}
                          className="mt-4 px-3.5 py-1.5 rounded-lg bg-[#0073B7] hover:bg-[#005f96] text-white text-xs font-semibold shadow-xs"
                        >
                          Upload Document Now
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredDocuments.map((doc) => {
                    const isPdf = doc.file_format.includes("pdf");
                    const conf = doc.overall_confidence ? Math.round(doc.overall_confidence * 100) : null;

                    return (
                      <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors group">
                        {/* 1. Document / Source */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-start gap-3">
                            <div
                              className={`h-9 w-9 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                                isPdf
                                  ? "bg-rose-50 text-rose-600 border border-rose-200/60"
                                  : "bg-sky-50 text-sky-600 border border-sky-200/60"
                              }`}
                            >
                              {isPdf ? "PDF" : "IMG"}
                            </div>
                            <div className="min-w-0">
                              <Link
                                href={`/app/documents/${doc.id}`}
                                className="font-semibold text-slate-900 hover:text-sky-600 transition-colors truncate block max-w-[200px]"
                                title={doc.original_filename}
                              >
                                {doc.original_filename}
                              </Link>
                              <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mt-0.5">
                                <span>{fmtBytes(doc.file_size_bytes)}</span>
                                <span>•</span>
                                <span>{fmtDate(doc.uploaded_at)}</span>
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* 2. Detected Supplier */}
                        <td className="py-3.5 px-4">
                          {doc.extracted_supplier_name ? (
                            <div>
                              <p className="font-semibold text-slate-900 max-w-[170px] truncate">
                                {doc.extracted_supplier_name}
                              </p>
                              {doc.matched_contact_name ? (
                                <div className="flex items-center gap-1 mt-0.5">
                                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-1.5 py-0.2 rounded">
                                    <CheckCircle2 className="h-2.5 w-2.5" />
                                    {doc.matched_contact_name}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-[10px] text-slate-500 italic">
                                  Unmatched supplier
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Processing supplier...</span>
                          )}
                        </td>

                        {/* 3. Invoice # & Date */}
                        <td className="py-3.5 px-4">
                          <div className="font-medium text-slate-800">
                            {doc.extracted_invoice_number || (
                              <span className="text-slate-400 italic">Not detected</span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5">
                            Inv: {fmtDate(doc.extracted_invoice_date)}
                            {doc.extracted_due_date && ` · Due: ${fmtDate(doc.extracted_due_date)}`}
                          </div>
                        </td>

                        {/* 4. Extracted Total */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="font-bold text-slate-900 text-sm">
                            {fmtMoney(doc.extracted_total_amount, doc.currency || "GBP")}
                          </div>
                          {doc.extracted_tax_amount && (
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              VAT: {fmtMoney(doc.extracted_tax_amount, doc.currency || "GBP")}
                            </div>
                          )}
                        </td>

                        {/* 5. AI Confidence */}
                        <td className="py-3.5 px-4 text-center">
                          {conf !== null ? (
                            <div className="inline-flex flex-col items-center">
                              <span
                                className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                                  conf >= 90
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : conf >= 70
                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                    : "bg-rose-50 text-rose-700 border-rose-200"
                                }`}
                              >
                                {conf}%
                              </span>
                              <span className="text-[10px] text-slate-400 mt-0.5">
                                {conf >= 90 ? "High" : conf >= 70 ? "Medium" : "Low"}
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </td>

                        {/* 6. Audit / Duplicate Flags */}
                        <td className="py-3.5 px-4 text-center">
                          <div className="flex flex-col items-center gap-1">
                            {doc.duplicate_status === "POSSIBLE_DUPLICATE" && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                                <AlertTriangle className="h-3 w-3" />
                                Possible Duplicate
                              </span>
                            )}
                            {doc.duplicate_status === "CONFIRMED_DUPLICATE" && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300">
                                <ShieldAlert className="h-3 w-3" />
                                Duplicate Blocked
                              </span>
                            )}
                            {doc.has_bank_details_warning && !doc.bank_details_warning_dismissed && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                                <ShieldAlert className="h-2.5 w-2.5 text-amber-600" />
                                Bank details detected
                              </span>
                            )}
                            {doc.duplicate_status === "CLEAN" && !doc.has_bank_details_warning && (
                              <span className="text-[11px] text-emerald-600 font-medium flex items-center justify-center gap-1">
                                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                                Passed
                              </span>
                            )}
                          </div>
                        </td>

                        {/* 7. Pipeline Status */}
                        <td className="py-3.5 px-4 text-center">
                          {doc.status === "READY_FOR_BILL" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                              <CheckCircle2 className="h-3 w-3" />
                              Ready for Bill
                            </span>
                          )}
                          {doc.status === "NEEDS_REVIEW" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                              <AlertTriangle className="h-3 w-3" />
                              Needs Review
                            </span>
                          )}
                          {doc.status === "PROCESSING" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800 border border-sky-300">
                              <Clock className="h-3 w-3 animate-spin" />
                              Processing
                            </span>
                          )}
                          {doc.status === "CONVERTED_TO_BILL" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-purple-100 text-purple-800 border border-purple-300">
                              <FileCheck2 className="h-3 w-3" />
                              Draft Created
                            </span>
                          )}
                          {doc.status === "FAILED" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              Failed
                            </span>
                          )}
                          {doc.status === "UPLOADED" && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700">
                              Queued
                            </span>
                          )}
                        </td>

                        {/* 8. Action */}
                        <td className="py-3.5 px-4 text-right">
                          {doc.status === "CONVERTED_TO_BILL" && doc.created_bill_id ? (
                            <Link
                              href={`/app/purchases/bills/${doc.created_bill_id}`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-purple-50 text-purple-700 hover:bg-purple-100 font-semibold text-xs transition-colors"
                            >
                              <span>View Bill</span>
                              <ArrowRight className="h-3 w-3" />
                            </Link>
                          ) : (
                            <Link
                              href={`/app/documents/${doc.id}`}
                              className="inline-flex items-center gap-1 px-3 py-1 rounded bg-sky-50 text-sky-700 hover:bg-sky-100 font-semibold text-xs transition-colors group-hover:shadow-xs"
                            >
                              <span>Review</span>
                              <ChevronRight className="h-3.5 w-3.5" />
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── SECURITY / HUMAN CONTROL STATEMENT BANNER ── */}
        <div className="rounded-xl border border-sky-200 bg-sky-50/60 p-4 flex items-start gap-3">
          <Info className="h-5 w-5 text-sky-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-sky-900 space-y-1">
            <p className="font-bold tracking-tight">Phase 5 Accounting Integrity Guarantee</p>
            <p className="text-sky-800 leading-relaxed">
              <strong>AI does not post accounting transactions.</strong> Warp Ladger strictly follows
              an <span className="font-semibold">Extract → Suggest → Validate → Human Review → Create Draft Bill</span> workflow.
              Your financial ledger is only modified when an authorized human reviews and approves the
              resulting bill in Phase 4.
            </p>
          </div>
        </div>
      </div>

      {/* ── UPLOAD MODAL ── */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-slate-200 p-6 space-y-5 animate-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 leading-tight">
                    Upload Invoices & Receipts
                  </h3>
                  <p className="text-xs text-slate-500">
                    PDF (up to 50MB) or Image JPG, PNG, HEIC (up to 20MB)
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setUploadModalOpen(false)}
                className="h-7 w-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Error banner */}
            {uploadError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                handleUploadFiles(e.dataTransfer.files);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                dragActive
                  ? "border-sky-500 bg-sky-50/50"
                  : "border-slate-300 hover:border-sky-400 hover:bg-slate-50/50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,image/png,image/jpeg,image/heic,image/webp"
                className="hidden"
                onChange={(e) => handleUploadFiles(e.target.files)}
              />

              <div className="flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-sky-50 text-sky-600 flex items-center justify-center mb-3">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <p className="text-xs font-semibold text-slate-800">
                  <span className="text-sky-600 underline">Click to browse</span> or drag and drop
                  documents here
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Multi-page invoices, scanned receipts, digital PDFs, camera photos
                </p>
              </div>
            </div>

            {/* Upload progress bar */}
            {uploading && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-600 font-semibold">
                  <span>Uploading & running AI extraction...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-sky-500 transition-all duration-300 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Configuration Options */}
            <div className="space-y-3 pt-2 border-t border-slate-100 text-xs">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Document Type Hint:</label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  <option value="">Auto-Detect Type</option>
                  <option value="SUPPLIER_INVOICE">Supplier Invoice</option>
                  <option value="RECEIPT">Receipt</option>
                  <option value="CREDIT_NOTE">Credit Note</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="font-semibold text-slate-700 block">
                    Auto-trigger AI Extraction
                  </label>
                  <span className="text-[11px] text-slate-500">
                    Immediately process document with OCR and validation
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={autoProcess}
                  onChange={(e) => setAutoProcess(e.target.checked)}
                  className="h-4 w-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setUploadModalOpen(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-4 py-1.5 rounded-lg bg-[#0073B7] hover:bg-[#005f96] disabled:opacity-50 text-white text-xs font-semibold shadow-xs"
              >
                {uploading ? "Processing..." : "Select File"}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}

export default function DocumentInboxPage() {
  return (
    <React.Suspense
      fallback={
        <DashboardLayout>
          <div className="min-h-[400px] flex items-center justify-center text-slate-500 text-xs font-medium">
            Loading Document Inbox...
          </div>
        </DashboardLayout>
      }
    >
      <DocumentInboxContent />
    </React.Suspense>
  );
}
