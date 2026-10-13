"""Train the GrihaValue price model and write the bundle.

Usage:
    python -m backend.train                       # synthetic data from markets.json
    python -m backend.train --csv my_sales.csv    # real transactions (recommended)

Target: log(price per sq.ft). Predicted price = predicted psf x area.
The point model is a voting ensemble (RandomForest + HistGradientBoosting).
Two quantile GBMs (P10 and P90) give the price range shown to users.

Metrics are computed on a held-out 20% split. The deployed models are the
ones trained on the 80% split, so reported metrics describe the deployed model.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.config import (
    BUNDLE_SCHEMA_VERSION,
    INTERVAL_HIGH_Q,
    INTERVAL_LOW_Q,
    MODEL_BUNDLE_PATH,
)
from backend.features import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    FURNISHING_OPTIONS,
    NUMERIC_FEATURES,
    PROPERTY_TYPES,
    STATUS_OPTIONS,
)
from backend.markets import MarketIndex, load_markets
from backend.model import markets_fingerprint
from backend.macro_news import HISTORICAL_NEWS_EVENTS

log = logging.getLogger("grihavalue.train")

# Noise added to the synthetic generator. This sets the irreducible error
# floor of any model trained on this data (reported in metrics).
SYNTHETIC_NOISE_SIGMA: float = 0.10

REQUIRED_CSV_COLUMNS = ["City", "Locality", "BHK", "Area_SqFt", "Price_INR",
                        "Construction_Status", "Property_Type"]

TYPE_FACTOR = {"Apartment": 1.0, "Builder Floor": 0.92,
               "Independent Villa": 1.08, "Penthouse": 1.25}
FURNISH_FACTOR = {"Unfurnished": 0.97, "Semi-Furnished": 1.0, "Fully Furnished": 1.04}
STATUS_FACTOR = {"Ready to Move": 1.0, "Under Construction": 0.93}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def generate_synthetic_dataset(markets: MarketIndex, n_rows: int, seed: int) -> pd.DataFrame:
    """Generate listings from the market reference plus lognormal noise.

    This is a MODEL OF THE MARKET, not transaction data. Its purpose is to
    exercise the pipeline and give a sensible default. Replace it with real
    transactions via --csv for production accuracy.
    """
    if n_rows < 500:
        raise ValueError("n_rows must be at least 500")
    rng = np.random.default_rng(seed)
    locs = list(markets.localities.values())
    loc_idx = rng.integers(0, len(locs), n_rows)

    bhk = rng.choice([1, 2, 3, 4, 5], n_rows, p=[0.12, 0.36, 0.32, 0.15, 0.05])
    area_lo = np.array([450, 850, 1200, 2000, 3000])[bhk - 1]
    area_hi = np.array([700, 1350, 2100, 3300, 5000])[bhk - 1]
    area = rng.uniform(area_lo, area_hi)
    bathrooms = np.clip(bhk + rng.integers(0, 2, n_rows), 1, None)

    ptype = rng.choice(PROPERTY_TYPES, n_rows, p=[0.70, 0.15, 0.10, 0.05])
    ptype = np.where((ptype == "Penthouse") & (bhk < 2), "Apartment", ptype)
    ptype = np.where((ptype == "Independent Villa") & (bhk < 2), "Apartment", ptype)

    furnishing = rng.choice(FURNISHING_OPTIONS, n_rows, p=[0.35, 0.40, 0.25])
    status = rng.choice(STATUS_OPTIONS, n_rows, p=[0.70, 0.30])
    age = np.where(status == "Under Construction", 0, rng.integers(0, 41, n_rows))
    parking = rng.integers(0, 4, n_rows)

    premium = np.array([locs[i].premium for i in loc_idx])
    base = np.array([markets.cities[locs[i].city].base_psf for i in loc_idx])
    type_f = np.array([TYPE_FACTOR[t] for t in ptype])
    furn_f = np.array([FURNISH_FACTOR[f] for f in furnishing])
    status_f = np.array([STATUS_FACTOR[s] for s in status])
    age_f = np.maximum(0.70, 1 - 0.008 * age)
    park_f = 1 + 0.015 * np.minimum(parking, 2)
    size_f = (area / 1000) ** -0.06
    noise = rng.lognormal(0.0, SYNTHETIC_NOISE_SIGMA, n_rows)

    psf = base * premium * type_f * furn_f * status_f * age_f * park_f * size_f * noise
    price = psf * area

    lat = np.array([locs[i].lat for i in loc_idx]) + rng.normal(0, 0.01, n_rows)
    lon = np.array([locs[i].lon for i in loc_idx]) + rng.normal(0, 0.01, n_rows)

    df = pd.DataFrame({
        "City": [locs[i].city for i in loc_idx],
        "Locality": [locs[i].name for i in loc_idx],
        "State": [locs[i].state for i in loc_idx],
        "BHK": bhk,
        "Area_SqFt": area.round(0),
        "Bathrooms": bathrooms,
        "Property_Type": ptype,
        "Furnishing": furnishing,
        "Construction_Status": status,
        "Age_Years": age,
        "Parking": parking,
        "Latitude": lat.round(6),
        "Longitude": lon.round(6),
        "Price_INR": price.round(0),
    })
    df["Price_per_sqft"] = df["Price_INR"] / df["Area_SqFt"]
    return df


def _column(df: pd.DataFrame, name: str, default) -> pd.Series:
    """Return a column, or a constant Series when the CSV lacks it."""
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index, dtype=object)


def load_csv_dataset(path: Path, markets: MarketIndex) -> tuple[pd.DataFrame, dict]:
    """Load real transactions. Returns (frame, report of dropped rows)."""
    raw = pd.read_csv(path)
    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    report: dict = {"input_rows": int(len(raw))}
    unknown = sorted({(c, l) for c, l in zip(raw["City"], raw["Locality"])
                      if (c, l) not in markets.localities})
    if unknown:
        raise ValueError(
            f"{len(unknown)} city/locality pairs are not in markets.json, e.g. {unknown[:5]}. "
            "Add them to backend/data/markets.json first."
        )

    df = raw.copy()
    for col in ["BHK", "Area_SqFt", "Price_INR"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["BHK", "Area_SqFt", "Price_INR"])
    df = df[(df["Area_SqFt"] > 0) & (df["Price_INR"] > 0)]
    df["Price_per_sqft"] = df["Price_INR"] / df["Area_SqFt"]
    df = df[(df["Price_per_sqft"] >= 500) & (df["Price_per_sqft"] <= 500_000)]
    df = df[df["BHK"].between(1, 5)]
    report["kept_rows"] = int(len(df))
    report["dropped_rows"] = report["input_rows"] - report["kept_rows"]
    if len(df) < 500:
        raise ValueError(f"Only {len(df)} usable rows after cleaning; need at least 500.")

    df["State"] = [markets.localities[(c, l)].state for c, l in zip(df["City"], df["Locality"])]
    if "Latitude" not in df.columns:
        df["Latitude"] = [markets.localities[(c, l)].lat for c, l in zip(df["City"], df["Locality"])]
    if "Longitude" not in df.columns:
        df["Longitude"] = [markets.localities[(c, l)].lon for c, l in zip(df["City"], df["Locality"])]
    b_col = _column(df, "Bathrooms", None)
    df["Bathrooms"] = b_col.infer_objects(copy=False).fillna(df["BHK"]).astype(int)
    df["Furnishing"] = _column(df, "Furnishing", "Semi-Furnished").fillna("Semi-Furnished")
    age_col = _column(df, "Age_Years", 0)
    df["Age_Years"] = age_col.infer_objects(copy=False).fillna(0).astype(int).clip(0, 50)
    park_col = _column(df, "Parking", 1)
    df["Parking"] = park_col.infer_objects(copy=False).fillna(1).astype(int).clip(0, 5)
    return df.reset_index(drop=True), report


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])


def _point_regressor(seed: int) -> TransformedTargetRegressor:
    rf = RandomForestRegressor(
        n_estimators=240, max_depth=20, min_samples_leaf=2,
        max_features=0.9, n_jobs=-1, random_state=seed,
    )
    hgb = HistGradientBoostingRegressor(
        max_iter=450, learning_rate=0.05, max_leaf_nodes=75,
        min_samples_leaf=10, l2_regularization=0.08, random_state=seed,
    )
    ensemble = VotingRegressor(estimators=[("rf", rf), ("hgb", hgb)], weights=[0.45, 0.55])
    return TransformedTargetRegressor(regressor=ensemble, func=np.log, inverse_func=np.exp)


def _quantile_regressor(alpha: float, seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="quantile", quantile=alpha,
        max_iter=450, learning_rate=0.05, max_leaf_nodes=35,
        min_samples_leaf=12, l2_regularization=0.05, random_state=seed,
    )


def _fit_pipeline(model, x: pd.DataFrame, y_log: np.ndarray) -> Pipeline:
    pipe = Pipeline([("prep", clone(_preprocessor())), ("model", model)])
    pipe.fit(x, y_log)
    return pipe


def fit_models(df: pd.DataFrame, seed: int) -> dict:
    """Fit on an 80% split and evaluate on the 20% split.

    Conventions (must match backend/model.py at inference):
      point model   -> fitted on raw price per sq.ft.; TransformedTargetRegressor
                       handles log/exp internally, so predict() returns psf.
      quantile GBMs -> fitted on log psf; predict() returns log psf, so exp it.
    """
    x = df[ALL_FEATURES]
    psf = df["Price_per_sqft"]
    log_psf = pd.Series(np.log(psf.to_numpy()), index=df.index)

    idx_tr, idx_te = train_test_split(df.index.to_numpy(), test_size=0.2, random_state=seed)
    x_tr, x_te = x.loc[idx_tr], x.loc[idx_te]
    psf_tr = psf.loc[idx_tr].to_numpy()
    logpsf_tr = log_psf.loc[idx_tr].to_numpy()

    point = _fit_pipeline(_point_regressor(seed), x_tr, psf_tr)
    q_low = _fit_pipeline(_quantile_regressor(INTERVAL_LOW_Q, seed), x_tr, logpsf_tr)
    q_high = _fit_pipeline(_quantile_regressor(INTERVAL_HIGH_Q, seed), x_tr, logpsf_tr)

    area_te = df.loc[idx_te, "Area_SqFt"].to_numpy()
    price_te = df.loc[idx_te, "Price_INR"].to_numpy()
    psf_te = psf.loc[idx_te].to_numpy()

    pred_psf = point.predict(x_te)
    low_psf = np.exp(q_low.predict(x_te))
    high_psf = np.exp(q_high.predict(x_te))
    pred_price = pred_psf * area_te

    # Baseline: median psf of the same city+locality in the training split.
    # A model that does not beat this is not adding value.
    train_df = df.loc[idx_tr]
    loc_median = train_df.groupby(["City", "Locality"])["Price_per_sqft"].median()
    global_median = float(train_df["Price_per_sqft"].median())
    keys = list(zip(df.loc[idx_te, "City"], df.loc[idx_te, "Locality"]))
    base_psf = np.array([float(loc_median.get(k, global_median)) for k in keys])
    base_price = base_psf * area_te

    ape = np.abs(pred_price - price_te) / price_te
    base_ape = np.abs(base_price - price_te) / price_te
    covered = (price_te >= low_psf * area_te) & (price_te <= high_psf * area_te)

    metrics = {
        "holdout_rows": int(len(idx_te)),
        "train_rows": int(len(idx_tr)),
        "r2_price": float(r2_score(price_te, pred_price)),
        "r2_log_psf": float(r2_score(np.log(psf_te), np.log(pred_psf))),
        "mae_inr": float(mean_absolute_error(price_te, pred_price)),
        "mape_pct": float(ape.mean() * 100),
        "median_ape_pct": float(np.median(ape) * 100),
        "p90_ape_pct": float(np.quantile(ape, 0.90) * 100),
        "baseline_locality_median_mape_pct": float(base_ape.mean() * 100),
        "interval_low_q": INTERVAL_LOW_Q,
        "interval_high_q": INTERVAL_HIGH_Q,
        "interval_coverage_pct": float(covered.mean() * 100),
        "interval_target_pct": float((INTERVAL_HIGH_Q - INTERVAL_LOW_Q) * 100),
    }
    return {"point": point, "q_low": q_low, "q_high": q_high, "metrics": metrics}


def noise_floor_mape(sigma: float, seed: int, n: int = 200_000) -> float:
    """Expected MAPE of a perfect model on data with this multiplicative noise."""
    rng = np.random.default_rng(seed)
    eps = rng.lognormal(0.0, sigma, n)
    return float(np.mean(np.abs(eps - 1.0)) * 100)


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------

def _comparable_samples(df: pd.DataFrame, per_city: int, seed: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for city, g in df.groupby("City"):
        sample = g.sample(n=min(per_city, len(g)), random_state=seed)
        out[city] = [
            {
                "City": str(r.City),
                "Locality": str(r.Locality),
                "BHK": int(r.BHK),
                "Area_SqFt": float(r.Area_SqFt),
                "Price_INR": float(r.Price_INR),
                "Price_per_sqft": float(r.Price_per_sqft),
                "Construction_Status": str(r.Construction_Status),
                "Property_Type": str(r.Property_Type),
            }
            for r in sample.itertuples()
        ]
    return out


def build_bundle(df: pd.DataFrame, markets: MarketIndex, data_meta: dict, seed: int) -> dict:
    fitted = fit_models(df, seed)
    metrics = fitted["metrics"]
    if data_meta["kind"] == "synthetic":
        metrics["noise_floor_mape_pct"] = noise_floor_mape(SYNTHETIC_NOISE_SIGMA, seed)

    markets_payload = [
        {
            "name": c.name,
            "state": c.state,
            "base_psf": c.base_psf,
            "source": c.source,
            "localities": [
                {"name": l.name, "state": l.state, "lat": l.lat, "lon": l.lon, "premium": l.premium}
                for l in c.localities
            ],
        }
        for c in markets.cities.values()
    ]

    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "model_name": "Voting(RandomForest+HistGB) on log psf, P10/P90 quantile GBMs",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "data": data_meta,
        "metrics": metrics,
        "features": {"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES},
        "point_model": fitted["point"],
        "q_low_model": fitted["q_low"],
        "q_high_model": fitted["q_high"],
        "markets": markets_payload,
        "market_provenance": markets.provenance,
        "markets_sha256": markets_fingerprint(),
        "property_types": PROPERTY_TYPES,
        "furnishing_options": FURNISHING_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "comparables": _comparable_samples(df, per_city=60, seed=seed),
        "macro_news_events": HISTORICAL_NEWS_EVENTS,
    }


def train(csv_path: Path | None, rows: int, seed: int, out: Path) -> dict:
    markets = load_markets()
    if csv_path is None:
        df = generate_synthetic_dataset(markets, rows, seed)
        data_meta = {
            "kind": "synthetic",
            "source": "backend/data/markets.json (generator, noise sigma "
                      f"{SYNTHETIC_NOISE_SIGMA})",
            "rows": int(len(df)),
            "provenance": "Synthetic listings generated from indicative market benchmarks. "
                          "Not transaction data. Metrics measure fit to the generator, "
                          "not accuracy against the real market.",
        }
    else:
        df, drop_report = load_csv_dataset(csv_path, markets)
        data_meta = {
            "kind": "csv",
            "source": str(csv_path.name),
            "rows": int(len(df)),
            "provenance": f"Operator-supplied data from {csv_path.name}. This software does not "
                          "verify its origin or quality; accuracy depends on the file.",
            "cleaning": drop_report,
        }

    log.info("Training on %d rows (%s)", len(df), data_meta["kind"])
    bundle = build_bundle(df, markets, data_meta, seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out, compress=3)
    log.info("Wrote %s", out)
    return bundle


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train the GrihaValue model")
    parser.add_argument("--csv", type=Path, default=None, help="Real transactions CSV")
    parser.add_argument("--rows", type=int, default=25_000, help="Synthetic rows (no --csv)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=MODEL_BUNDLE_PATH)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    bundle = train(args.csv, args.rows, args.seed, args.out)
    print(json.dumps({"data": bundle["data"], "metrics": bundle["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
