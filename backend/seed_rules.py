"""Idempotent seeder for versioned, effective-dated financial rules in GrihaValue.

Seeds primary source verified constants:
- RBI Housing Finance Master Direction (LTV caps)
- GST Council Notifications (Under construction, affordable, and CC exempt rates)
- State stamp duty schedules (marked with APPROXIMATE status until primary gazette check)
- Benchmark lending rates
"""

from __future__ import annotations

import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine, Base
from backend.rule_models import (
    BenchmarkRateRule,
    GSTRule,
    LTVRule,
    StampDutyRule,
)

LTV_SEED_DATA = [
    {
        "tier_name": "Tier 1: Loans up to Rs 30 Lakh",
        "max_loan_inr": 3_000_000.0,
        "ltv_ratio": 0.90,
        "citation_ref": "RBI/2015-16/203 DBR.BP.BC.No.44/08.12.015/2015-16",
        "source_title": "RBI Master Direction - Housing Finance, Annex I (LTV ratios)",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx?id=12513",
        "effective_from": datetime.date(2015, 10, 8),
        "effective_to": None,
        "verified_by": "Reserve Bank of India Master Circular",
        "verification_status": "VERIFIED",
    },
    {
        "tier_name": "Tier 2: Loans Rs 30 Lakh to Rs 75 Lakh",
        "max_loan_inr": 7_500_000.0,
        "ltv_ratio": 0.80,
        "citation_ref": "RBI/2015-16/203 DBR.BP.BC.No.44/08.12.015/2015-16",
        "source_title": "RBI Master Direction - Housing Finance, Annex I (LTV ratios)",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx?id=12513",
        "effective_from": datetime.date(2015, 10, 8),
        "effective_to": None,
        "verified_by": "Reserve Bank of India Master Circular",
        "verification_status": "VERIFIED",
    },
    {
        "tier_name": "Tier 3: Loans above Rs 75 Lakh",
        "max_loan_inr": 1e15,  # effectively unbounded
        "ltv_ratio": 0.75,
        "citation_ref": "RBI/2015-16/203 DBR.BP.BC.No.44/08.12.015/2015-16",
        "source_title": "RBI Master Direction - Housing Finance, Annex I (LTV ratios)",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx?id=12513",
        "effective_from": datetime.date(2015, 10, 8),
        "effective_to": None,
        "verified_by": "Reserve Bank of India Master Circular",
        "verification_status": "VERIFIED",
    },
]

GST_SEED_DATA = [
    {
        "construction_status": "Under Construction",
        "is_affordable": False,
        "affordable_threshold_inr": 4_500_000.0,
        "rate_pct": 0.05,
        "notification_ref": "Notification No. 03/2019-Central Tax (Rate)",
        "source_title": "GST Council 34th Meeting Decisions on Real Estate Sector",
        "source_url": "https://cbic-gst.gov.in/pdf/central-tax-rate/notf-03-2019-cgst-rate.pdf",
        "effective_from": datetime.date(2019, 4, 1),
        "effective_to": None,
        "verified_by": "CBIC / GST Council Gazette",
        "verification_status": "VERIFIED",
    },
    {
        "construction_status": "Under Construction",
        "is_affordable": True,
        "affordable_threshold_inr": 4_500_000.0,
        "rate_pct": 0.01,
        "notification_ref": "Notification No. 03/2019-Central Tax (Rate)",
        "source_title": "GST Council Affordable Housing Concession (value <= 45 Lakhs)",
        "source_url": "https://cbic-gst.gov.in/pdf/central-tax-rate/notf-03-2019-cgst-rate.pdf",
        "effective_from": datetime.date(2019, 4, 1),
        "effective_to": None,
        "verified_by": "CBIC / GST Council Gazette",
        "verification_status": "VERIFIED",
    },
    {
        "construction_status": "Ready to Move",
        "is_affordable": False,
        "affordable_threshold_inr": 0.0,
        "rate_pct": 0.0,
        "notification_ref": "CGST Act 2017, Schedule III, Clause 5",
        "source_title": "Sale of land and sale of building post completion certificate exempt from GST",
        "source_url": "https://cbic-gst.gov.in/act.html",
        "effective_from": datetime.date(2017, 7, 1),
        "effective_to": None,
        "verified_by": "CGST Act 2017 Schedule III",
        "verification_status": "VERIFIED",
    },
]

