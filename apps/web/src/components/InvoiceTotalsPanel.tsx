"use client";

import React from "react";
import { LineItem, TaxRate } from "./InvoiceLineEditor";

interface Props {
  lines: LineItem[];
  taxRates: TaxRate[];
  currency?: string;
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
  return { net, tax, discount, gross: net + tax };
}

function fmt(v: number, currency = "GBP") {
  const s = { GBP: "£", USD: "$", EUR: "€" }[currency] ?? currency + " ";
  return `${s}${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function InvoiceTotalsPanel({ lines, taxRates, currency = "GBP" }: Props) {
  const calcs = lines.map((l) => calcLine(l, taxRates));
  const subtotal = calcs.reduce((a, c) => a + c.net, 0);
  const discountTotal = calcs.reduce((a, c) => a + c.discount, 0);
  const taxTotal = calcs.reduce((a, c) => a + c.tax, 0);
  const total = subtotal + taxTotal;

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-slate-600">
          <span>Subtotal</span>
          <span className="tabular-nums font-medium">{fmt(subtotal, currency)}</span>
        </div>

        {discountTotal > 0 && (
          <div className="flex justify-between text-sm text-emerald-700">
            <span>Discount</span>
            <span className="tabular-nums font-medium">−{fmt(discountTotal, currency)}</span>
          </div>
        )}

        <div className="flex justify-between text-sm text-slate-600">
          <span>VAT</span>
          <span className="tabular-nums font-medium">{fmt(taxTotal, currency)}</span>
        </div>

        <div className="border-t-2 border-slate-300 pt-3 flex justify-between">
          <span className="text-base font-bold text-slate-900">Total</span>
          <span className="text-xl font-bold text-slate-900 tabular-nums">
            {fmt(total, currency)}
          </span>
        </div>
      </div>

      <p className="text-[10px] text-slate-400 mt-3 leading-relaxed">
        * Preview only. Final totals are recalculated and verified by the server.
      </p>
    </div>
  );
}
