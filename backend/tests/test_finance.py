"""Unit tests for the acquisition-cost engine. Pure functions, no model needed."""

import math

import pytest

from backend.config import LTV_TIERS
from backend.finance import (
    compute_emi,
    compute_gst,
    cost_breakdown,
    effective_loan,
    get_ltv,
    stamp_duty_rate,
)


@pytest.mark.parametrize("loan,expected", [
    (1_000_000, 0.90),
    (3_000_000, 0.90),       # boundary belongs to the lower tier
    (3_000_001, 0.80),
    (7_500_000, 0.80),
    (7_500_001, 0.75),
    (50_000_000, 0.75),
])
def test_ltv_tiers_by_loan_amount(loan, expected):
    assert get_ltv(loan) == expected


def test_ltv_tier_table_matches_rbi_brackets():
    assert [t[1] for t in LTV_TIERS] == [0.90, 0.80, 0.75]


def test_emi_matches_closed_form_and_amortises_to_zero():
    principal, rate, years = 5_000_000, 8.5, 20
    emi = compute_emi(principal, rate, years)
    r, n = rate / 1200, years * 12
    assert emi == pytest.approx(principal * r * (1 + r) ** n / ((1 + r) ** n - 1), rel=1e-12)
    balance = principal
    for _ in range(n):
        balance = balance * (1 + r) - emi
    assert balance == pytest.approx(0, abs=1e-4)


def test_emi_zero_rate_is_straight_line():
    assert compute_emi(1_200_000, 0.0, 10) == pytest.approx(10_000)


def test_emi_rejects_non_positive_tenure():
    with pytest.raises(ValueError):
        compute_emi(1_000_000, 8.5, 0)


def test_effective_loan_applies_cap_when_down_payment_too_low():
    # 5% down on Rs 1 Cr => loan 95L, tier 75% => capped at 75L
    loan, capped = effective_loan(10_000_000, 5.0)
    assert capped is True
    assert loan == pytest.approx(7_500_000)


def test_effective_loan_no_cap_when_down_payment_sufficient():
    loan, capped = effective_loan(10_000_000, 25.0)
    assert capped is False
    assert loan == pytest.approx(7_500_000)


def test_effective_loan_rejects_non_positive_value():
    with pytest.raises(ValueError):
        effective_loan(0, 20)


def test_gst_rules():
    assert compute_gst(10_000_000, is_under_construction=False) == 0.0
    assert compute_gst(10_000_000, is_under_construction=True) == pytest.approx(500_000)
    # affordable threshold: below Rs 45L uses the 1% rate
    assert compute_gst(4_000_000, is_under_construction=True) == pytest.approx(40_000)


def test_stamp_duty_known_and_unknown_states():
    rate, status = stamp_duty_rate("Karnataka")
    assert rate == pytest.approx(0.065)
    assert status == "APPROXIMATE"
    rate, status = stamp_duty_rate("Atlantis")
    assert status == "FALLBACK"
    assert rate == pytest.approx(0.065)


def test_cost_breakdown_is_internally_consistent():
    out = cost_breakdown(
        state="Maharashtra", property_value=12_000_000, down_payment_pct=20,
        annual_rate_pct=8.5, tenure_years=20, is_under_construction=True,
    )
    assert out["down_payment"] + out["loan_amount"] == pytest.approx(12_000_000)
    assert out["upfront_cash"] == pytest.approx(out["down_payment"] + out["stamp_duty"] + out["gst"])
    assert out["total_acquisition_cost"] == pytest.approx(12_000_000 + out["stamp_duty"] + out["gst"])
    assert out["total_repayment"] == pytest.approx(out["loan_amount"] + out["total_interest"])
    assert out["stamp_duty_rate"] == pytest.approx(0.06)
    # 20% down on Rs 1.2 Cr => loan Rs 96L (75% tier) => cap at 75% = Rs 90L
    assert out["ltv_cap_applied"] is True
    assert out["loan_amount"] == pytest.approx(9_000_000)
    assert out["ltv_ratio"] == pytest.approx(0.75)


def test_cost_breakdown_ready_to_move_has_no_gst():
    out = cost_breakdown(
        state="Karnataka", property_value=8_000_000, down_payment_pct=20,
        annual_rate_pct=8.5, tenure_years=20, is_under_construction=False,
    )
    assert out["gst"] == 0.0


def test_cost_breakdown_rejects_non_positive_value():
    with pytest.raises(ValueError):
        cost_breakdown(state=None, property_value=-1, down_payment_pct=20,
                       annual_rate_pct=8.5, tenure_years=20, is_under_construction=False)
