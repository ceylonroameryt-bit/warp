import React from "react";

interface PaymentStatusBadgeProps {
  status: string;
  className?: string;
}

export function PaymentStatusBadge({ status, className = "" }: PaymentStatusBadgeProps) {
  const getBadgeStyle = (statusVal: string) => {
    switch (statusVal?.toUpperCase()) {
      case "POSTED":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "DRAFT":
        return "bg-slate-100 text-slate-700 border-slate-200";
      case "VOIDED":
        return "bg-rose-50 text-rose-700 border-rose-200 line-through";
      case "REFUNDED":
        return "bg-amber-50 text-amber-800 border-amber-200";
      default:
        return "bg-slate-100 text-slate-600 border-slate-200";
    }
  };

  const getStatusLabel = (statusVal: string) => {
    switch (statusVal?.toUpperCase()) {
      case "POSTED":
        return "Posted / Cleared";
      case "DRAFT":
        return "Draft";
      case "VOIDED":
        return "Voided";
      case "REFUNDED":
        return "Refunded";
      default:
        return statusVal || "Unknown";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${getBadgeStyle(
        status
      )} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-75" />
      {getStatusLabel(status)}
    </span>
  );
}

export function PaymentTypeBadge({ type, className = "" }: { type: string; className?: string }) {
  const isIncoming = type?.toUpperCase() === "INCOMING";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${
        isIncoming
          ? "bg-teal-50 text-teal-700 border-teal-200"
          : "bg-indigo-50 text-indigo-700 border-indigo-200"
      } ${className}`}
    >
      <span className="mr-1">{isIncoming ? "↓ Received" : "↑ Sent"}</span>
      {isIncoming ? "Customer Receipt" : "Supplier Payment"}
    </span>
  );
}
