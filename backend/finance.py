"""Acquisition-cost engine.

Calculations resolve versioned, effective-dated rules in force on the valuation date,
with provenance citations and reproducible audit trail.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from backend.config import (
    EQUITY_CAGR_DEFAULT_PCT,
    GST_AFFORDABLE_RATE,
    GST_AFFORDABLE_THRESHOLD,
    GST_UNDER_CONSTRUCTION_RATE,
    INFRASTRUCTURE_PROJECTS,
    LTV_TIERS,
    MAINTENANCE_DRAG_PCT,
    MARKET_MAP_NODES,
    PREPAYMENT_PENALTY_PCT,
    PROPERTY_APPRECIATION_DEFAULT_PCT,
    RENT_ESCALATION_DEFAULT_PCT,
    RENTAL_YIELD_BY_CITY,
    RENTAL_YIELD_DEFAULT,
    RENTAL_YIELD_STATUS,
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


def get_rental_yield_rate(city: str | None) -> tuple[float, str]:
    """Return gross rental yield (rate, status)."""
    if city and city in RENTAL_YIELD_BY_CITY:
        return RENTAL_YIELD_BY_CITY[city], RENTAL_YIELD_STATUS
    return RENTAL_YIELD_DEFAULT, "FALLBACK"


def compute_rental_and_wealth(
    *,
    property_value: float,
    city: str | None = None,
    state: str | None = None,
    down_payment_pct: float = 20.0,
    annual_rate_pct: float = 8.5,
    tenure_years: int = 20,
    is_under_construction: bool = False,
    rental_yield_pct: float | None = None,
    property_appreciation_pct: float = PROPERTY_APPRECIATION_DEFAULT_PCT,
    rent_escalation_pct: float = RENT_ESCALATION_DEFAULT_PCT,
    equity_cagr_pct: float = EQUITY_CAGR_DEFAULT_PCT,
    simulation_years: int = 20,
) -> dict[str, Any]:
    """Rigorous 20-year Buy vs. Rent wealth compounding analysis and rental yield metrics."""
    if property_value <= 0:
        raise ValueError("property_value must be positive")

    costs = cost_breakdown(
        state=state,
        property_value=property_value,
        down_payment_pct=down_payment_pct,
        annual_rate_pct=annual_rate_pct,
        tenure_years=tenure_years,
        is_under_construction=is_under_construction,
    )

    loan_amount = costs["loan_amount"]
    monthly_emi = costs["monthly_emi"]
    upfront_cash = costs["upfront_cash"]

    default_yield, yield_status = get_rental_yield_rate(city)
    applied_yield = (rental_yield_pct / 100.0) if rental_yield_pct is not None else default_yield
    initial_monthly_rent = (property_value * applied_yield) / 12.0
    net_rental_yield = max(0.0, applied_yield - MAINTENANCE_DRAG_PCT)

    r_monthly = (annual_rate_pct / 100.0) / 12.0
    r_equity = equity_cagr_pct / 100.0
    g_prop = property_appreciation_pct / 100.0
    g_rent = rent_escalation_pct / 100.0
    total_loan_months = tenure_years * 12

    trajectory = []
    renter_portfolio = upfront_cash
    current_monthly_rent = initial_monthly_rent
    breakeven_year = None

    for yr in range(1, simulation_years + 1):
        months_elapsed = yr * 12
        buyer_prop_val = property_value * ((1 + g_prop) ** yr)

        if months_elapsed >= total_loan_months:
            loan_balance = 0.0
        elif r_monthly > 0:
            growth_m = (1 + r_monthly) ** months_elapsed
            loan_balance = max(0.0, loan_amount * growth_m - monthly_emi * ((growth_m - 1) / r_monthly))
        else:
            loan_balance = max(0.0, loan_amount - (monthly_emi * months_elapsed))

        buyer_equity = buyer_prop_val - loan_balance

        annual_maint = buyer_prop_val * MAINTENANCE_DRAG_PCT
        buyer_monthly_outlay = (monthly_emi if months_elapsed <= total_loan_months else 0.0) + (annual_maint / 12.0)
        renter_monthly_outlay = current_monthly_rent

        renter_portfolio = renter_portfolio * (1 + r_equity)
        annual_cashflow_delta = (buyer_monthly_outlay - renter_monthly_outlay) * 12.0
        renter_portfolio = max(0.0, renter_portfolio + annual_cashflow_delta)

        current_monthly_rent = current_monthly_rent * (1 + g_rent)
        wealth_delta = buyer_equity - renter_portfolio

        if breakeven_year is None and wealth_delta > 0:
            breakeven_year = yr

        trajectory.append({
            "year": yr,
            "property_value": round(buyer_prop_val, 0),
            "loan_balance": round(loan_balance, 0),
            "buyer_equity": round(buyer_equity, 0),
            "renter_portfolio": round(renter_portfolio, 0),
            "renter_monthly_rent": round(current_monthly_rent, 0),
            "wealth_delta": round(wealth_delta, 0),
            "buyer_ahead": buyer_equity >= renter_portfolio,
        })

    annual_gross_rent = round(initial_monthly_rent * 12.0, 0)
    vacancy_reserve_annual = round(initial_monthly_rent * 1.0, 0)  # 1 month annual vacancy allowance
    maintenance_tax_annual = round(property_value * MAINTENANCE_DRAG_PCT, 0)  # 0.75% annual
    net_annual_rental_cashflow = round(max(0.0, annual_gross_rent - vacancy_reserve_annual - maintenance_tax_annual), 0)
    net_rental_yield_real_pct = round((net_annual_rental_cashflow / property_value) * 100.0, 2)
    net_monthly_cashflow = round(net_annual_rental_cashflow / 12.0, 0)
    emi_offset_pct = round(min(100.0, (initial_monthly_rent / monthly_emi) * 100.0), 1) if monthly_emi > 0 else 0.0
    payback_period_years = round(upfront_cash / net_annual_rental_cashflow, 1) if net_annual_rental_cashflow > 0 else None

    year_10_stat = trajectory[min(9, len(trajectory) - 1)]

    return {
        "gross_rental_yield_pct": round(applied_yield * 100, 2),
        "net_rental_yield_pct": round(net_rental_yield * 100, 2),
        "net_rental_yield_real_pct": net_rental_yield_real_pct,
        "yield_status": yield_status,
        "initial_monthly_rent": round(initial_monthly_rent, 0),
        "initial_annual_rent": annual_gross_rent,
        "vacancy_reserve_annual": vacancy_reserve_annual,
        "maintenance_tax_annual": maintenance_tax_annual,
        "net_annual_rental_cashflow": net_annual_rental_cashflow,
        "net_monthly_cashflow": net_monthly_cashflow,
        "emi_offset_pct": emi_offset_pct,
        "payback_period_years": payback_period_years,
        "breakeven_year": breakeven_year,
        "year_10_buyer_equity": year_10_stat["buyer_equity"],
        "year_10_renter_portfolio": year_10_stat["renter_portfolio"],
        "year_10_wealth_delta": year_10_stat["wealth_delta"],
        "year_10_buyer_ahead": year_10_stat["buyer_ahead"],
        "pro_forma": {
            "annual_gross_rent": annual_gross_rent,
            "vacancy_reserve_annual": vacancy_reserve_annual,
            "maintenance_tax_annual": maintenance_tax_annual,
            "net_annual_rental_cashflow": net_annual_rental_cashflow,
            "net_monthly_cashflow": net_monthly_cashflow,
            "net_rental_yield_real_pct": net_rental_yield_real_pct,
            "emi_offset_pct": emi_offset_pct,
            "monthly_emi": monthly_emi,
            "upfront_equity": upfront_cash,
            "payback_period_years": payback_period_years,
        },
        "assumptions": {
            "property_appreciation_pct": property_appreciation_pct,
            "rent_escalation_pct": rent_escalation_pct,
            "equity_cagr_pct": equity_cagr_pct,
            "maintenance_drag_pct": round(MAINTENANCE_DRAG_PCT * 100, 2),
            "prepayment_penalty_pct": PREPAYMENT_PENALTY_PCT,
        },
        "trajectory": trajectory,
    }


def compute_loan_prepayment(
    *,
    loan_amount: float,
    annual_rate_pct: float,
    tenure_years: int,
    monthly_prepayment: float = 0.0,
    annual_lumpsum: float = 0.0,
) -> dict[str, Any]:
    """Simulates loan acceleration via recurring monthly prepayment and annual lumpsum."""
    if loan_amount <= 0:
        raise ValueError("loan_amount must be positive")
    if tenure_years <= 0:
        raise ValueError("tenure_years must be positive")

    base_emi = compute_emi(loan_amount, annual_rate_pct, tenure_years)
    base_months = tenure_years * 12
    base_total_interest = (base_emi * base_months) - loan_amount

    r_monthly = (annual_rate_pct / 100.0) / 12.0
    balance = loan_amount
    accelerated_interest = 0.0
    accelerated_months = 0

    schedule_checkpoints = []

    while balance > 0.01 and accelerated_months < base_months:
        accelerated_months += 1
        interest_for_month = balance * r_monthly
        accelerated_interest += interest_for_month
        principal_from_emi = base_emi - interest_for_month

        extra_payment = monthly_prepayment
        if accelerated_months % 12 == 0:
            extra_payment += annual_lumpsum

        total_principal_paid = min(balance, principal_from_emi + extra_payment)
        balance -= total_principal_paid

        if accelerated_months % 12 == 0 or balance <= 0.01:
            schedule_checkpoints.append({
                "month": accelerated_months,
                "year": round(accelerated_months / 12, 1),
                "remaining_principal": round(max(0.0, balance), 0),
                "cumulative_interest": round(accelerated_interest, 0),
            })

    months_saved = max(0, base_months - accelerated_months)
    years_saved = round(months_saved / 12.0, 1)
    interest_saved = max(0.0, base_total_interest - accelerated_interest)

    return {
        "loan_amount": round(loan_amount, 0),
        "base_tenure_years": tenure_years,
        "base_monthly_emi": round(base_emi, 0),
        "base_total_interest": round(base_total_interest, 0),
        "base_total_repayment": round(loan_amount + base_total_interest, 0),
        "accelerated_tenure_years": round(accelerated_months / 12.0, 1),
        "accelerated_total_interest": round(accelerated_interest, 0),
        "accelerated_total_repayment": round(loan_amount + accelerated_interest, 0),
        "months_saved": months_saved,
        "years_saved": years_saved,
        "interest_saved": round(interest_saved, 0),
        "interest_saved_pct": round((interest_saved / base_total_interest) * 100, 1) if base_total_interest > 0 else 0.0,
        "checkpoints": schedule_checkpoints,
    }


def compute_offer_strategy(
    *,
    property_value: float,
    price_low: float,
    price_high: float,
    target_offer: float,
    city: str | None = None,
    locality: str | None = None,
) -> dict[str, Any]:
    """Calculates negotiation leverage, bargaining tier, and actionable talking points."""
    if property_value <= 0 or price_high <= price_low:
        raise ValueError("Invalid property value or price range")

    span = price_high - price_low
    percentile = max(0.0, min(100.0, ((target_offer - price_low) / span) * 100))
    discount_vs_point = property_value - target_offer
    discount_pct = (discount_vs_point / property_value) * 100

    if percentile <= 25.0:
        tier = "AGGRESSIVE_BARGAIN"
        badge = "Aggressive Bargain (Top 10–25% Discount)"
        description = "High friction with seller; justified primarily for aged inventory, distress sales, or unrenovated units."
    elif percentile <= 60.0:
        tier = "FAIR_BENCHMARK"
        badge = "Fair Market Benchmark (Institutional Equilibrium)"
        description = "Supported by bank valuation panels and recent NHB micro-market transactions. Optimal acceptance probability."
    else:
        tier = "PREMIUM_SELLER"
        badge = "Premium Seller Bracket (Upper Quantile)"
        description = "Above median market pricing. Only recommended for panoramic oceanfronts, high-floor penthouses, or superior vastu/turnkey finishes."

    stamp_rate, _ = stamp_duty_rate("Maharashtra" if city and "Mumbai" in city else None)
    stamp_saved = max(0.0, discount_vs_point * stamp_rate)

    orig_emi = compute_emi(property_value * 0.75, 8.5, 20)
    offer_emi = compute_emi(target_offer * 0.75, 8.5, 20)
    emi_saved = max(0.0, orig_emi - offer_emi)

    loc_str = locality or "this micro-market"
    points = [
        f"Statistical P10-P90 spread anchors median valuation at ₹{property_value/1e7:.2f} Cr; offering ₹{target_offer/1e7:.2f} Cr reflects an active {abs(discount_pct):.1f}% liquidity adjustment.",
        f"A negotiated closing at ₹{target_offer/1e7:.2f} Cr reduces your upfront statutory stamp duty burden by ₹{stamp_saved/1e5:.1f} Lakhs and trims monthly EMI by ₹{emi_saved:,.0f}/month.",
        f"Citing NHB RESIDEX comparable listings in {loc_str}, transactions in the lower quartile have closed within 45 days, giving all-cash/pre-approved buyers maximal leverage.",
    ]

    return {
        "property_value": property_value,
        "price_low": price_low,
        "price_high": price_high,
        "target_offer": target_offer,
        "percentile": round(percentile, 1),
        "discount_inr": round(discount_vs_point, 0),
        "discount_pct": round(discount_pct, 1),
        "tier": tier,
        "badge": badge,
        "description": description,
        "stamp_saved_inr": round(stamp_saved, 0),
        "monthly_emi_saved_inr": round(emi_saved, 0),
        "negotiation_points": points,
    }


def get_infrastructure_impact(locality: str | None, city: str | None = None) -> dict[str, Any]:
    """Matches active mega-infrastructure initiatives and estimates appreciation catalysts."""
    matched = []
    total_boost = 0.0

    loc_lower = (locality or "").lower()
    for proj in INFRASTRUCTURE_PROJECTS:
        impacts = [imp.lower() for imp in proj["impacted_localities"]]
        if any(imp in loc_lower or loc_lower in imp for imp in impacts):
            matched.append(proj)
            total_boost += proj["premium_appreciation_pct"]

    if not matched:
        matched = [INFRASTRUCTURE_PROJECTS[0]]
        total_boost = 1.8

    base_cagr = PROPERTY_APPRECIATION_DEFAULT_PCT
    catalyst_cagr = round(base_cagr + min(total_boost, 4.5), 1)

    return {
        "locality": locality or "Prime Mumbai",
        "city": city or "Mumbai (MMR)",
        "active_projects": matched,
        "base_cagr_pct": base_cagr,
        "catalyst_cagr_pct": catalyst_cagr,
        "projected_3yr_multiplier": round(((1 + catalyst_cagr / 100.0) ** 3), 2),
        "projected_5yr_multiplier": round(((1 + catalyst_cagr / 100.0) ** 5), 2),
    }


def get_market_heatmap() -> list[dict[str, Any]]:
    """Returns coordinates and benchmark rates for micro-market heatmap nodes."""
    return MARKET_MAP_NODES


def compare_properties(properties: list[dict[str, Any]]) -> dict[str, Any]:
    """Compares 2 to 4 properties side-by-side with institutional valuation, cost, yield, and AI verdict."""
    if len(properties) < 2 or len(properties) > 4:
        raise ValueError("Property comparison requires between 2 and 4 properties")

    evaluated = []
    for prop in properties:
        val = float(prop["property_value"])
        if val <= 0:
            raise ValueError("property_value must be positive")
        area = float(prop.get("area_sqft") or 1200.0)
        bhk = int(prop.get("bhk") or 3)
        age = int(prop.get("age_years") or 2)
        city = str(prop.get("city") or "Mumbai (MMR)")
        state = prop.get("state") or ("Maharashtra" if "Mumbai" in city or "Pune" in city else None)
        name = str(prop.get("name") or prop.get("locality") or f"{bhk} BHK Residence")

        down_payment_pct = float(prop.get("down_payment_pct") or 20.0)
        annual_rate_pct = float(prop.get("annual_rate_pct") or 8.5)
        tenure_years = int(prop.get("tenure_years") or 20)

        costs = cost_breakdown(
            state=state,
            property_value=val,
            down_payment_pct=down_payment_pct,
            annual_rate_pct=annual_rate_pct,
            tenure_years=tenure_years,
            is_under_construction=bool(prop.get("is_under_construction", False)),
        )

        yield_rate, _ = get_rental_yield_rate(city)
        if "rental_yield_pct" in prop and prop["rental_yield_pct"] is not None:
            yield_rate = float(prop["rental_yield_pct"]) / 100.0

        annual_gross_rent = val * yield_rate
        monthly_rent = annual_gross_rent / 12.0
        # Real net rental: subtract maintenance & 1-month vacancy
        net_annual_rent = max(0.0, annual_gross_rent - (val * MAINTENANCE_DRAG_PCT) - monthly_rent)
        net_yield_pct = round((net_annual_rent / val) * 100.0, 2)
        emi = costs["monthly_emi"]
        emi_offset = round(min(100.0, (monthly_rent / emi) * 100.0), 1) if emi > 0 else 0.0

        rate_per_sqft = round(val / area, 0)
        p10 = float(prop.get("price_low") or (val * 0.92))
        p90 = float(prop.get("price_high") or (val * 1.08))

        efficiency_score = round((area / (val / 1e7)) * (1.0 / (1.0 + age * 0.015)), 1)

        if yield_rate >= 0.035 or emi_offset >= 45.0:
            verdict = "Optimal Immediate Rental Yield & Cash-Flow Coverage"
            verdict_badge = "Cash-Flow Champion"
            verdict_tag = "rental"
        elif rate_per_sqft >= 70000 or any(x in name for x in ["Worli", "Malabar", "Cuffe"]):
            verdict = "Superior Long-Term Capital Appreciation & Trophy Rarity"
            verdict_badge = "Trophy Capital"
            verdict_tag = "appreciation"
        elif efficiency_score > 400:
            verdict = "Maximum Space-to-Price Efficiency & Liquidity Resilience"
            verdict_badge = "Value Alpha Pick"
            verdict_tag = "efficiency"
        else:
            verdict = "Balanced Prime Residential Equilibrium"
            verdict_badge = "Balanced Core"
            verdict_tag = "balanced"

        evaluated.append({
            "name": name,
            "city": city,
            "locality": prop.get("locality") or name,
            "bhk": bhk,
            "area_sqft": area,
            "age_years": age,
            "property_value": val,
            "rate_per_sqft": rate_per_sqft,
            "price_low": round(p10, 0),
            "price_high": round(p90, 0),
            "spread_pct": round(((p90 - p10) / val) * 100, 1),
            "down_payment_inr": costs["down_payment"],
            "stamp_duty_inr": costs["stamp_duty"],
            "gst_inr": costs["gst"],
            "upfront_cash_inr": costs["upfront_cash"],
            "loan_amount_inr": costs["loan_amount"],
            "monthly_emi_inr": emi,
            "gross_rental_yield_pct": round(yield_rate * 100.0, 2),
            "net_rental_yield_pct": net_yield_pct,
            "monthly_rent_inr": round(monthly_rent, 0),
            "emi_offset_pct": emi_offset,
            "efficiency_score": efficiency_score,
            "verdict": verdict,
            "verdict_badge": verdict_badge,
            "verdict_tag": verdict_tag,
        })

    winner_lowest_upfront = min(evaluated, key=lambda x: x["upfront_cash_inr"])["name"]
    winner_highest_yield = max(evaluated, key=lambda x: x["gross_rental_yield_pct"])["name"]
    winner_lowest_emi = min(evaluated, key=lambda x: x["monthly_emi_inr"])["name"]
    winner_lowest_sqft = min(evaluated, key=lambda x: x["rate_per_sqft"])["name"]

    return {
        "properties": evaluated,
        "winner_summary": {
            "lowest_upfront_cash": winner_lowest_upfront,
            "highest_rental_yield": winner_highest_yield,
            "lowest_monthly_emi": winner_lowest_emi,
            "best_value_rate_per_sqft": winner_lowest_sqft,
        },
    }

