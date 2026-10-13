"""Quality gates on the shipped bundle. These fail if a retrain makes the model worse."""

from backend.model import get_bundle


def test_model_beats_locality_median_baseline():
    m = get_bundle()["metrics"]
    assert m["mape_pct"] < m["baseline_locality_median_mape_pct"]


def test_model_is_within_reasonable_distance_of_noise_floor():
    m = get_bundle()["metrics"]
    if "noise_floor_mape_pct" in m:
        assert m["mape_pct"] < m["noise_floor_mape_pct"] * 1.35


def test_interval_coverage_not_wildly_off_target():
    m = get_bundle()["metrics"]
    assert abs(m["interval_coverage_pct"] - m["interval_target_pct"]) < 15


def test_bundle_markets_match_markets_json():
    from backend.model import markets_fingerprint
    assert get_bundle().get("markets_sha256") == markets_fingerprint()
