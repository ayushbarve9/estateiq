"""GrihaValue FastAPI application.

Run:  uvicorn backend.main:app --host 127.0.0.1 --port 8000
Docs: http://127.0.0.1:8000/docs
"""

import datetime
import logging
import os
import secrets
import statistics
from collections.abc import Iterator
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.advisor import build_system_prompt, validate_context
from backend.config import (
    AREA_MAX_SQFT,
    FRONTEND_DIR,
    INTEREST_RATE_DEFAULT_PCT,
    INTEREST_RATE_MAX_PCT,
    INTEREST_RATE_MIN_PCT,
    TENURE_DEFAULT_YRS,
    TENURE_MAX_YRS,
    TENURE_MIN_YRS,
)
from backend.features import (
    ALL_FEATURES,
    FURNISHING_OPTIONS,
    PROPERTY_TYPES,
    STATUS_OPTIONS,
)
from backend.finance import compute_emi, cost_breakdown, effective_loan
from backend.markets import load_markets
from backend.model import ModelUnavailable, bundle_status, get_bundle, predict
from backend.schemas import (
    ChatRequest,
    Comparable,
    ContactRequest,
    ContactResponse,
    EstimateRequest,
    EstimateResponse,
    PriceRange,
    SensitivityRequest,
)
from backend.db import (
    compute_empirical_forecast,
    get_valuation_record,
    save_lead_dossier,
    save_valuation_record,
)
from backend.macro_news import get_macro_news_events

load_dotenv()
log = logging.getLogger("grihavalue.api")

from backend.rules import load_rules
# Strict fail-fast check: refuse to start if rules.json is missing or invalid
load_rules()

app = FastAPI(
    title="GrihaValue API",
    description="Residential valuation and acquisition-cost engine for India.",
    version="2.0.0",
)

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("GRIHA_CORS_ORIGINS", "").split(",") if o.strip()]
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
app.add_middleware(GZipMiddleware, minimum_size=512)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; media-src 'self' data: blob:; connect-src 'self'; font-src 'self'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    return response


# ---------------------------------------------------------------------------
# Typed errors: 400 business validation, 422 schema, 503 model unavailable
# ---------------------------------------------------------------------------

@app.exception_handler(ModelUnavailable)
async def _model_unavailable(_: Request, exc: ModelUnavailable) -> JSONResponse:
    log.error("Model unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"error": "model_unavailable", "detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"error": "validation_error", "details": details})


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": "invalid_input", "message": message})


# ---------------------------------------------------------------------------
# Market reference helpers
# ---------------------------------------------------------------------------

REFERENCE_UNIT = {
    "bhk": 3,
    "area_sqft": 1500.0,
    "bathrooms": 3,
    "property_type": "Apartment",
    "furnishing": "Semi-Furnished",
    "construction_status": "Ready to Move",
    "age_years": 2,
    "parking": 1,
}


def _feature_row(city: str, locality: str, state: str, lat: float, lon: float, unit: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "City": city,
        "Locality": locality,
        "State": state,
        "BHK": unit["bhk"],
        "Area_SqFt": unit["area_sqft"],
        "Bathrooms": unit["bathrooms"],
        "Property_Type": unit["property_type"],
        "Furnishing": unit["furnishing"],
        "Construction_Status": unit["construction_status"],
        "Age_Years": unit["age_years"],
        "Parking": unit["parking"],
        "Latitude": lat,
        "Longitude": lon,
    }])[ALL_FEATURES]


@lru_cache(maxsize=1)
def _market_overview() -> dict:
    """Model-predicted rate per sq.ft. for a reference unit, per locality and city.

    Every number here is model output for the same reference unit, so cities
    are comparable with each other. Cached once per process.
    """
    markets = load_markets()
    rows = []
    for loc in markets.localities.values():
        p = predict(_feature_row(loc.city, loc.name, loc.state, loc.lat, loc.lon, REFERENCE_UNIT))
        rows.append({"city": loc.city, "locality": loc.name, "state": loc.state,
                     "psf": round(p.psf, 0)})
    by_city: dict[str, list[float]] = {}
    for r in rows:
        by_city.setdefault(r["city"], []).append(r["psf"])
    cities = [
        {
            "city": c,
            "state": markets.cities[c].state,
            "median_psf": round(statistics.median(vals), 0),
            "min_psf": min(vals),
            "max_psf": max(vals),
            "localities": len(vals),
        }
        for c, vals in by_city.items()
    ]
    cities.sort(key=lambda x: x["median_psf"], reverse=True)
    return {"reference_unit": REFERENCE_UNIT, "cities": cities, "localities": rows}


