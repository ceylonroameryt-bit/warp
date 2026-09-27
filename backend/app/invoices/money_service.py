"""
Warp Ladger — Money Service
Centralised financial calculation engine using Python Decimal.
NEVER use float arithmetic for monetary amounts.

All rounding uses ROUND_HALF_UP with configurable decimal places.
The frontend must never control final totals — always verify server-side.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

# ─── Constants ───────────────────────────────────────────────
TWO_DP = Decimal("0.01")
FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0")


# ─── Data Classes ────────────────────────────────────────────
@dataclass
class LineCalcResult:
    """Result of a single invoice line calculation."""
    quantity: Decimal
    unit_price: Decimal
    discount_type: Optional[str]
    discount_value: Decimal
    discount_amount: Decimal       # derived
    net_amount: Decimal            # qty × price − discount
    tax_rate: Decimal              # e.g. 20.0000
    tax_amount: Decimal            # net × (rate / 100)
    gross_amount: Decimal          # net + tax


@dataclass
class InvoiceTotals:
    """Aggregated totals for a complete invoice."""
    subtotal: Decimal       # sum of net_amounts (before invoice-level discount)
    discount_total: Decimal # sum of discount_amounts across all lines
    tax_total: Decimal      # sum of tax_amounts
    total: Decimal          # subtotal − discount_total + tax_total
    amount_paid: Decimal = field(default_factory=lambda: ZERO)
    amount_due: Decimal = field(default_factory=lambda: ZERO)

    def __post_init__(self) -> None:
        self.amount_due = self.total - self.amount_paid


# ─── Money Service ───────────────────────────────────────────
class MoneyService:
    """
    Central financial calculation service.

    Rules:
    - All inputs coerced to Decimal via _d()
    - Rounding is ROUND_HALF_UP, applied once at presentation boundary
    - Internal precision retained at 4dp (NUMERIC 19,4)
    - Presentation rounds to 2dp for GBP/most currencies
    """

    # ── Conversion helper ────────────────────────────────────
    @staticmethod
    def _d(value) -> Decimal:
        """Safely convert any numeric input to Decimal."""
        if isinstance(value, Decimal):
            return value
        if value is None:
            return ZERO
        return Decimal(str(value))

    # ── Rounding ─────────────────────────────────────────────
    @staticmethod
    def round_currency(value, dp: int = 2) -> Decimal:
        """Round to specified decimal places using ROUND_HALF_UP."""
        quant = Decimal("0.1") ** dp
        return MoneyService._d(value).quantize(quant, rounding=ROUND_HALF_UP)

    # ── Line Calculation ─────────────────────────────────────
    @staticmethod
    def calculate_line(
        quantity,
        unit_price,
        tax_rate: Decimal,
        discount_type: Optional[str] = None,
        discount_value=None,
    ) -> LineCalcResult:
        """
        Calculate a single invoice line.

        Args:
            quantity:       Number of units (can be decimal, e.g. 1.5 hours)
            unit_price:     Price per unit
            tax_rate:       Rate as percentage, e.g. Decimal('20.0000') for 20%
            discount_type:  'PERCENTAGE' | 'FIXED' | None
            discount_value: Amount of discount

        Returns:
            LineCalcResult with all derived monetary fields.
        """
        qty = MoneyService._d(quantity)
        price = MoneyService._d(unit_price)
        rate = MoneyService._d(tax_rate)
        disc_val = MoneyService._d(discount_value)

        gross_before_discount = qty * price

        # Calculate discount amount
        if discount_type == "PERCENTAGE":
            discount_amount = MoneyService.round_currency(gross_before_discount * (disc_val / Decimal("100")))
        elif discount_type == "FIXED":
            discount_amount = MoneyService.round_currency(min(disc_val, gross_before_discount))
        else:
            discount_amount = ZERO

        net_amount = MoneyService.round_currency(gross_before_discount - discount_amount)

        # Tax is calculated on the net (post-discount) amount
        tax_amount = MoneyService.round_currency(net_amount * (rate / Decimal("100")))
        gross_amount = MoneyService.round_currency(net_amount + tax_amount)

        return LineCalcResult(
            quantity=qty,
            unit_price=price,
            discount_type=discount_type,
            discount_value=disc_val,
            discount_amount=discount_amount,
            net_amount=net_amount,
            tax_rate=rate,
            tax_amount=tax_amount,
            gross_amount=gross_amount,
        )

    # ── Invoice Totals ────────────────────────────────────────
    @staticmethod
    def calculate_invoice_totals(lines: list[LineCalcResult]) -> InvoiceTotals:
        """
        Aggregate line-level results into invoice-level totals.
        All summation happens in Decimal to avoid floating-point drift.
        """
        subtotal = MoneyService.round_currency(sum((ln.net_amount for ln in lines), ZERO))
        discount_total = MoneyService.round_currency(sum((ln.discount_amount for ln in lines), ZERO))
        tax_total = MoneyService.round_currency(sum((ln.tax_amount for ln in lines), ZERO))
        total = MoneyService.round_currency(subtotal + tax_total)  # discount already deducted in net_amount

        return InvoiceTotals(
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            total=total,
            amount_paid=ZERO,
            amount_due=total,
        )

    # ── Validation ────────────────────────────────────────────
    @staticmethod
    def verify_totals(
        lines: list[LineCalcResult],
        claimed_subtotal,
        claimed_tax_total,
        claimed_total,
        tolerance=None,
    ) -> bool:
        """
        Verify that claimed totals match recalculated values.
        Returns True if within tolerance (default 0.01 for rounding differences).
        This is a defensive check; the backend always wins.
        """
        if tolerance is None:
            tolerance = Decimal("0.01")

        recalculated = MoneyService.calculate_invoice_totals(lines)

        def within(a, b) -> bool:
            return abs(MoneyService._d(a) - MoneyService._d(b)) <= tolerance

        return (
            within(claimed_subtotal, recalculated.subtotal)
            and within(claimed_tax_total, recalculated.tax_total)
            and within(claimed_total, recalculated.total)
        )
