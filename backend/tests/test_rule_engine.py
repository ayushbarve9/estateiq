"""Unit tests for the Versioned Database Rule Engine and Provenance Tracking.

Tests effective-dating, point-in-time rule resolution, and reproducible valuations.
"""

import datetime
from sqlalchemy import select
import pytest

from backend.database import SessionLocal
from backend.finance import cost_breakdown, get_ltv, stamp_duty_rate, compute_gst
from backend.rule_engine import (
    build_applied_rules_snapshot,
    resolve_benchmark_rates,
    resolve_gst_rate,
    resolve_ltv_tiers,
    resolve_stamp_duty,
)
from backend.rule_models import (
    BenchmarkRateRule,
    GSTRule,
    LTVRule,
    StampDutyRule,
    ValuationHistory,
)
from backend.seed_rules import seed_all_rules


@pytest.fixture(autouse=True)
def ensure_rules_seeded():
    """Ensure database has seeded rules before running tests."""
    with SessionLocal() as session:
        seed_all_rules(session)


def test_versioned_tables_seeded_with_provenance():
    with SessionLocal() as session:
        ltv_rules = list(session.scalars(select(LTVRule)).all())
        assert len(ltv_rules) >= 3
        for r in ltv_rules:
            assert r.citation_ref, f"LTV rule {r.tier_name} missing citation_ref"
            assert r.source_url.startswith("http"), f"LTV rule {r.tier_name} invalid source_url"
            assert r.verification_status == "VERIFIED"
            assert r.effective_from <= datetime.date(2020, 1, 1)

        gst_rules = list(session.scalars(select(GSTRule)).all())
        assert len(gst_rules) >= 3
        for r in gst_rules:
            assert r.notification_ref, f"GST rule missing notification_ref"
            assert r.verification_status == "VERIFIED"

        stamp_rules = list(session.scalars(select(StampDutyRule)).all())
        assert len(stamp_rules) >= 18
        states = {r.state for r in stamp_rules}
        assert "Karnataka" in states
        assert "Maharashtra" in states
        assert "Delhi" in states

        benchmarks = list(session.scalars(select(BenchmarkRateRule)).all())
        assert len(benchmarks) >= 6


def test_effective_dating_ltv_resolution():
    """Current date should resolve 3 tiers (0.90, 0.80, 0.75)."""
    current_tiers = resolve_ltv_tiers(valuation_date=datetime.date(2026, 1, 1))
    assert len(current_tiers) >= 3
    ratios = [t["ltv_ratio"] for t in current_tiers]
    assert ratios == [0.90, 0.80, 0.75]
    assert current_tiers[0]["citation_ref"].startswith("RBI/2015-16/203")


def test_effective_dating_point_in_time_historical_superseding():
    """Adding an older historical rule should resolve correctly based on the valuation date."""
    with SessionLocal() as session:
        # Add a historical rule active only between 2010 and 2014
        historical_rule = StampDutyRule(
            state="TestState",
            buyer_category="General",
            rate_pct=0.040,  # 4%
            gazette_ref="Historical Gazette 2010",
            source_title="State Gazette 2010",
            source_url="https://igod.gov.in/test",
            effective_from=datetime.date(2010, 1, 1),
            effective_to=datetime.date(2014, 12, 31),
            verified_by="Historical Gazette",
            verification_status="VERIFIED",
        )
        # Add modern rule active from 2015 onwards
        modern_rule = StampDutyRule(
            state="TestState",
            buyer_category="General",
            rate_pct=0.070,  # 7%
            gazette_ref="Modern Gazette 2015",
            source_title="State Gazette 2015",
            source_url="https://igod.gov.in/test",
            effective_from=datetime.date(2015, 1, 1),
            effective_to=None,
            verified_by="Modern Gazette",
            verification_status="VERIFIED",
        )
        session.add(historical_rule)
        session.add(modern_rule)
        session.commit()

        # Query on 2012 date -> should resolve 4%
        r_hist = resolve_stamp_duty("TestState", session=session, valuation_date=datetime.date(2012, 6, 1))
        assert r_hist["rate"] == 0.040
        assert r_hist["citation_ref"] == "Historical Gazette 2010"

        # Query on 2026 date -> should resolve 7%
        r_mod = resolve_stamp_duty("TestState", session=session, valuation_date=datetime.date(2026, 1, 1))
        assert r_mod["rate"] == 0.070
        assert r_mod["citation_ref"] == "Modern Gazette 2015"


def test_gst_rule_resolution():
    # Ready to move has 0% GST
    r_rtm = resolve_gst_rate("Ready to Move", 10_000_000)
    assert r_rtm["rate"] == 0.0
    assert "Schedule III" in r_rtm["citation_ref"]

    # Under construction affordable (<= 45 Lakhs) has 1% GST
    r_aff = resolve_gst_rate("Under Construction", 4_000_000)
    assert r_aff["rate"] == 0.01

    # Under construction non-affordable (> 45 Lakhs) has 5% GST
    r_std = resolve_gst_rate("Under Construction", 10_000_000)
    assert r_std["rate"] == 0.05


def test_applied_rules_snapshot_reproducibility():
    """Verify that cost_breakdown produces an applied_rules_snapshot containing all rule IDs."""
    cb = cost_breakdown(
        state="Karnataka",
        property_value=12_000_000,
        down_payment_pct=20,
        annual_rate_pct=8.5,
        tenure_years=20,
        is_under_construction=True,
        valuation_date=datetime.date(2026, 10, 13),
    )
    assert "applied_rules_snapshot" in cb
    snap = cb["applied_rules_snapshot"]
    assert snap["state"] == "Karnataka"
    assert snap["stamp_duty_rule"]["rate"] == 0.065
    assert snap["gst_rule"]["rate"] == 0.05
    assert len(snap["ltv_rules"]) >= 3
    assert snap["valuation_date"] == "2026-10-13"


def test_rules_api_endpoint():
    """Verify that /api/rules endpoint returns all active rules and citations."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["total_rules"] >= 30
    assert len(data["ltv_rules"]) >= 3
    assert len(data["stamp_duty_rules"]) >= 18
    assert len(data["gst_rules"]) >= 3
    assert len(data["benchmark_rates"]) >= 6


def test_estimate_generates_valuation_record_and_certificate():
    """Verify /api/estimate generates persistent valuation record and certified certificate HTML."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    req = {
        "city": "Mumbai (MMR)",
        "locality": "Worli / South Mumbai",
        "bhk": 3,
        "area_sqft": 1800.0,
        "bathrooms": 3,
        "property_type": "Apartment",
        "furnishing": "Semi-Furnished",
        "construction_status": "Ready to Move",
        "age_years": 2,
        "parking": 2,
        "down_payment_pct": 20.0,
        "annual_rate_pct": 8.5,
        "tenure_years": 20,
    }
    resp = client.post("/api/estimate", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valuation_ref"] is not None
    assert "applied_rules_snapshot" in data["finance"]
    assert data["finance"]["applied_rules_snapshot"]["state"] == "Maharashtra"
    assert data["finance"]["applied_rules_snapshot"]["stamp_duty_rule"]["rate"] == 0.06

    # Test certificate endpoint
    cert_resp = client.get(f"/api/valuation/{data['valuation_ref']}/certificate")
    assert cert_resp.status_code == 200
    html = cert_resp.text
    assert "EstateIQ Official Residential Valuation Dossier" in html
    assert data["valuation_ref"] in html
    assert "Maharashtra Stamp Act" in html
    assert "PROVENANCE VERIFIED" in html
    assert "/js/cert.js" in html