STAMP_DUTY_SEED_DATA = [
    ("Karnataka", 0.065, "Karnataka Stamp Act 1957 (Indicative male buyer total including cess)"),
    ("Maharashtra", 0.060, "Maharashtra Stamp Act 1958 Schedule I (Indicative 5% + 1% cess)"),
    ("Delhi", 0.060, "Delhi Stamp Act Schedule 1A"),
    ("Haryana", 0.080, "Haryana Stamp Act Schedule (Urban areas)"),
    ("Uttar Pradesh", 0.080, "UP Stamp Act Schedule 1B"),
    ("Telangana", 0.075, "Telangana Registration & Stamp Schedule"),
    ("Tamil Nadu", 0.070, "Tamil Nadu Stamp Act Schedule"),
    ("West Bengal", 0.060, "West Bengal Stamp Act Schedule"),
    ("Gujarat", 0.059, "Gujarat Stamp Act Schedule (4.9% duty + 1% registration)"),
    ("Rajasthan", 0.060, "Rajasthan Stamp Law Schedule"),
    ("Chandigarh", 0.060, "Chandigarh Stamp Schedule"),
    ("Punjab", 0.080, "Punjab Stamp Act Schedule"),
    ("Madhya Pradesh", 0.075, "MP Stamp Act Schedule"),
    ("Kerala", 0.080, "Kerala Stamp Act Schedule"),
    ("Andhra Pradesh", 0.065, "AP Registration & Stamp Schedule"),
    ("Odisha", 0.060, "Odisha Stamp Schedule"),
    ("Bihar", 0.080, "Bihar Stamp Act Schedule"),
    ("Assam", 0.080, "Assam Stamp Act Schedule"),
    ("DEFAULT", 0.065, "National planning default for unmapped states"),
]

BENCHMARK_RATES_SEED_DATA = [
    ("interest_rate_default_pct", 8.5, "percentage", "Bank Floating Rate Median", "Indicative major bank retail housing loan floating rate index"),
    ("interest_rate_min_pct", 6.5, "percentage", "Subsidized / Floor Lending Rate", "Lowest concessional home loan benchmark"),
    ("interest_rate_max_pct", 14.0, "percentage", "Ceiling Non-Prime Lending Rate", "Upper ceiling for retail housing loans"),
    ("tenure_default_yrs", 20.0, "years", "Typical Home Loan Term", "Standard industry loan amortization horizon"),
    ("tenure_min_yrs", 5.0, "years", "Minimum Loan Term", "Shortest standard tenure"),
    ("tenure_max_yrs", 30.0, "years", "Maximum Loan Term", "Maximum permissible home loan tenure"),
]


def seed_all_rules(session: Session) -> dict[str, int]:
    """Idempotently seed all financial rules into the database."""
    Base.metadata.create_all(bind=session.bind)

    counts = {"ltv": 0, "gst": 0, "stamp_duty": 0, "benchmark_rates": 0}

    # 1. Seed LTV Rules
    for item in LTV_SEED_DATA:
        exists = session.scalar(
            select(LTVRule).where(
                LTVRule.tier_name == item["tier_name"],
                LTVRule.effective_from == item["effective_from"],
            )
        )
        if not exists:
            session.add(LTVRule(**item))
            counts["ltv"] += 1

    # 2. Seed GST Rules
    for item in GST_SEED_DATA:
        exists = session.scalar(
            select(GSTRule).where(
                GSTRule.construction_status == item["construction_status"],
                GSTRule.is_affordable == item["is_affordable"],
                GSTRule.effective_from == item["effective_from"],
            )
        )
        if not exists:
            session.add(GSTRule(**item))
            counts["gst"] += 1

    # 3. Seed Stamp Duty Rules
    for state, rate, note in STAMP_DUTY_SEED_DATA:
        exists = session.scalar(
            select(StampDutyRule).where(
                StampDutyRule.state == state,
                StampDutyRule.buyer_category == "General",
                StampDutyRule.effective_from == datetime.date(2020, 1, 1),
            )
        )
        if not exists:
            session.add(
                StampDutyRule(
                    state=state,
                    buyer_category="General",
                    rate_pct=rate,
                    gazette_ref=note,
                    source_title=f"State Stamp Schedule ({state})",
                    source_url="https://igod.gov.in/",
                    effective_from=datetime.date(2020, 1, 1),
                    effective_to=None,
                    verified_by="State Registration Dept Schedule Compilation",
                    verification_status="APPROXIMATE",
                )
            )
            counts["stamp_duty"] += 1

    # 4. Seed Benchmark Rates
    for key, val, unit, title, note in BENCHMARK_RATES_SEED_DATA:
        exists = session.scalar(
            select(BenchmarkRateRule).where(
                BenchmarkRateRule.rate_key == key,
                BenchmarkRateRule.effective_from == datetime.date(2024, 1, 1),
            )
        )
        if not exists:
            session.add(
                BenchmarkRateRule(
                    rate_key=key,
                    rate_value=val,
                    unit=unit,
                    citation_ref=note,
                    source_title=title,
                    source_url="https://www.rbi.org.in/",
                    effective_from=datetime.date(2024, 1, 1),
                    effective_to=None,
                    verified_by="Aggregated Retail Lending Schedule",
                    verification_status="UNVERIFIED",
                )
            )
            counts["benchmark_rates"] += 1

    session.commit()
    return counts


if __name__ == "__main__":
    with SessionLocal() as db_session:
        res = seed_all_rules(db_session)
        print(f"Rules seeded successfully: {res}")
