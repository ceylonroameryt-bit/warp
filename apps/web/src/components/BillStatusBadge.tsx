"use client";

import React from "react";
import {
  Clock,
  CheckCircle,
  AlertTriangle,
  Ban,
  DollarSign,
  XCircle,
  FileClock,
  CreditCard,
} from "lucide-react";

export type BillStatus =
  | "DRAFT"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "AWAITING_PAYMENT"
  | "PARTIALLY_PAID"
  | "PAID"
  | "OVERDUE"
  | "REJECTED"
  | "VOID";

interface Props {
  status: BillStatus | string;
  effectiveStatus?: string;
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
  AWAITING_APPROVAL: {
    label: "Awaiting Approval",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    Icon: FileClock,
  },
  APPROVED: {
    label: "Approved",
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    Icon: CheckCircle,
  },
  AWAITING_PAYMENT: {
    label: "Awaiting Payment",
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    border: "border-indigo-200",
    Icon: CreditCard,
  },
  OVERDUE: {
    label: "Overdue",
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    Icon: AlertTriangle,
  },
  PAID: {
    label: "Paid",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    Icon: DollarSign,
  },
  PARTIALLY_PAID: {
    label: "Partially Paid",
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
    Icon: DollarSign,
  },
  REJECTED: {
    label: "Rejected",
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    Icon: XCircle,
  },
  VOID: {
    label: "Void",
    bg: "bg-zinc-100",
    text: "text-zinc-500",
    border: "border-zinc-200",
    Icon: Ban,
  },
};

export default function BillStatusBadge({ status, effectiveStatus, size = "sm" }: Props) {
  const norm = (effectiveStatus || status || "").toUpperCase();
  const cfg = STATUS_CONFIG[norm] ?? {
    label: status,
    bg: "bg-slate-100",
    text: "text-slate-600",
    border: "border-slate-200",
    Icon: Clock,
  };

  const { Icon } = cfg;

  const sizeClasses =
    size === "md"
      ? "text-xs px-2.5 py-1 gap-1.5"
      : "text-[11px] px-2 py-0.5 gap-1";

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border} ${sizeClasses}`}
    >
      <Icon className={size === "md" ? "h-3.5 w-3.5" : "h-3 w-3"} />
      {cfg.label}
    </span>
  );
}