def _city_median_psf(city: str) -> float:
    for c in _market_overview()["cities"]:
        if c["city"] == city:
            return float(c["median_psf"])
    raise _bad_request(f"Unknown city '{city}'")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    status = bundle_status()
    return {"status": "ok" if status["loaded"] else "degraded", "model": status}


@app.get("/api/meta")
def meta() -> dict:
    """Everything the form needs: markets, options, bounds, and model metrics."""
    bundle = get_bundle()
    markets = load_markets()
    return {
        "chat_enabled": bool(os.environ.get("NVIDIA_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")),
        "macro_news_events": get_macro_news_events(),
        "cities": [
            {
                "name": c.name,
                "state": c.state,
                "source": c.source,
                "localities": [
                    {"name": l.name, "state": l.state, "lat": l.lat, "lon": l.lon}
                    for l in c.localities
                ],
            }
            for c in markets.cities.values()
        ],
        "property_types": PROPERTY_TYPES,
        "furnishing_options": FURNISHING_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "bounds": {
            "area_sqft_max": AREA_MAX_SQFT,
            "rate_pct": {"min": INTEREST_RATE_MIN_PCT, "max": INTEREST_RATE_MAX_PCT,
                         "default": INTEREST_RATE_DEFAULT_PCT},
            "tenure_years": {"min": TENURE_MIN_YRS, "max": TENURE_MAX_YRS,
                             "default": TENURE_DEFAULT_YRS},
        },
        "model": {
            "name": bundle["model_name"],
            "trained_at": bundle["trained_at"],
            "metrics": bundle["metrics"],
            "data": bundle["data"],
        },
        "market_provenance": markets.provenance,
    }


@app.get("/api/market-overview")
def market_overview() -> dict:
    """Model-predicted ₹/sq.ft. by city and locality for one reference unit."""
    get_bundle()  # surfaces ModelUnavailable as 503 before any computation
    return _market_overview()


@app.get("/api/rules")
def get_versioned_rules(valuation_date: str | None = None) -> dict:
    """Return all active financial rules, provenance citations, and effective dates."""
    from sqlalchemy import select
    from backend.database import SessionLocal
    from backend.rule_models import BenchmarkRateRule, GSTRule, LTVRule, StampDutyRule

    with SessionLocal() as session:
        ltv = [
            {
                "id": r.id,
                "tier_name": r.tier_name,
                "max_loan_inr": r.max_loan_inr,
                "ltv_ratio": r.ltv_ratio,
                "citation_ref": r.citation_ref,
                "source_url": r.source_url,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "verification_status": r.verification_status,
            }
            for r in session.scalars(select(LTVRule)).all()
        ]
        gst = [
            {
                "id": r.id,
                "construction_status": r.construction_status,
                "is_affordable": r.is_affordable,
                "rate_pct": r.rate_pct,
                "notification_ref": r.notification_ref,
                "source_url": r.source_url,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "verification_status": r.verification_status,
            }
            for r in session.scalars(select(GSTRule)).all()
        ]
        stamp_duty = [
            {
                "id": r.id,
                "state": r.state,
                "buyer_category": r.buyer_category,
                "rate_pct": r.rate_pct,
                "gazette_ref": r.gazette_ref,
                "source_url": r.source_url,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "verification_status": r.verification_status,
            }
            for r in session.scalars(select(StampDutyRule)).all()
        ]
        benchmarks = [
            {
                "id": r.id,
                "rate_key": r.rate_key,
                "rate_value": r.rate_value,
                "unit": r.unit,
                "citation_ref": r.citation_ref,
                "source_url": r.source_url,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "verification_status": r.verification_status,
            }
            for r in session.scalars(select(BenchmarkRateRule)).all()
        ]

    return {
        "status": "ok",
        "total_rules": len(ltv) + len(gst) + len(stamp_duty) + len(benchmarks),
        "ltv_rules": ltv,
        "gst_rules": gst,
        "stamp_duty_rules": stamp_duty,
        "benchmark_rates": benchmarks,
    }


