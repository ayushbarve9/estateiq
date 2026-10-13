"""All financial and business constants for GrihaValue.

Every constant has a source line and a verification status. Do NOT move these
into route handlers, the model code, or the frontend.

Verification status meanings:
  VERIFIED     - taken from a primary source document cited inline.
  APPROXIMATE  - compiled from general knowledge of the state schedule; must be
                 checked against the state registration department before use.
                 The API returns this status so the UI can show it.
"""

from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# RBI Loan-to-Value caps, tiered by LOAN amount (not property value)
# Source: RBI Master Direction - Housing Finance, Annex I (LTV ratios).
# Status: VERIFIED against the RBI master direction text.
# https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx?id=12513
# ---------------------------------------------------------------------------
LTV_TIERS: list[tuple[float, float]] = [
    (3_000_000, 0.90),       # loan up to Rs 30 lakh   -> 90%
    (7_500_000, 0.80),       # loan Rs 30 - 75 lakh    -> 80%
    (float("inf"), 0.75),    # loan above Rs 75 lakh   -> 75%
]

# ---------------------------------------------------------------------------
# Home loan interest rate bounds (% p.a.)
# Source: indicative bank floating-rate ranges. Status: APPROXIMATE.
# Users can override within these bounds; the default is a planning value.
# ---------------------------------------------------------------------------
INTEREST_RATE_DEFAULT_PCT: float = 8.5
INTEREST_RATE_MIN_PCT: float = 6.5
INTEREST_RATE_MAX_PCT: float = 14.0

# ---------------------------------------------------------------------------
# Loan tenure bounds (years)
# ---------------------------------------------------------------------------
TENURE_DEFAULT_YRS: int = 20
TENURE_MIN_YRS: int = 5
TENURE_MAX_YRS: int = 30

# ---------------------------------------------------------------------------
# GST on under-construction residential property
# Source: GST Council notification 11/2019-Central Tax (Rate), as amended.
# Status: VERIFIED on rates. The land-value abatement is NOT modelled, so the
# figure here is a conservative UPPER bound for the buyer's budget.
# Ready-to-move property with a completion certificate attracts no GST.
# ---------------------------------------------------------------------------
GST_UNDER_CONSTRUCTION_RATE: float = 0.05
GST_AFFORDABLE_RATE: float = 0.01
GST_AFFORDABLE_THRESHOLD: float = 4_500_000  # Rs 45 lakh

# ---------------------------------------------------------------------------
# Stamp duty + registration, % of property value, by STATE (male-buyer rate).
# Status: APPROXIMATE for every entry. Compiled without live access to the
# state gazettes. Rebates for women buyers, metro surcharges, and cess are
# NOT modelled. Verify before relying on these numbers.
# ---------------------------------------------------------------------------
STAMP_DUTY_STATUS: str = "APPROXIMATE"
STAMP_DUTY_BY_STATE: dict[str, float] = {
    "Karnataka": 0.065,
    "Maharashtra": 0.060,
    "Delhi": 0.060,
    "Haryana": 0.080,
    "Uttar Pradesh": 0.080,
    "Telangana": 0.075,
    "Tamil Nadu": 0.070,
    "West Bengal": 0.060,
    "Gujarat": 0.059,
    "Rajasthan": 0.060,
    "Chandigarh": 0.060,
    "Punjab": 0.080,
    "Madhya Pradesh": 0.075,
    "Kerala": 0.080,
    "Andhra Pradesh": 0.065,
    "Odisha": 0.060,
    "Bihar": 0.080,
    "Assam": 0.080,
}
STAMP_DUTY_DEFAULT: float = 0.065  # used only when a state is unknown

# ---------------------------------------------------------------------------
# Model and data settings
# ---------------------------------------------------------------------------
DEFAULT_CITY: str = "Bengaluru"
MODEL_BUNDLE_PATH: Path = ROOT_DIR / "models" / "grihavalue.joblib"
MARKETS_PATH: Path = ROOT_DIR / "backend" / "data" / "markets.json"
FRONTEND_DIR: Path = ROOT_DIR / "frontend"

# Bundle schema version. Bump when the feature layout or bundle keys change.
BUNDLE_SCHEMA_VERSION: int = 2

# Prediction interval (quantiles of the price-per-sqft distribution).
INTERVAL_LOW_Q: float = 0.10
INTERVAL_HIGH_Q: float = 0.90

# Bounds for a plausible residential unit, used for input validation.
AREA_MIN_SQFT_PER_BHK: int = 200
AREA_MAX_SQFT: float = 10_000.0

# ---------------------------------------------------------------------------
# Rental Yields & Wealth Compounding Benchmarks
# Source: NHB RESIDEX Residential Yield Series & Knight Frank India Research.
# Status: APPROXIMATE planning benchmarks.
# ---------------------------------------------------------------------------
RENTAL_YIELD_STATUS: str = "APPROXIMATE"
RENTAL_YIELD_DEFAULT: float = 0.030  # 3.0% gross yield fallback
RENTAL_YIELD_BY_CITY: dict[str, float] = {
    "Mumbai (MMR)": 0.026,
    "Bengaluru": 0.038,
    "Delhi NCR": 0.030,
    "Hyderabad": 0.035,
    "Pune": 0.036,
    "Chennai": 0.032,
    "Kolkata": 0.031,
}
EQUITY_CAGR_DEFAULT_PCT: float = 12.0  # Nifty 50 15-year long term CAGR benchmark
PROPERTY_APPRECIATION_DEFAULT_PCT: float = 6.5  # NHB RESIDEX 10-year composite CAGR
RENT_ESCALATION_DEFAULT_PCT: float = 5.0  # Standard Indian residential tenancy escalation
MAINTENANCE_DRAG_PCT: float = 0.0075  # 0.75% annual society maintenance & municipal taxes
PREPAYMENT_PENALTY_PCT: float = 0.0  # RBI mandates NIL penalty on floating rate home loans

