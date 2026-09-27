"use client";

import React from "react";
import { Trash2, Plus, GripVertical } from "lucide-react";

export interface TaxRate {
  id: string;
  name: string;
  code: string;
  rate: string;
}

export interface BillLineItem {
  id?: string;
  description: string;
  purchase_category?: string;
  quantity: string;
  unit_price: string;
  tax_rate_id: string;
  discount_type?: "PERCENTAGE" | "FIXED" | "";
  discount_value: string;
  position: number;
  _net?: number;
  _tax?: number;
  _gross?: number;
}

interface Props {
  lines: BillLineItem[];
  taxRates: TaxRate[];
  onChange: (lines: BillLineItem[]) => void;
  currency?: string;
  disabled?: boolean;
}

export const PURCHASE_CATEGORIES = [
  "General Expense",
  "Software & SaaS",
  "Rent & Rates",
  "Utilities",
  "Office Supplies",
  "Professional Fees",
  "Marketing & Advertising",
  "Travel & Subsistence",
  "Hardware & Equipment",
  "Subcontractor Costs",
  "Telecoms & Internet",
  "Other",
];

function fmt(v: number | undefined, currency = "GBP") {
  if (v === undefined || isNaN(v)) return "—";
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function calcBillLine(line: BillLineItem, taxRates: TaxRate[]) {
  const qty = parseFloat(line.quantity) || 0;
  const price = parseFloat(line.unit_price) || 0;
  const raw = qty * price;

  let discount = 0;
  if (line.discount_type === "PERCENTAGE") {
    discount = raw * ((parseFloat(line.discount_value) || 0) / 100);
  } else if (line.discount_type === "FIXED") {
    discount = Math.min(parseFloat(line.discount_value) || 0, raw);
  }
  const net = Math.max(0, raw - discount);

  const tr = taxRates.find((r) => r.id === line.tax_rate_id);
  const rate = tr ? parseFloat(tr.rate) : 0;
  const tax = net * (rate / 100);
  const gross = net + tax;

  return { net, tax, gross };
}

export default function BillLineEditor({
  lines,
  taxRates,
  onChange,
  currency = "GBP",
  disabled = false,
}: Props) {
  function updateLine(idx: number, patch: Partial<BillLineItem>) {
    const updated = lines.map((l, i) => {
      if (i !== idx) return l;
      const next = { ...l, ...patch };
      const { net, tax, gross } = calcBillLine(next, taxRates);
      return { ...next, _net: net, _tax: tax, _gross: gross };
    });
    onChange(updated);
  }

  function addLine() {
    const defaultTaxId = taxRates.length > 0 ? taxRates[0].id : "";
    const newLine: BillLineItem = {
      description: "",
      purchase_category: "General Expense",
      quantity: "1",
      unit_price: "0.00",
      tax_rate_id: defaultTaxId,
      discount_type: "",
      discount_value: "0",
      position: lines.length,
    };
    const { net, tax, gross } = calcBillLine(newLine, taxRates);
    onChange([...lines, { ...newLine, _net: net, _tax: tax, _gross: gross }]);
  }

  function removeLine(idx: number) {
    if (lines.length <= 1) return;
    onChange(
      lines
        .filter((_, i) => i !== idx)
        .map((l, i) => ({ ...l, position: i }))
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
            <tr>
              <th className="w-7 py-3 pl-3 pr-1 text-center">#</th>
              <th className="py-3 px-2 min-w-[200px]">Description</th>
              <th className="py-3 px-2 w-36">Category</th>
              <th className="py-3 px-2 w-20 text-right">Qty</th>
              <th className="py-3 px-2 w-28 text-right">Unit Price</th>
              <th className="py-3 px-2 w-32">VAT / Tax</th>
              <th className="py-3 px-2 w-28 text-right">Gross Total</th>
              <th className="w-9 py-3 pr-3 text-center"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {lines.map((line, idx) => {
              const { gross } = calcBillLine(line, taxRates);
              return (
                <tr key={idx} className="hover:bg-slate-50/70 transition-colors group">
                  <td className="py-2.5 pl-3 pr-1 text-center text-slate-400 font-mono text-[11px]">
                    <div className="flex items-center justify-center gap-1">
                      <GripVertical className="h-3 w-3 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
                      <span>{idx + 1}</span>
                    </div>
                  </td>

                  {/* Description */}
                  <td className="py-2.5 px-2">
                    <input
                      type="text"
                      disabled={disabled}
                      placeholder="e.g. Monthly subscription or services..."
                      value={line.description}
                      onChange={(e) => updateLine(idx, { description: e.target.value })}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white placeholder-slate-400 focus:outline-none focus:border-sky-500 text-xs text-slate-800"
                    />
                  </td>

                  {/* Category */}
                  <td className="py-2.5 px-2">
                    <select
                      disabled={disabled}
                      value={line.purchase_category || "General Expense"}
                      onChange={(e) => updateLine(idx, { purchase_category: e.target.value })}
                      className="w-full px-2 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 focus:outline-none focus:border-sky-500"
                    >
                      {PURCHASE_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Quantity */}
                  <td className="py-2.5 px-2">
                    <input
                      type="number"
                      step="any"
                      min="0.0001"
                      disabled={disabled}
                      value={line.quantity}
                      onChange={(e) => updateLine(idx, { quantity: e.target.value })}
                      className="w-full px-2 py-1.5 rounded-lg border border-slate-200 bg-white text-right text-xs text-slate-800 focus:outline-none focus:border-sky-500"
                    />
                  </td>

                  {/* Unit Price */}
                  <td className="py-2.5 px-2">
                    <input
                      type="number"
                      step="any"
                      min="0"
                      disabled={disabled}
                      value={line.unit_price}
                      onChange={(e) => updateLine(idx, { unit_price: e.target.value })}
                      className="w-full px-2 py-1.5 rounded-lg border border-slate-200 bg-white text-right text-xs text-slate-800 focus:outline-none focus:border-sky-500 font-mono"
                    />
                  </td>

                  {/* Tax Rate */}
                  <td className="py-2.5 px-2">
                    <select
                      disabled={disabled}
                      value={line.tax_rate_id}
                      onChange={(e) => updateLine(idx, { tax_rate_id: e.target.value })}
                      className="w-full px-2 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 focus:outline-none focus:border-sky-500"
                    >
                      <option value="">No VAT (0%)</option>
                      {taxRates.map((tr) => (
                        <option key={tr.id} value={tr.id}>
                          {tr.code} ({parseFloat(tr.rate)}%)
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Gross Total */}
                  <td className="py-2.5 px-2 text-right font-bold text-slate-900 font-mono">
                    {fmt(gross, currency)}
                  </td>

                  {/* Remove action */}
                  <td className="py-2.5 pr-3 text-center">
                    <button
                      type="button"
                      disabled={disabled || lines.length <= 1}
                      onClick={() => removeLine(idx)}
                      className="p-1 rounded text-slate-300 hover:text-rose-600 hover:bg-rose-50 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                      title="Remove line"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add Line Action */}
      {!disabled && (
        <div className="p-3 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={addLine}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-sky-700 hover:text-sky-800 bg-white border border-sky-200 rounded-lg hover:bg-sky-50 shadow-xs transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Purchase Line
          </button>
          <span className="text-[11px] text-slate-400">
            {lines.length} {lines.length === 1 ? "line item" : "line items"}
          </span>
        </div>
      )}
    </div>
  );
}
