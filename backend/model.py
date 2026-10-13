"""Runtime model loading and inference.

The bundle is loaded once at startup. Missing or incompatible bundles raise a
typed error that the API maps to HTTP 503. There is no silent fallback.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

from backend.config import BUNDLE_SCHEMA_VERSION, MODEL_BUNDLE_PATH
from backend.features import ALL_FEATURES

log = logging.getLogger("grihavalue.model")

REQUIRED_KEYS = {
    "schema_version", "model_name", "trained_at", "data", "metrics",
    "point_model", "q_low_model", "q_high_model", "markets",
    "property_types", "furnishing_options", "status_options", "comparables",
}


class ModelUnavailable(RuntimeError):
    """Raised when the bundle is missing, malformed, or the wrong schema."""


@dataclass(frozen=True)
class Prediction:
    psf: float
    psf_low: float
    psf_high: float


@lru_cache(maxsize=1)
def get_bundle() -> dict[str, Any]:
    """Load and validate the bundle once. Thread-safe via lru_cache's lock."""
    path = MODEL_BUNDLE_PATH
    if not path.exists():
        raise ModelUnavailable(
            f"Model bundle not found at {path}. Run: python -m backend.train"
        )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bundle = joblib.load(path)
    if not isinstance(bundle, dict):
        raise ModelUnavailable("Model bundle is not a dict. Re-run: python -m backend.train")

    missing = REQUIRED_KEYS - bundle.keys()
    if missing:
        raise ModelUnavailable(f"Bundle missing keys {sorted(missing)}. Re-run training.")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise ModelUnavailable(
            f"Bundle schema v{bundle['schema_version']} != expected v{BUNDLE_SCHEMA_VERSION}. "
            "Re-run training."
        )
    trained_with = bundle.get("sklearn_version")
    if trained_with != sklearn.__version__:
        log.warning(
            "Bundle trained with scikit-learn %s, running %s. "
            "Predictions may differ; retrain to remove this warning.",
            trained_with, sklearn.__version__,
        )
    for w in caught:
        log.debug("joblib warning during load: %s", w.message)
    current = markets_fingerprint()
    if bundle.get("markets_sha256") not in (None, current):
        log.warning("markets.json changed since the bundle was trained. Re-run: python -m backend.train")
    return bundle


def markets_fingerprint() -> str:
    """SHA-256 of markets.json. Stored in the bundle to detect stale training."""
    import hashlib
    from backend.config import MARKETS_PATH
    return hashlib.sha256(MARKETS_PATH.read_bytes()).hexdigest()


def bundle_status() -> dict[str, Any]:
    """Health view of the model. Never raises."""
    try:
        b = get_bundle()
    except ModelUnavailable as exc:
        return {"loaded": False, "reason": str(exc)}
    return {
        "loaded": True,
        "model_name": b["model_name"],
        "trained_at": b["trained_at"],
        "sklearn_version": b.get("sklearn_version"),
        "schema_version": b["schema_version"],
        "data": b["data"],
        "metrics": b["metrics"],
        "markets_current": b.get("markets_sha256") in (None, markets_fingerprint()),
    }


def predict(input_df: pd.DataFrame) -> Prediction:
    """Predict price per sq.ft. with an interval for one row."""
    if list(input_df.columns) != ALL_FEATURES:
        raise ValueError(f"input columns must be exactly {ALL_FEATURES}")
    b = get_bundle()
    psf = float(b["point_model"].predict(input_df)[0])
    low = float(np.exp(b["q_low_model"].predict(input_df)[0]))
    high = float(np.exp(b["q_high_model"].predict(input_df)[0]))
    # Quantile models are fitted independently, so enforce ordering.
    low, high = min(low, psf), max(high, psf)
    return Prediction(psf=psf, psf_low=low, psf_high=high)
