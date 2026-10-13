"""Point-in-time Rule Resolution Engine.

Resolves versioned, effective-dated financial rules in force on the valuation date:
- RBI LTV cap tiers
- State stamp duty and registration rates
- GST on under-construction vs ready properties
- Home loan floating rates and tenure bounds

Produces an auditable snapshot of rule IDs and legal citations for every valuation.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.config import (
    INTEREST_RATE_DEFAULT_PCT,
    INTEREST_RATE_MAX_PCT,
    INTEREST_RATE_MIN_PCT,
    LTV_TIERS,
    STAMP_DUTY_BY_STATE,
    STAMP_DUTY_DEFAULT,
    TENURE_DEFAULT_YRS,
    TENURE_MAX_YRS,
    TENURE_MIN_YRS,
)
from backend.database import SessionLocal
from backend.rule_models import (
    BenchmarkRateRule,
    GSTRule,
    LTVRule,
    StampDutyRule,
)


def get_valuation_date(val_date: Optional[datetime.date | str] = None) -> datetime.date:
    """Normalize input date to datetime.date object; defaults to UTC today."""
    if val_date is None:
        return datetime.datetime.now(datetime.timezone.utc).date()
    if isinstance(val_date, str):
        return datetime.date.fromisoformat(val_date.split("T")[0])
    return val_date


def resolve_ltv_tiers(
    session: Optional[Session] = None,
    valuation_date: Optional[datetime.date | str] = None,
) -> list[dict[str, Any]]:
    """Resolve active LTV tiers for a given date.
    
    Returns list of dicts ordered by max_loan_inr ascending:
    [{"id": ..., "max_loan_inr": ..., "ltv_ratio": ..., "citation": ..., "source_url": ...}]
    """
    vdate = get_valuation_date(valuation_date)
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        stmt = (
            select(LTVRule)
            .where(
                and_(
                    LTVRule.effective_from <= vdate,
                    or_(LTVRule.effective_to.is_(None), LTVRule.effective_to > vdate),
                )
            )
            .order_by(LTVRule.max_loan_inr.asc())
        )
        rules = list(session.scalars(stmt).all())
        if rules:
            return [
                {
                    "rule_id": r.id,
                    "tier_name": r.tier_name,
                    "max_loan_inr": r.max_loan_inr,
                    "ltv_ratio": r.ltv_ratio,
                    "citation_ref": r.citation_ref,
                    "source_url": r.source_url,
                    "verification_status": r.verification_status,
                }
                for r in rules
            ]
        # Fallback to config constants if database table not yet populated
        return [
            {
                "rule_id": None,
                "tier_name": f"Tier (up to {t[0]})",
                "max_loan_inr": t[0],
                "ltv_ratio": t[1],
                "citation_ref": "RBI Master Direction - Housing Finance, Annex I",
                "source_url": "https://www.rbi.org.in/",
                "verification_status": "VERIFIED",
            }
            for t in LTV_TIERS
        ]
    finally:
        if close_session:
            session.close()


def resolve_stamp_duty(
    state: str,
    buyer_category: str = "General",
    session: Optional[Session] = None,
    valuation_date: Optional[datetime.date | str] = None,
) -> dict[str, Any]:
    """Resolve stamp duty and registration rate for a state on the given date."""
    vdate = get_valuation_date(valuation_date)
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        stmt = (
            select(StampDutyRule)
            .where(
                and_(
                    StampDutyRule.state == state,
                    StampDutyRule.buyer_category == buyer_category,
                    StampDutyRule.effective_from <= vdate,
                    or_(StampDutyRule.effective_to.is_(None), StampDutyRule.effective_to > vdate),
                )
            )
            .order_by(StampDutyRule.effective_from.desc())
        )
        rule = session.scalars(stmt).first()

        is_fallback = False
        # Fallback to DEFAULT state rule if specific state not found
        if not rule:
            is_fallback = True
            stmt_default = select(StampDutyRule).where(
                and_(
                    StampDutyRule.state == "DEFAULT",
                    StampDutyRule.buyer_category == buyer_category,
                    StampDutyRule.effective_from <= vdate,
                    or_(StampDutyRule.effective_to.is_(None), StampDutyRule.effective_to > vdate),
                )
            )
            rule = session.scalars(stmt_default).first()

        if rule:
            return {
                "rule_id": rule.id,
                "state": state if is_fallback else rule.state,
                "rate": rule.rate_pct,
                "citation_ref": rule.gazette_ref,
                "source_url": rule.source_url,
                "verification_status": "FALLBACK" if is_fallback else rule.verification_status,
            }

        # Fallback to config constants
        rate = STAMP_DUTY_BY_STATE.get(state, STAMP_DUTY_DEFAULT)
        return {
            "rule_id": None,
            "state": state,
            "rate": rate,
            "citation_ref": "State Stamp Act Schedule (approximate compilation)",
            "source_url": "https://igod.gov.in/",
            "verification_status": "APPROXIMATE",
        }
    finally:
        if close_session:
            session.close()


def resolve_gst_rate(
    construction_status: str,
    property_value: float,
    session: Optional[Session] = None,
    valuation_date: Optional[datetime.date | str] = None,
) -> dict[str, Any]:
    """Resolve GST rate on property for a given date."""
    vdate = get_valuation_date(valuation_date)
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    is_under_construction = construction_status == "Under Construction"

    try:
        if not is_under_construction:
            stmt = select(GSTRule).where(
                and_(
                    GSTRule.construction_status == "Ready to Move",
                    GSTRule.effective_from <= vdate,
                    or_(GSTRule.effective_to.is_(None), GSTRule.effective_to > vdate),
                )
            )
            rule = session.scalars(stmt).first()
            if rule:
                return {
                    "rule_id": rule.id,
                    "rate": rule.rate_pct,
                    "citation_ref": rule.notification_ref,
                    "source_url": rule.source_url,
                    "verification_status": rule.verification_status,
                }
            return {
                "rule_id": None,
                "rate": 0.0,
                "citation_ref": "CGST Act 2017 Schedule III Clause 5",
                "source_url": "https://cbic-gst.gov.in/",
                "verification_status": "VERIFIED",
            }

        # Under construction: check if affordable
        # Affordable if value <= threshold
        stmt = (
            select(GSTRule)
            .where(
                and_(
                    GSTRule.construction_status == "Under Construction",
                    GSTRule.effective_from <= vdate,
                    or_(GSTRule.effective_to.is_(None), GSTRule.effective_to > vdate),
                )
            )
            .order_by(GSTRule.rate_pct.asc())
        )
        rules = list(session.scalars(stmt).all())
        affordable_rule = next((r for r in rules if r.is_affordable), None)
        standard_rule = next((r for r in rules if not r.is_affordable), None)

        threshold = affordable_rule.affordable_threshold_inr if affordable_rule else 4_500_000.0
        if property_value <= threshold and affordable_rule:
            return {
                "rule_id": affordable_rule.id,
                "rate": affordable_rule.rate_pct,
                "citation_ref": affordable_rule.notification_ref,
                "source_url": affordable_rule.source_url,
                "verification_status": affordable_rule.verification_status,
            }
        elif standard_rule:
            return {
                "rule_id": standard_rule.id,
                "rate": standard_rule.rate_pct,
                "citation_ref": standard_rule.notification_ref,
                "source_url": standard_rule.source_url,
                "verification_status": standard_rule.verification_status,
            }

        rate = 0.01 if property_value <= 4_500_000.0 else 0.05
        return {
            "rule_id": None,
            "rate": rate,
            "citation_ref": "Notification No. 03/2019-Central Tax (Rate)",
            "source_url": "https://cbic-gst.gov.in/",
            "verification_status": "VERIFIED",
        }
    finally:
        if close_session:
            session.close()


def resolve_benchmark_rates(
    session: Optional[Session] = None,
    valuation_date: Optional[datetime.date | str] = None,
) -> dict[str, Any]:
    """Resolve interest rate and loan tenure defaults and bounds."""
    vdate = get_valuation_date(valuation_date)
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        stmt = select(BenchmarkRateRule).where(
            and_(
                BenchmarkRateRule.effective_from <= vdate,
                or_(BenchmarkRateRule.effective_to.is_(None), BenchmarkRateRule.effective_to > vdate),
            )
        )
        rules = {r.rate_key: r for r in session.scalars(stmt).all()}

        return {
            "interest_rate_default_pct": rules["interest_rate_default_pct"].rate_value if "interest_rate_default_pct" in rules else INTEREST_RATE_DEFAULT_PCT,
            "interest_rate_min_pct": rules["interest_rate_min_pct"].rate_value if "interest_rate_min_pct" in rules else INTEREST_RATE_MIN_PCT,
            "interest_rate_max_pct": rules["interest_rate_max_pct"].rate_value if "interest_rate_max_pct" in rules else INTEREST_RATE_MAX_PCT,
            "tenure_default_yrs": int(rules["tenure_default_yrs"].rate_value) if "tenure_default_yrs" in rules else TENURE_DEFAULT_YRS,
            "tenure_min_yrs": int(rules["tenure_min_yrs"].rate_value) if "tenure_min_yrs" in rules else TENURE_MIN_YRS,
            "tenure_max_yrs": int(rules["tenure_max_yrs"].rate_value) if "tenure_max_yrs" in rules else TENURE_MAX_YRS,
            "rules_applied": {k: {"rule_id": r.id, "citation": r.citation_ref} for k, r in rules.items()},
        }
    finally:
        if close_session:
            session.close()


def build_applied_rules_snapshot(
    state: str,
    construction_status: str,
    property_value: float,
    valuation_date: Optional[datetime.date | str] = None,
    session: Optional[Session] = None,
) -> dict[str, Any]:
    """Generate a complete, reproducible snapshot of all rules active for this valuation."""
    vdate = get_valuation_date(valuation_date)
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        ltv_rules = resolve_ltv_tiers(session=session, valuation_date=vdate)
        stamp_rule = resolve_stamp_duty(state=state, session=session, valuation_date=vdate)
        gst_rule = resolve_gst_rate(construction_status=construction_status, property_value=property_value, session=session, valuation_date=vdate)
        benchmarks = resolve_benchmark_rates(session=session, valuation_date=vdate)

        return {
            "valuation_date": vdate.isoformat(),
            "state": state,
            "construction_status": construction_status,
            "property_value_inr": property_value,
            "ltv_rules": ltv_rules,
            "stamp_duty_rule": stamp_rule,
            "gst_rule": gst_rule,
            "benchmark_rates": benchmarks,
        }
    finally:
        if close_session:
            session.close()
