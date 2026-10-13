"""Acquisition-cost engine.

Calculations resolve versioned, effective-dated rules in force on the valuation date,
with provenance citations and reproducible audit trail.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from backend.config import (
    GST_AFFORDABLE_RATE,
    GST_AFFORDABLE_THRESHOLD,
    GST_UNDER_CONSTRUCTION_RATE,
    LTV_TIERS,
    STAMP_DUTY_BY_STATE,
    STAMP_DUTY_DEFAULT,
    STAMP_DUTY_STATUS,
)
from backend.rule_engine import (
    build_applied_rules_snapshot,
    resolve_gst_rate,
    resolve_ltv_tiers,
    resolve_stamp_duty,
)


def get_ltv(loan_amount: float, valuation_date: Optional[datetime.date | str] = None) -> float:
    """RBI maximum LTV for a loan amount (tier chosen by loan size on valuation date)."""
    tiers = resolve_ltv_tiers(valuation_date=valuation_date)
    for t in tiers:
        if loan_amount <= t["max_loan_inr"]:
            return t["ltv_ratio"]
    return tiers[-1]["ltv_ratio"] if tiers else 0.75


def compute_emi(principal: float, annual_rate_pct: float, tenure_years: int) -> float:
    """Monthly EMI, reducing-balance amortisation."""
    if tenure_years <= 0:
        raise ValueError("tenure_years must be positive")
    r = annual_rate_pct / 12 / 100
    n = tenure_years * 12
    if principal <= 0:
        return 0.0
    if r == 0:
        return principal / n
    growth = (1 + r) ** n
    return principal * r * growth / (growth - 1)


def stamp_duty_rate(
    state: str | None,
    valuation_date: Optional[datetime.date | str] = None,
) -> tuple[float, str]:
    """Return (rate, status). Unknown state falls back to the national default."""
    if state:
        res = resolve_stamp_duty(state, valuation_date=valuation_date)
        return res["rate"], res.get("verification_status", STAMP_DUTY_STATUS)
    return STAMP_DUTY_DEFAULT, "FALLBACK"


def compute_gst(
    property_value: float,
    is_under_construction: bool,
    valuation_date: Optional[datetime.date | str] = None,
) -> float:
    """GST on under-construction property (upper bound, CBIC notification)."""
    status = "Under Construction" if is_under_construction else "Ready to Move"
    res = resolve_gst_rate(status, property_value, valuation_date=valuation_date)
    return property_value * res["rate"]


def effective_loan(
    property_value: float,
    down_payment_pct: float,
    valuation_date: Optional[datetime.date | str] = None,
) -> tuple[float, bool]:
    """Loan after the RBI LTV cap. Returns (loan_amount, cap_applied).

    The single source for the loan figure, so the estimate and the EMI grid
    never disagree.
    """
    if property_value <= 0:
        raise ValueError("property_value must be positive")
    loan = property_value * (1 - down_payment_pct / 100)
    max_ltv = get_ltv(loan, valuation_date=valuation_date)
    if loan > property_value * max_ltv:
        return property_value * max_ltv, True
    return loan, False


def cost_breakdown(
    *,
    state: str | None,
    property_value: float,
    down_payment_pct: float,
    annual_rate_pct: float,
    tenure_years: int,
    is_under_construction: bool,
    valuation_date: Optional[datetime.date | str] = None,
) -> dict[str, Any]:
    """Full acquisition cost stack. All money values are INR floats."""
    if property_value <= 0:
        raise ValueError("property_value must be positive")

    loan_amount, capped = effective_loan(property_value, down_payment_pct, valuation_date=valuation_date)
    down_payment = property_value - loan_amount

    rate, duty_status = stamp_duty_rate(state, valuation_date=valuation_date)
    stamp_duty = property_value * rate
    gst = compute_gst(property_value, is_under_construction, valuation_date=valuation_date)
    emi = compute_emi(loan_amount, annual_rate_pct, tenure_years)
    total_interest = emi * tenure_years * 12 - loan_amount
    upfront_cash = down_payment + stamp_duty + gst

    # Build full reproducible rules snapshot
    rules_snapshot = build_applied_rules_snapshot(
        state=state or "DEFAULT",
        construction_status="Under Construction" if is_under_construction else "Ready to Move",
        property_value=property_value,
        valuation_date=valuation_date,
    )

    return {
        "property_value": property_value,
        "down_payment": down_payment,
        "down_payment_requested_pct": down_payment_pct,
        "ltv_cap_applied": capped,
        "ltv_ratio": loan_amount / property_value,
        "loan_amount": loan_amount,
        "monthly_emi": emi,
        "total_interest": total_interest,
        "total_repayment": loan_amount + total_interest,
        "stamp_duty": stamp_duty,
        "stamp_duty_rate": rate,
        "stamp_duty_status": duty_status,
        "gst": gst,
        "upfront_cash": upfront_cash,
        "total_acquisition_cost": property_value + stamp_duty + gst,
        "state": state,
        "applied_rules_snapshot": rules_snapshot,
    }