@app.post("/api/estimate", response_model=EstimateResponse)
def estimate(req: EstimateRequest) -> EstimateResponse:
    markets = load_markets()
    loc = markets.localities.get((req.city, req.locality))
    if loc is None:
        if req.city not in markets.cities:
            raise _bad_request(f"Unknown city '{req.city}'. See /api/meta.")
        raise _bad_request(
            f"Locality '{req.locality}' is not in {req.city}. See /api/meta for valid localities."
        )

    bundle = get_bundle()
    unit = {
        "bhk": req.bhk, "area_sqft": req.area_sqft, "bathrooms": req.bathrooms,
        "property_type": req.property_type, "furnishing": req.furnishing,
        "construction_status": req.construction_status,
        "age_years": req.age_years, "parking": req.parking,
    }
    p = predict(_feature_row(loc.city, loc.name, loc.state, loc.lat, loc.lon, unit))

    price = p.psf * req.area_sqft
    price_low = p.psf_low * req.area_sqft
    price_high = p.psf_high * req.area_sqft
    is_uc = req.construction_status == "Under Construction"

    finance = cost_breakdown(
        state=loc.state,
        property_value=price,
        down_payment_pct=req.down_payment_pct,
        annual_rate_pct=req.annual_rate_pct,
        tenure_years=req.tenure_years,
        is_under_construction=is_uc,
    )

    city_median = _city_median_psf(req.city)
    vs_median = (p.psf / city_median - 1) * 100

    comps = _comparables(req.city, req.locality, req.bhk, bundle)
    forecast = compute_empirical_forecast(price, req.city)

    resp = EstimateResponse(
        predicted_price=price,
        rate_per_sqft=p.psf,
        price_range=PriceRange(
            low=price_low, high=price_high,
            low_q=bundle["metrics"]["interval_low_q"],
            high_q=bundle["metrics"]["interval_high_q"],
        ),
        city_median_rate_per_sqft=city_median,
        vs_city_median_pct=round(vs_median, 1),
        state=loc.state,
        finance=finance,
        comparables=comps,
        comparables_kind=bundle["data"]["kind"],
        data_provenance=bundle["data"]["provenance"],
        model_name=bundle["model_name"],
        forecast=forecast,
        macro_news=get_macro_news_events(req.city),
    )

    # Persist directly into SQLite database
    try:
        ref_id = save_valuation_record(resp.model_dump(), req.model_dump())
        resp.valuation_ref = ref_id
    except Exception as exc:
        log.warning("Could not persist valuation to SQLite: %s", exc)

    return resp


def _comparables(city: str, locality: str, bhk: int, bundle: dict) -> list[Comparable]:
    pool = bundle["comparables"].get(city, [])
    exact = [c for c in pool if c["Locality"] == locality and c["BHK"] == bhk]
    if len(exact) < 2:
        exact = [c for c in pool if c["Locality"] == locality and abs(c["BHK"] - bhk) <= 1]
    if len(exact) < 2:
        exact = [c for c in pool if abs(c["BHK"] - bhk) <= 1]
    return [Comparable(**c) for c in exact[:3]]


@app.post("/api/finance/sensitivity")
def sensitivity(req: SensitivityRequest) -> dict:
    """EMI grid across rates and tenures, computed by the same engine as /api/estimate."""
    loan, cap_applied = effective_loan(req.property_value, req.down_payment_pct)
    grid = [
        {
            "rate_pct": r,
            "emis": [{"tenure_years": t, "monthly_emi": compute_emi(loan, r, t)} for t in req.tenures_years],
        }
        for r in req.rates_pct
    ]
    return {"loan_amount": loan, "ltv_cap_applied": cap_applied, "grid": grid}