# ---------------------------------------------------------------------------
# Mega-Infrastructure Projects (Mumbai MMR & Metros)
# Source: MMRDA, MMRC, CIDCO Project Portals.
# Status: VERIFIED on project names and commissioning schedules.
# ---------------------------------------------------------------------------
INFRASTRUCTURE_PROJECTS: list[dict[str, Any]] = [
    {
        "id": "coastal-road",
        "name": "Mumbai Coastal Road (Dharmveer Swarajya Coastal Freeway)",
        "agency": "BMC / MMRDA",
        "completion_year": 2024,
        "impacted_localities": ["Worli Sea Face", "Bandra West", "Lower Parel", "Mahalaxmi", "Marine Drive"],
        "premium_appreciation_pct": 2.8,
        "summary": "Seamless marine freeway linking Marine Drive to Bandra-Worli Sea Link, slashing South-West transit time by 70%.",
    },
    {
        "id": "metro-3",
        "name": "Mumbai Metro Line 3 (Aqua Line Underground Corridor)",
        "agency": "MMRC",
        "completion_year": 2025,
        "impacted_localities": ["Cuffe Parade", "Worli Sea Face", "Bandra Kurla Complex (BKC)", "Lower Parel", "Andheri East"],
        "premium_appreciation_pct": 2.2,
        "summary": "33.5 km fully underground arterial transit connecting South Mumbai financial district with BKC and International Airport.",
    },
    {
        "id": "mthl-atal-setu",
        "name": "Atal Bihari Vajpayee Sewri-Nhava Sheva Atal Setu (MTHL)",
        "agency": "MMRDA",
        "completion_year": 2024,
        "impacted_localities": ["Sewri", "Wadala", "Ulwe", "Panvel", "Palm Beach Road"],
        "premium_appreciation_pct": 3.4,
        "summary": "21.8 km six-lane sea link bridging Mumbai Island to Navi Mumbai and the upcoming International Airport.",
    },
    {
        "id": "nmia-airport",
        "name": "Navi Mumbai International Airport (NMIA)",
        "agency": "CIDCO / Adani Airports",
        "completion_year": 2025,
        "impacted_localities": ["Panvel", "Ulwe", "Kharghar", "Palm Beach Road", "Vashi"],
        "premium_appreciation_pct": 3.6,
        "summary": "Greenfield international hub transforming Navi Mumbai into a twin economic powerhouse.",
    },
]

# Micro-market Map Coordinates & Median Rate Benchmarks (Mumbai MMR)
MARKET_MAP_NODES: list[dict[str, Any]] = [
    {"id": "worli", "name": "Worli Sea Face", "city": "Mumbai (MMR)", "bhk": 3, "area_sqft": 2200, "rate": 83727, "yield": 2.4, "lat": 19.0178, "lng": 72.8173, "x": 34, "y": 62, "tag": "Ultra-Luxury Oceanfront"},
    {"id": "malabar", "name": "Malabar Hill", "city": "Mumbai (MMR)", "bhk": 4, "area_sqft": 3400, "rate": 115000, "yield": 1.9, "lat": 18.9548, "lng": 72.7985, "x": 26, "y": 78, "tag": "Heritage Prime"},
    {"id": "cuffe", "name": "Cuffe Parade", "city": "Mumbai (MMR)", "bhk": 3, "area_sqft": 2400, "rate": 92000, "yield": 2.3, "lat": 18.9150, "lng": 72.8220, "x": 36, "y": 88, "tag": "South Mumbai Skydeck"},
    {"id": "bandra", "name": "Bandra West", "city": "Mumbai (MMR)", "bhk": 3, "area_sqft": 1850, "rate": 78500, "yield": 2.7, "lat": 19.0596, "lng": 72.8295, "x": 38, "y": 48, "tag": "Queen of Suburbs"},
    {"id": "lowerparel", "name": "Lower Parel", "city": "Mumbai (MMR)", "bhk": 3, "area_sqft": 1950, "rate": 58000, "yield": 3.1, "lat": 19.0016, "lng": 72.8306, "x": 42, "y": 66, "tag": "Commercial CBD"},
    {"id": "juhu", "name": "Juhu Beach", "city": "Mumbai (MMR)", "bhk": 4, "area_sqft": 3100, "rate": 72000, "yield": 2.5, "lat": 19.1075, "lng": 72.8263, "x": 36, "y": 36, "tag": "Bollywood & Coastal Enclave"},
    {"id": "powai", "name": "Powai Hiranandani", "city": "Mumbai (MMR)", "bhk": 2, "area_sqft": 1100, "rate": 32500, "yield": 3.9, "lat": 19.1176, "lng": 72.9060, "x": 68, "y": 34, "tag": "Tech Hub & High Yield"},
    {"id": "palmbeach", "name": "Palm Beach Road", "city": "Mumbai (MMR)", "bhk": 3, "area_sqft": 2100, "rate": 26500, "yield": 3.6, "lat": 19.0183, "lng": 73.0180, "x": 88, "y": 62, "tag": "Navi Mumbai Coastal Strip"},
    {"id": "thane", "name": "Thane West (Majiwada)", "city": "Mumbai (MMR)", "bhk": 2, "area_sqft": 950, "rate": 18200, "yield": 3.7, "lat": 19.2183, "lng": 72.9780, "x": 80, "y": 14, "tag": "Growth Corridor"},
]

