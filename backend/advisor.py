"""Grounded chat advisor. The model's figures are the only facts it may use."""

from __future__ import annotations

from typing import Any

from backend.config import INTEREST_RATE_DEFAULT_PCT


def inr(v: float) -> str:
    """Indian number format: Crore and Lakh."""
    v = float(v or 0)
    if abs(v) >= 10_000_000:
        return f"Rs {v / 10_000_000:.2f} Cr"
    if abs(v) >= 100_000:
        return f"Rs {v / 100_000:.2f} L"
    return f"Rs {v:,.0f}"


REQUIRED_CONTEXT_KEYS = ("predicted_price", "rate_per_sqft", "finance", "city", "locality", "bhk")


def validate_context(ctx: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_CONTEXT_KEYS if k not in ctx]
    if missing:
        raise ValueError(f"estimate_context is missing {missing}")
    if "finance" in ctx and not isinstance(ctx["finance"], dict):
        raise ValueError("estimate_context.finance must be an object")


from backend.macro_news import get_news_summary_for_advisor


def build_system_prompt(ctx: dict[str, Any]) -> str:
    fin = ctx.get("finance", {})
    city = ctx.get("city", "Mumbai (MMR)")
    locality = ctx.get("locality", "")
    rules_snap = fin.get("applied_rules_snapshot", {})
    stamp_rule = rules_snap.get("stamp_duty_rule", {})
    gst_rule = rules_snap.get("gst_rule", {})
    ltv_rules = rules_snap.get("ltv_rules", [])

    stamp_cit = stamp_rule.get("citation_ref", "State Stamp Act Schedule")
    gst_cit = gst_rule.get("citation_ref", "CBIC Real Estate GST Notification")
    ltv_cit = ltv_rules[0].get("citation_ref") if ltv_rules else "RBI Master Direction - Housing Finance"

    news_context = get_news_summary_for_advisor(city, locality)

    return f"""You are EstateIQ's Senior Real Estate Advisory Concierge for Indian prime residential acquisitions.

PROPERTY VALUATION CONTEXT:
- Location: {ctx.get('bhk')} BHK in {locality}, {city}
- Fair Market Valuation: {inr(ctx.get('predicted_price', 0))}
- Rate per sq.ft.: Rs {float(ctx.get('rate_per_sqft', 0)):,.0f} / sq.ft.
- Statistical Price Range (P10–P90): {inr(ctx.get('price_range', {}).get('low', 0))} to {inr(ctx.get('price_range', {}).get('high', 0))}
- Loan Amount: {inr(fin.get('loan_amount', 0))} ({int(fin.get('ltv_ratio', 0.75) * 100)}% LTV Cap)
- Down Payment: {inr(fin.get('down_payment', 0))}
- Monthly EMI: {inr(fin.get('monthly_emi', 0))} / month
- Stamp Duty & Registration: {inr(fin.get('stamp_duty', 0))} (Statutory Citation: {stamp_cit})
- GST (Construction): {inr(fin.get('gst', 0))} (Notification: {gst_cit})
- Total Upfront Cash Required: {inr(fin.get('upfront_cash', 0))}
- Total Acquisition Cost: {inr(fin.get('total_acquisition_cost', 0))}
- Banking LTV Ceiling: {ltv_cit}

RECENT REAL ESTATE NEWS & MACROECONOMIC MOVEMENTS (NHB RESIDEX & REGULATORY ARCHIVES):
{news_context}

ADVISORY INSTRUCTIONS:
1. Ground your answers in the exact valuation numbers and verified macro real estate news above.
2. When asked about price drivers, future appreciation, or why a micro-market is priced as it is, correlate the figures with relevant infrastructure developments (e.g. Coastal Road, Metro Line 3, airport access) and historical market movements (RERA compliance, repo rate shifts).
3. Explain financial terms (EMI, LTV cap, stamp duty, upfront cash) clearly and plainly using Indian Lakh and Crore notation.
4. Maintain a sophisticated, institutional, yet accessible advisor persona.
5. If the user asks whether you are an AI, confirm honestly that you are EstateIQ's AI Property Advisory Concierge.
6. Give no guarantees on future speculative gains; refer clients to registered property advocates and bankers for transaction execution."""