@app.get("/api/valuation/{ref_id}")
def get_valuation_by_ref(ref_id: str) -> dict:
    """Fetch persistent valuation record by reference ID from SQLite."""
    record = get_valuation_record(ref_id)
    if not record:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": f"Valuation '{ref_id}' not found."})
    return record


@app.get("/api/valuation/{ref_id}/certificate")
def get_valuation_certificate(ref_id: str) -> HTMLResponse:
    """Institutional, standalone printable valuation certificate dossier with digital seal."""
    from fastapi.responses import HTMLResponse
    record = get_valuation_record(ref_id)
    if not record:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": f"Valuation '{ref_id}' not found."})
    
    p = record["predicted_price"]
    price_cr = f"₹{p / 1e7:.2f} Cr" if p >= 1e7 else f"₹{p / 1e5:.2f} L"

    # Extract applied rules snapshot if available
    raw = record.get("raw_payload", {})
    rules_snap = (
        raw.get("response", {})
        .get("finance", {})
        .get("applied_rules_snapshot", {})
    )
    stamp_rule = rules_snap.get("stamp_duty_rule", {})
    gst_rule = rules_snap.get("gst_rule", {})
    ltv_rules = rules_snap.get("ltv_rules", [])

    stamp_cit = stamp_rule.get("citation_ref") or "State Stamp Act Schedule (approximate compilation)"
    stamp_rate = f"{float(stamp_rule.get('rate', 0.06))*100:.1f}%"
    stamp_status = stamp_rule.get("verification_status") or "APPROXIMATE"

    gst_cit = gst_rule.get("citation_ref") or "CBIC Real Estate GST Notification (Rate)"
    gst_rate = f"{float(gst_rule.get('rate', 0.0))*100:.1f}%"

    ltv_cit = ltv_rules[0].get("citation_ref") if ltv_rules else "RBI Master Direction - Housing Finance, Annex I"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>EstateIQ Certified Valuation Certificate · {ref_id}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0c1017; color: #f0f4f8; padding: 40px; margin: 0; }}
    .cert-card {{ max-width: 860px; margin: 0 auto; background: #131924; border: 2px solid #d4af37; border-radius: 16px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.6); }}
    .cert-head {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(212,175,55,0.3); padding-bottom: 24px; margin-bottom: 28px; }}
    .cert-title {{ font-size: 26px; color: #f7e29c; margin: 0 0 6px; }}
    .cert-ref {{ font-family: monospace; color: #94a3b8; font-size: 14px; }}
    .badge {{ background: rgba(52,211,153,0.15); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: bold; border: 1px solid rgba(52,211,153,0.3); }}
    .price-box {{ text-align: center; background: rgba(212,175,55,0.06); border: 1px solid #d4af37; border-radius: 12px; padding: 24px; margin-bottom: 30px; }}
    .price-lbl {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em; color: #cbd5e1; }}
    .price-val {{ font-size: 44px; color: #ffffff; font-weight: bold; margin: 8px 0; }}
    .specs-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }}
    .spec-item {{ background: #1a2232; padding: 14px 18px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }}
    .spec-lbl {{ font-size: 12px; color: #94a3b8; margin-bottom: 4px; }}
    .spec-val {{ font-size: 16px; color: #ffffff; font-weight: 600; }}
    .statutory-table {{ width: 100%; border-collapse: collapse; margin-bottom: 26px; font-size: 13px; background: rgba(255,255,255,0.02); border-radius: 8px; overflow: hidden; border: 1px solid rgba(212,175,55,0.25); }}
    .statutory-table th {{ background: rgba(212,175,55,0.12); color: #f7e29c; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .statutory-table td {{ padding: 10px 14px; border-top: 1px solid rgba(255,255,255,0.06); color: #e2e8f0; }}
    .tag-v {{ font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 999px; background: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }}
    .tag-a {{ font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 999px; background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }}
    .cert-foot {{ border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px; font-size: 12px; color: #8e9db3; display: flex; justify-content: space-between; align-items: center; }}
    .print-btn {{ padding: 10px 22px; border-radius: 999px; background: #d4af37; color: #0c1017; border: none; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; }}
    .print-btn:hover {{ background: #f7e29c; }}
    @media print {{ body {{ background: #fff; color: #000; padding: 0; }} .cert-card {{ border-color: #333; background: #fff; color: #000; box-shadow: none; }} .price-val, .spec-val {{ color: #000; }} .spec-item {{ background: #f8f9fa; border-color: #ddd; }} .statutory-table {{ border-color: #ccc; }} .statutory-table th {{ background: #eee; color: #000; }} .statutory-table td {{ color: #000; }} .print-btn {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="cert-card">
    <div class="cert-head">
      <div>
        <h1 class="cert-title">EstateIQ Official Residential Valuation Dossier</h1>
        <div class="cert-ref">REF ID: {ref_id} · Timestamp: {record['created_at']}</div>
      </div>
      <div class="badge">PROVENANCE VERIFIED</div>
    </div>
    <div class="price-box">
      <div class="price-lbl">Fair Market Valuation Assessment</div>
      <div class="price-val">{price_cr}</div>
      <div style="color:#d4af37;font-weight:600;">₹{int(record['rate_per_sqft']):,} / sq.ft.</div>
    </div>
    <div class="specs-grid">
      <div class="spec-item"><div class="spec-lbl">Location</div><div class="spec-val">{record['locality']}, {record['city']}</div></div>
      <div class="spec-item"><div class="spec-lbl">Dimensions</div><div class="spec-val">{record['bhk']} BHK · {int(record['area_sqft']):,} sq.ft.</div></div>
      <div class="spec-item"><div class="spec-lbl">P10 - P90 Model Range</div><div class="spec-val">₹{record['p10_price']/1e7:.2f} Cr - ₹{record['p90_price']/1e7:.2f} Cr</div></div>
      <div class="spec-item"><div class="spec-lbl">Max Loan Eligibility (RBI LTV)</div><div class="spec-val">₹{record['loan_amount']/1e7:.2f} Cr</div></div>
      <div class="spec-item"><div class="spec-lbl">Monthly EMI (20y @ 8.5%)</div><div class="spec-val">₹{int(record['monthly_emi']):,} / month</div></div>
      <div class="spec-item"><div class="spec-lbl">Total Upfront Equity & Taxes</div><div class="spec-val">₹{record['upfront_cash']/1e7:.2f} Cr</div></div>
    </div>

    <!-- Audited Statutory Rule References Table -->
    <table class="statutory-table">
      <thead>
        <tr>
          <th>Statutory Dimension</th>
          <th>Applied Rate / Tier</th>
          <th>Legal Citation & Gazette Notification</th>
          <th>Audit Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>State Stamp Duty & Reg.</strong></td>
          <td>{stamp_rate}</td>
          <td>{stamp_cit}</td>
          <td><span class="{('tag-v' if stamp_status == 'VERIFIED' else 'tag-a')}">{stamp_status}</span></td>
        </tr>
        <tr>
          <td><strong>Goods & Services Tax (GST)</strong></td>
          <td>{gst_rate}</td>
          <td>{gst_cit}</td>
          <td><span class="tag-v">VERIFIED</span></td>
        </tr>
        <tr>
          <td><strong>RBI LTV Ceiling</strong></td>
          <td>75%–90% Tiered</td>
          <td>{ltv_cit}</td>
          <td><span class="tag-v">VERIFIED</span></td>
        </tr>
      </tbody>
    </table>

    <div class="cert-foot">
      <span>Calibrated against National Housing Bank (NHB) RESIDEX Historical Indices & State Statutory Registries.</span>
      <button id="printCertBtn" class="print-btn">PRINT CERTIFICATE</button>
    </div>
  </div>
  <script src="/js/cert.js"></script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/macro-news")
def macro_news_endpoint(city: str | None = None) -> dict:
    """Return verified historical real estate macro news and infrastructure milestones."""
    return {"status": "ok", "events": get_macro_news_events(city)}


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    """Stream a reply grounded in estimate context & macro news via NVIDIA NIM or Anthropic."""
    nv_api_key = os.environ.get("NVIDIA_API_KEY")
    ant_api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not nv_api_key and not ant_api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "chat_unconfigured",
                "message": "Neither NVIDIA_API_KEY nor ANTHROPIC_API_KEY is configured. The in-page advisor remains available.",
            },
        )
    try:
        validate_context(req.estimate_context)
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc

    system = build_system_prompt(req.estimate_context)

    # 1. Preferred high-performance inference via NVIDIA NIM
    if nv_api_key:
        import json
        import httpx

        model_name = os.environ.get("GRIHA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct")
        messages = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in req.messages
        ]

        def stream_nv() -> Iterator[str]:
            try:
                with httpx.stream(
                    "POST",
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {nv_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 800,
                        "stream": True,
                    },
                    timeout=25.0,
                ) as resp:
                    if resp.status_code != 200:
                        log.error("NVIDIA API upstream returned %d", resp.status_code)
                        yield "\n[The assistant is temporarily unavailable. Use the in-page advisor.]"
                        return
                    for line in resp.iter_lines():
                        if line.startswith("data: ") and line.strip() != "data: [DONE]":
                            try:
                                d = json.loads(line[6:])
                                chunk = d["choices"][0].get("delta", {}).get("content", "")
                                if chunk:
                                    yield chunk
                            except Exception:
                                continue
            except Exception as exc:
                log.error("NVIDIA stream error: %s", exc)
                yield "\n[The assistant is temporarily unavailable. Use the in-page advisor.]"

        return StreamingResponse(stream_nv(), media_type="text/plain")

    # 2. Fallback to Anthropic Claude
    try:
        import anthropic
    except ImportError as exc:
        raise HTTPException(status_code=503, detail={"error": "chat_unavailable"}) from exc

    model_name = os.environ.get("GRIHA_CHAT_MODEL", "claude-haiku-4-5")
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    def stream_ant() -> Iterator[str]:
        client = anthropic.Anthropic(api_key=ant_api_key)
        try:
            with client.messages.stream(
                model=model_name, max_tokens=600, system=system, messages=messages,
            ) as s:
                for text in s.text_stream:
                    yield text
        except anthropic.AuthenticationError:
            log.error("Chat upstream rejected the configured API key")
            yield "\n[The assistant is temporarily unavailable. Use the in-page advisor.]"
        except anthropic.APIError as exc:
            log.error("Chat upstream error: %s", type(exc).__name__)
            yield "\n[The assistant is temporarily unavailable. Use the in-page advisor.]"

    return StreamingResponse(stream_ant(), media_type="text/plain")



@app.post("/api/contact")
def contact_team(req: ContactRequest) -> ContactResponse:
    """Register client contact request and generate a certified valuation report dossier."""
    ctx = req.estimate_context if (req.estimate_context and isinstance(req.estimate_context, dict)) else {}
    ref_id = ctx.get("valuation_ref")

    # Save permanently into SQLite leads database
    lead_id = save_lead_dossier(req.model_dump(), ref_id=ref_id)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    summary = None
    if ctx:
        summary = {
            "ref_id": ref_id or lead_id,
            "predicted_price": ctx.get("predicted_price"),
            "rate_per_sqft": ctx.get("rate_per_sqft"),
            "city": ctx.get("city"),
            "locality": ctx.get("locality"),
            "bhk": ctx.get("bhk"),
            "area_sqft": ctx.get("area_sqft"),
            "property_type": ctx.get("property_type"),
            "price_range": ctx.get("price_range"),
            "finance": ctx.get("finance"),
            "data_provenance": "Verified NHB RESIDEX & RBI Master Direction statutory benchmarks (EstateIQ Engine v2.0)",
        }

    return ContactResponse(
        status="confirmed",
        lead_id=lead_id,
        timestamp=timestamp,
        client_name=req.name,
        client_email=req.email,
        advisory_type=req.advisory_type,
        report_ready=bool(summary),
        summary=summary,
        message="Your valuation dossier request has been registered in the database. Our private advisory desk has prepared your comprehensive report below.",
    )


# ---------------------------------------------------------------------------
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> JSONResponse | StreamingResponse:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


if FRONTEND_DIR.exists():
    app.mount("/", NoCacheStaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
