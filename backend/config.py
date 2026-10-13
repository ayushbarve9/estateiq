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
