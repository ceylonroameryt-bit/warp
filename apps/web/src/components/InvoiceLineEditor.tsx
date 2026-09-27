"use client";

import React from "react";
import { Trash2, Plus, GripVertical } from "lucide-react";

export interface TaxRate {
  id: string;
  name: string;
  code: string;
  rate: string;
}

export interface LineItem {
  id?: string;           // undefined for new lines
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate_id: string;
  discount_type?: "PERCENTAGE" | "FIXED" | "";
  discount_value: string;
  position: number;
  // Computed (display only; backend recalculates on save)
  _net?: number;
  _tax?: number;
  _gross?: number;
}

interface Props {
  lines: LineItem[];
  taxRates: TaxRate[];
  onChange: (lines: LineItem[]) => void;
  currency?: string;
  disabled?: boolean;
}

function fmt(v: number | undefined, currency = "GBP") {
  if (v === undefined || isNaN(v)) return "—";
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function calcLine(line: LineItem, taxRates: TaxRate[]) {
  const qty = parseFloat(line.quantity) || 0;
  const price = parseFloat(line.unit_price) || 0;
  const raw = qty * price;

  let discount = 0;
  if (line.discount_type === "PERCENTAGE") {
    discount = raw * ((parseFloat(line.discount_value) || 0) / 100);
  } else if (line.discount_type === "FIXED") {
    discount = Math.min(parseFloat(line.discount_value) || 0, raw);
  }
  const net = raw - discount;

  const tr = taxRates.find((r) => r.id === line.tax_rate_id);
  const rate = tr ? parseFloat(tr.rate) : 0;
  const tax = net * (rate / 100);
  const gross = net + tax;

  return { net, tax, gross };
}

export default function InvoiceLineEditor({
  lines,
  taxRates,
  onChange,
  currency = "GBP",
  disabled = false,
}: Props) {
  function updateLine(idx: number, field: keyof LineItem, value: string) {
    const updated = lines.map((l, i) =>
      i === idx ? { ...l, [field]: value } : l
    );
    onChange(updated);
  }

  function addLine() {
    onChange([
      ...lines,
      {
        description: "",
        quantity: "1",
        unit_price: "0.00",
        tax_rate_id: taxRates[0]?.id ?? "",
        discount_type: "",
        discount_value: "0",
        position: lines.length,
      },
    ]);
  }

  function removeLine(idx: number) {
    onChange(lines.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-0">
      {/* Header row */}
      <div className="hidden lg:grid grid-cols-[auto_1fr_80px_110px_140px_110px_90px_36px] gap-2 px-3 py-2 bg-slate-800 text-slate-300 text-[11px] font-semibold uppercase tracking-wide rounded-t-lg">
        <div />
        <div>Description</div>
        <div className="text-right">Qty</div>
        <div className="text-right">Unit Price</div>
        <div>Tax Rate</div>
        <div className="text-right">Discount</div>
        <div className="text-right">Amount</div>
        <div />
      </div>

      {lines.length === 0 && (
        <div className="flex items-center justify-center py-10 border-2 border-dashed border-slate-200 rounded-lg text-sm text-slate-400">
          No line items yet. Click below to add one.
        </div>
      )}

      {lines.map((line, idx) => {
        const calc = calcLine(line, taxRates);
        return (
          <div
            key={idx}
            className={`group grid grid-cols-1 lg:grid-cols-[auto_1fr_80px_110px_140px_110px_90px_36px] gap-2 px-3 py-3 border-b border-slate-100 hover:bg-slate-50 transition-colors ${
              idx === 0 ? "" : ""
            }`}
          >
            {/* Drag handle */}
            <div className="hidden lg:flex items-center text-slate-300">
              <GripVertical className="h-4 w-4" />
            </div>

            {/* Description */}
            <div className="lg:col-auto">
              <label className="lg:hidden text-[10px] text-slate-400 mb-0.5 block">Description</label>
              <input
                type="text"
                value={line.description}
                onChange={(e) => updateLine(idx, "description", e.target.value)}
                placeholder="Item description…"
                disabled={disabled}
                className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-200 transition-all"
              />
            </div>

            {/* Quantity */}
            <div>
              <label className="lg:hidden text-[10px] text-slate-400 mb-0.5 block">Qty</label>
              <input
                type="number"
                value={line.quantity}
                onChange={(e) => updateLine(idx, "quantity", e.target.value)}
                min="0"
                step="0.01"
                disabled={disabled}
                className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 text-right"
              />
            </div>

            {/* Unit Price */}
            <div>
              <label className="lg:hidden text-[10px] text-slate-400 mb-0.5 block">Unit Price</label>
              <div className="relative">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                  {currency === "GBP" ? "£" : currency === "EUR" ? "€" : "$"}
                </span>
                <input
                  type="number"
                  value={line.unit_price}
                  onChange={(e) => updateLine(idx, "unit_price", e.target.value)}
                  min="0"
                  step="0.01"
                  disabled={disabled}
                  className="w-full pl-6 pr-2 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 text-right"
                />
              </div>
            </div>

            {/* Tax Rate */}
            <div>
              <label className="lg:hidden text-[10px] text-slate-400 mb-0.5 block">Tax Rate</label>
              <select
                value={line.tax_rate_id}
                onChange={(e) => updateLine(idx, "tax_rate_id", e.target.value)}
                disabled={disabled}
                className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white"
              >
                <option value="">No Tax</option>
                {taxRates.map((tr) => (
                  <option key={tr.id} value={tr.id}>
                    {tr.name} ({tr.rate}%)
                  </option>
                ))}
              </select>
            </div>

            {/* Discount */}
            <div className="flex gap-1">
              <select
                value={line.discount_type ?? ""}
                onChange={(e) =>
                  updateLine(idx, "discount_type", e.target.value)
                }
                disabled={disabled}
                className="w-[70px] shrink-0 px-1.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 bg-white"
              >
                <option value="">None</option>
                <option value="PERCENTAGE">%</option>
                <option value="FIXED">£</option>
              </select>
              {line.discount_type ? (
                <input
                  type="number"
                  value={line.discount_value}
                  onChange={(e) => updateLine(idx, "discount_value", e.target.value)}
                  min="0"
                  step="0.01"
                  disabled={disabled}
                  className="w-full px-2 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-sky-400 text-right"
                />
              ) : (
                <div className="flex-1" />
              )}
            </div>

            {/* Gross Amount (display) */}
            <div className="flex items-center justify-end">
              <span className="text-sm font-semibold text-slate-800 tabular-nums">
                {fmt(calc.gross, currency)}
              </span>
            </div>

            {/* Remove */}
            <div className="flex items-center justify-center">
              <button
                type="button"
                onClick={() => removeLine(idx)}
                disabled={disabled}
                className="p-1 text-slate-300 hover:text-red-500 transition-colors disabled:opacity-40"
                aria-label="Remove line"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        );
      })}

      {/* Add Line */}
      {!disabled && (
        <button
          type="button"
          onClick={addLine}
          className="flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-sky-600 hover:text-sky-700 hover:bg-sky-50 rounded-b-lg transition-colors w-full"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Line Item
        </button>
      )}
    </div>
  );
}
