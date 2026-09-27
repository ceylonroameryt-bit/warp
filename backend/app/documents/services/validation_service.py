"""
Warp Ladger — Document Validation Engine
Deterministic financial, mathematical, date, and invoice fraud checks.
Never trusts AI arithmetic blindly.
"""
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from app.documents.providers.base import LineExtraction
from app.documents.schemas import MathValidationResponse

# Rounding tolerance in GBP/currency units
ROUNDING_TOLERANCE = Decimal("0.05")

# Bank details heuristic patterns
SORT_CODE_PATTERN = re.compile(r"\b(\d{2})[- ](\d{2})[- ](\d{2})\b")
ACCOUNT_NUMBER_PATTERN = re.compile(r"\b\d{8}\b")
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b")


class DocumentValidationService:
    """Performs deterministic sanity checks on extracted financial data."""

    @staticmethod
    def validate_totals(
        subtotal: Optional[Decimal],
        discount_total: Optional[Decimal],
        tax_total: Optional[Decimal],
        total: Optional[Decimal],
    ) -> MathValidationResponse:
        sub = subtotal or Decimal("0")
        disc = discount_total or Decimal("0")
        tax = tax_total or Decimal("0")
        declared = total or Decimal("0")

        calculated = sub - disc + tax
        diff = abs(declared - calculated)
        is_valid = diff <= ROUNDING_TOLERANCE

        notes = None
        if not is_valid:
            notes = (
                f"Financial mismatch: Subtotal ({sub:.2f}) - Discount ({disc:.2f}) "
                f"+ Tax ({tax:.2f}) = {calculated:.2f}, but extracted Total is {declared:.2f}. "
                f"Discrepancy: {diff:.2f}."
            )

        return MathValidationResponse(
            is_valid=is_valid,
            subtotal=sub,
            discount_total=disc,
            tax_total=tax,
            calculated_total=calculated,
            declared_total=declared,
            difference=diff,
            notes=notes,
        )

    @staticmethod
    def validate_lines(
        lines: list[LineExtraction], declared_subtotal: Optional[Decimal]
    ) -> tuple[bool, Optional[str]]:
        """Cross-checks line items calculations and line totals sum."""
        if not lines:
            return True, None

        sum_line_nets = Decimal("0")
        issues: list[str] = []

        for idx, line in enumerate(lines):
            pos = line.position or idx + 1
            if line.quantity is not None and line.unit_price is not None and line.net_amount is not None:
                expected_net = line.quantity * line.unit_price
                if abs(expected_net - line.net_amount) > ROUNDING_TOLERANCE:
                    issues.append(
                        f"Line {pos}: {line.quantity} × {line.unit_price} = {expected_net:.2f}, "
                        f"extracted net is {line.net_amount:.2f}."
                    )

            if line.net_amount is not None and line.tax_rate is not None and line.tax_amount is not None:
                expected_tax = line.net_amount * (line.tax_rate / Decimal("100"))
                if abs(expected_tax - line.tax_amount) > ROUNDING_TOLERANCE:
                    issues.append(
                        f"Line {pos}: Tax on {line.net_amount:.2f} @ {line.tax_rate}% is {expected_tax:.2f}, "
                        f"extracted tax is {line.tax_amount:.2f}."
                    )

            if line.net_amount is not None:
                sum_line_nets += line.net_amount

        if declared_subtotal is not None and len(lines) > 1:
            diff = abs(sum_line_nets - declared_subtotal)
            if diff > ROUNDING_TOLERANCE:
                issues.append(
                    f"Sum of lines ({sum_line_nets:.2f}) does not match document subtotal ({declared_subtotal:.2f})."
                )

        if issues:
            return False, "; ".join(issues)
        return True, None

    @staticmethod
    def validate_dates(
        invoice_date: Optional[datetime], due_date: Optional[datetime]
    ) -> tuple[bool, Optional[str]]:
        if not invoice_date:
            return True, None

        if due_date and due_date < invoice_date:
            return False, "Due date cannot be before invoice date."

        now = datetime.now(UTC)
        # Check for absurd invoice dates (e.g. > 10 years ago or > 2 years in future)
        inv_dt = invoice_date if invoice_date.tzinfo else invoice_date.replace(tzinfo=UTC)
        if (inv_dt - now).days > 730:
            return False, "Invoice date is more than 2 years in the future."
        if (now - inv_dt).days > 3650:
            return False, "Invoice date is more than 10 years in the past."

        return True, None

    @staticmethod
    def detect_bank_details(raw_text: str) -> tuple[bool, Optional[str]]:
        """
        Scans document text for supplier banking details.
        Alerts the bookkeeper to prevent invoice redirect fraud.
        """
        if not raw_text:
            return False, None

        found_sort = SORT_CODE_PATTERN.search(raw_text)
        found_iban = IBAN_PATTERN.search(raw_text)

        if found_sort or found_iban:
            return (
                True,
                "Bank details detected in document. Never update supplier payment information automatically. "
                "Independent telephone or callback verification with the supplier is strongly recommended.",
            )

        return False, None
