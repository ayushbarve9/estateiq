"""API contract tests. Uses the trained bundle at models/grihavalue.joblib."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

VALID = {
    "city": "Bengaluru",
    "locality": "Whitefield",
    "bhk": 3,
    "area_sqft": 1500.0,
    "bathrooms": 3,
    "property_type": "Apartment",
    "furnishing": "Semi-Furnished",
    "construction_status": "Ready to Move",
    "age_years": 2,
    "parking": 1,
    "down_payment_pct": 20.0,
    "annual_rate_pct": 8.5,
    "tenure_years": 20,
}


def test_health_reports_loaded_model():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model"]["loaded"] is True
    assert body["model"]["data"]["kind"] in ("synthetic", "csv")


def test_meta_contract():
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert len(body["cities"]) >= 20
    for c in body["cities"]:
        assert c["localities"], f"{c['name']} has no localities"
    assert set(body["property_types"]) >= {"Apartment", "Penthouse"}
    assert body["bounds"]["rate_pct"]["min"] < body["bounds"]["rate_pct"]["default"] < body["bounds"]["rate_pct"]["max"]
    assert "metrics" in body["model"]
    assert isinstance(body["chat_enabled"], bool)


def test_estimate_happy_path_shape():
    r = client.post("/api/estimate", json=VALID)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["predicted_price"] > 0
    assert body["rate_per_sqft"] * VALID["area_sqft"] == pytest.approx(body["predicted_price"], rel=1e-9)
    low, high = body["price_range"]["low"], body["price_range"]["high"]
    assert low <= body["predicted_price"] <= high
    assert body["state"] == "Karnataka"
    assert body["finance"]["gst"] == 0.0  # ready to move
    assert body["finance"]["monthly_emi"] > 0
    assert body["comparables_kind"] in ("synthetic", "csv")


def test_estimate_under_construction_adds_gst():
    payload = dict(VALID, construction_status="Under Construction", age_years=0)
    body = client.post("/api/estimate", json=payload).json()
    assert body["finance"]["gst"] > 0


def test_estimate_penthouse_one_bhk_rejected():
    payload = dict(VALID, bhk=1, area_sqft=600, bathrooms=1, property_type="Penthouse")
    r = client.post("/api/estimate", json=payload)
    assert r.status_code == 422


def test_estimate_unknown_city_is_400():
    r = client.post("/api/estimate", json=dict(VALID, city="Atlantis", locality="Nowhere"))
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "invalid_input"


def test_estimate_locality_from_other_city_is_400():
    r = client.post("/api/estimate", json=dict(VALID, locality="Bandra West"))
    assert r.status_code == 400


def test_estimate_area_too_small_is_422():
    r = client.post("/api/estimate", json=dict(VALID, bhk=4, area_sqft=500))
    assert r.status_code == 422


def test_estimate_rejects_unknown_fields():
    r = client.post("/api/estimate", json=dict(VALID, injected="x"))
    assert r.status_code == 422


def test_estimate_rate_out_of_bounds_is_422():
    r = client.post("/api/estimate", json=dict(VALID, annual_rate_pct=40))
    assert r.status_code == 422


def test_comparables_match_locality_when_available():
    body = client.post("/api/estimate", json=VALID).json()
    assert 1 <= len(body["comparables"]) <= 3
    for c in body["comparables"]:
        assert c["City"] == "Bengaluru"


def test_sensitivity_matches_estimate_emi_when_cap_not_binding():
    est = client.post("/api/estimate", json=VALID).json()
    grid = client.post("/api/finance/sensitivity", json={
        "property_value": est["predicted_price"],
        "down_payment_pct": VALID["down_payment_pct"],
        "rates_pct": [VALID["annual_rate_pct"]],
        "tenures_years": [VALID["tenure_years"]],
    }).json()
    emi_grid = grid["grid"][0]["emis"][0]["monthly_emi"]
    assert emi_grid == pytest.approx(est["finance"]["monthly_emi"], rel=1e-9)


def test_sensitivity_rejects_out_of_range_rate():
    r = client.post("/api/finance/sensitivity", json={
        "property_value": 1e7, "rates_pct": [50], "tenures_years": [20]})
    assert r.status_code == 422


def test_market_overview_covers_all_cities():
    r = client.get("/api/market-overview")
    assert r.status_code == 200
    body = r.json()
    names = {c["city"] for c in body["cities"]}
    assert len(names) == len(client.get("/api/meta").json()["cities"])
    assert all(c["median_psf"] > 0 for c in body["cities"])


def test_chat_without_key_returns_503(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    r = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "estimate_context": {"predicted_price": 1, "rate_per_sqft": 1, "finance": {},
                             "city": "x", "locality": "y", "bhk": 2},
    })
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "chat_unconfigured"


def test_chat_rejects_incomplete_context(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    r = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "estimate_context": {"city": "x"},
    })
    assert r.status_code == 400


def test_security_headers_present():
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert "script-src 'self'" in r.headers["Content-Security-Policy"]


def test_frontend_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "EstateIQ" in r.text
    assert "GrihaValue" in r.text


def test_contact_happy_path_and_report_metadata():
    est = client.post("/api/estimate", json=VALID).json()
    payload = {
        "name": "Aditya Singhania",
        "email": "aditya@singhania.in",
        "phone": "+91 98200 12345",
        "advisory_type": "Full Acquisition Report & Valuation Audit",
        "preferred_contact": "whatsapp",
        "notes": "Please verify Mumbai stamp duty and RBI LTV ceiling.",
        "estimate_context": est,
    }
    r = client.post("/api/contact", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"
    assert data["lead_id"].startswith("EID-")
    assert data["report_ready"] is True
    assert data["summary"]["predicted_price"] == est["predicted_price"]


def test_contact_invalid_email_is_422():
    r = client.post("/api/contact", json={
        "name": "Test User",
        "email": "notanemail",
        "phone": "9820012345",
    })
    assert r.status_code == 422


def test_macro_news_endpoint():
    r = client.get("/api/macro-news")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert len(data["events"]) >= 5
    first = data["events"][0]
    assert "year" in first
    assert "headline" in first
    assert "primary_source" in first


def test_estimate_includes_macro_news():
    r = client.post("/api/estimate", json=VALID)
    assert r.status_code == 200
    data = r.json()
    assert "macro_news" in data
    assert len(data["macro_news"]) >= 5
    assert all("primary_source" in ev for ev in data["macro_news"])


def test_offer_strategy_endpoint():
    payload = {
        "property_value": 15_000_000,
        "price_low": 13_500_000,
        "price_high": 16_500_000,
        "target_offer": 14_000_000,
        "city": "Mumbai (MMR)",
        "locality": "Worli Sea Face",
    }
    r = client.post("/api/finance/offer-strategy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["tier"] in ("AGGRESSIVE_BARGAIN", "FAIR_BENCHMARK", "PREMIUM_SELLER")
    assert len(data["negotiation_points"]) == 3
    assert data["discount_inr"] == 1_000_000


def test_loan_prepayment_endpoint():
    payload = {
        "loan_amount": 10_000_000,
        "annual_rate_pct": 8.5,
        "tenure_years": 20,
        "monthly_prepayment": 15_000,
        "annual_lumpsum": 100_000,
    }
    r = client.post("/api/finance/loan-prepayment", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["years_saved"] > 3.0
    assert data["interest_saved"] > 0


def test_buy_vs_rent_endpoint():
    payload = {
        "property_value": 15_000_000,
        "city": "Mumbai (MMR)",
        "state": "Maharashtra",
        "down_payment_pct": 20.0,
        "annual_rate_pct": 8.5,
        "tenure_years": 20,
    }
    r = client.post("/api/finance/buy-vs-rent", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "gross_rental_yield_pct" in data
    assert len(data["trajectory"]) == 20


def test_infrastructure_projects_endpoint():
    r = client.get("/api/infrastructure-projects?locality=Worli+Sea+Face")
    assert r.status_code == 200
    data = r.json()
    assert len(data["active_projects"]) >= 1
    assert data["catalyst_cagr_pct"] > 0


def test_market_heatmap_endpoint():
    r = client.get("/api/market-heatmap")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 5
    assert all("rate" in n and "yield" in n for n in data)


def test_compare_properties_endpoint():
    payload = {
        "properties": [
            {
                "name": "Worli 3 BHK",
                "property_value": 35_000_000,
                "area_sqft": 2200,
                "bhk": 3,
                "city": "Mumbai (MMR)",
                "locality": "Worli Sea Face",
            },
            {
                "name": "Powai 2 BHK",
                "property_value": 18_000_000,
                "area_sqft": 1100,
                "bhk": 2,
                "city": "Mumbai (MMR)",
                "locality": "Powai Hiranandani",
            },
        ]
    }
    r = client.post("/api/finance/compare-properties", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["properties"]) == 2
    assert "winner_summary" in data

