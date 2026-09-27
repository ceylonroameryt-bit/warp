"use client";

import React from "react";
import {
  Clock,
  CheckCircle,
  Send,
  AlertTriangle,
  Ban,
  CreditCard,
  DollarSign,
  RefreshCw,
} from "lucide-react";

type InvoiceStatus =
  | "DRAFT"
  | "APPROVED"
  | "SENT"
  | "AWAITING_PAYMENT"
  | "PARTIALLY_PAID"
  | "PAID"
  | "OVERDUE"
  | "VOID"
  | "CREDITED";

interface Props {
  status: InvoiceStatus | string;
  size?: "sm" | "md";
}

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; border: string; Icon: React.ElementType }
> = {
  DRAFT: {
    label: "Draft",
    bg: "bg-slate-100",
    text: "text-slate-600",
    border: "border-slate-200",
    Icon: Clock,
  },
  APPROVED: {
    label: "Approved",
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    Icon: CheckCircle,
  },
  SENT: {
    label: "Sent",
    bg: "bg-sky-50",
    text: "text-sky-700",
    border: "border-sky-200",
    Icon: Send,
  },
  AWAITING_PAYMENT: {
    label: "Awaiting Payment",
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    border: "border-indigo-200",
    Icon: DollarSign,
  },
  PARTIALLY_PAID: {
    label: "Partially Paid",
    bg: "bg-purple-50",
    text: "text-purple-700",
    border: "border-purple-200",
    Icon: RefreshCw,
  },
  PAID: {
    label: "Paid",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    Icon: CheckCircle,
  },
  OVERDUE: {
    label: "Overdue",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-300",
    Icon: AlertTriangle,
  },
  VOID: {
    label: "Void",
    bg: "bg-red-50",
    text: "text-red-600",
    border: "border-red-200",
    Icon: Ban,
  },
  CREDITED: {
    label: "Credited",
    bg: "bg-slate-50",
    text: "text-slate-500",
    border: "border-slate-200",
    Icon: CreditCard,
  },
};

export default function InvoiceStatusBadge({ status, size = "md" }: Props) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG["DRAFT"];
  const { label, bg, text, border, Icon } = config;

  const sizeClasses =
    size === "sm"
      ? "text-[10px] px-1.5 py-0.5 gap-1"
      : "text-[11px] px-2 py-1 gap-1.5";

  return (
    <span
      className={`inline-flex items-center font-semibold rounded-full border ${bg} ${text} ${border} ${sizeClasses}`}
    >
      <Icon className={size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3"} />
      {label}
    </span>
  );
}
