"""Training pipeline tests. Use small row counts so they run in seconds."""

import numpy as np
import pandas as pd
import pytest

from backend.features import ALL_FEATURES
from backend.markets import load_markets
from backend.train import generate_synthetic_dataset, load_csv_dataset, noise_floor_mape


def test_synthetic_dataset_is_reproducible():
    m = load_markets()
    a = generate_synthetic_dataset(m, 600, seed=7)
    b = generate_synthetic_dataset(m, 600, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_synthetic_dataset_is_plausible():
    df = generate_synthetic_dataset(load_markets(), 2000, seed=1)
    assert set(ALL_FEATURES) <= set(df.columns)
    assert (df["Price_INR"] > 0).all()
    assert df["Price_per_sqft"].between(500, 500_000).all()
    assert df["BHK"].between(1, 5).all()
    assert not ((df["Property_Type"] == "Penthouse") & (df["BHK"] < 2)).any()
    assert not ((df["Construction_Status"] == "Under Construction") & (df["Age_Years"] > 0)).any()


def test_every_locality_present_in_large_sample():
    m = load_markets()
    df = generate_synthetic_dataset(m, 20_000, seed=3)
    seen = set(zip(df["City"], df["Locality"]))
    assert seen == set(m.localities.keys())


def test_noise_floor_is_reasonable():
    floor = noise_floor_mape(0.10, seed=0, n=50_000)
    assert 7.5 < floor < 8.5


def test_csv_loader_rejects_unknown_locality(tmp_path):
    p = tmp_path / "sales.csv"
    rows = [{"City": "Bengaluru", "Locality": "Atlantis Heights", "BHK": 2, "Area_SqFt": 1000,
             "Price_INR": 9_000_000, "Construction_Status": "Ready to Move",
             "Property_Type": "Apartment"}] * 600
    pd.DataFrame(rows).to_csv(p, index=False)
    with pytest.raises(ValueError, match="not in markets.json"):
        load_csv_dataset(p, load_markets())


def test_csv_loader_rejects_missing_columns(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame({"City": ["Bengaluru"]}).to_csv(p, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_csv_dataset(p, load_markets())


def test_csv_loader_drops_bad_rows_and_reports(tmp_path):
    p = tmp_path / "ok.csv"
    good = {"City": "Bengaluru", "Locality": "Whitefield", "BHK": 3, "Area_SqFt": 1500,
            "Price_INR": 15_000_000, "Construction_Status": "Ready to Move",
            "Property_Type": "Apartment"}
    bad = dict(good, Price_INR=-5)
    pd.DataFrame([good] * 600 + [bad] * 10).to_csv(p, index=False)
    df, report = load_csv_dataset(p, load_markets())
    assert report["input_rows"] == 610
    assert report["dropped_rows"] == 10
    assert len(df) == 600
    assert set(df["State"]) == {"Karnataka"}


def test_training_end_to_end_small(tmp_path):
    from backend.train import train
    out = tmp_path / "bundle.joblib"
    bundle = train(csv_path=None, rows=1200, seed=5, out=out)
    assert out.exists()
    m = bundle["metrics"]
    assert 0 < m["mape_pct"] < 100
    assert m["interval_low_q"] < m["interval_high_q"]
    assert bundle["schema_version"] >= 2
    assert bundle["data"]["kind"] == "synthetic"
