"""Feature layout shared by training and inference. Keep these in one place."""

from __future__ import annotations

import pandas as pd

NUMERIC_FEATURES: list[str] = [
    "BHK",
    "Area_SqFt",
    "Bathrooms",
    "Age_Years",
    "Parking",
    "Latitude",
    "Longitude",
]
CATEGORICAL_FEATURES: list[str] = [
    "City",
    "Locality",
    "State",
    "Property_Type",
    "Furnishing",
    "Construction_Status",
]
ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

PROPERTY_TYPES: list[str] = ["Apartment", "Builder Floor", "Independent Villa", "Penthouse"]
FURNISHING_OPTIONS: list[str] = ["Unfurnished", "Semi-Furnished", "Fully Furnished"]
STATUS_OPTIONS: list[str] = ["Ready to Move", "Under Construction"]


def build_frame(rows: list[dict]) -> pd.DataFrame:
    """Return a frame with exactly ALL_FEATURES in a stable column order."""
    df = pd.DataFrame(rows)
    missing = [c for c in ALL_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    return df[ALL_FEATURES]
