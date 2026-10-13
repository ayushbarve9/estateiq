"""Tests for the financial rules checker and validator."""

import json
import pytest
from backend.rules import (
    RuleValidationError,
    get_rule,
    get_rule_value,
    get_rules,
    load_rules,
    validate_rules_data,
)


def test_real_rules_json_loads_and_validates():
    rules = load_rules()
    assert len(rules) >= 25
    names = {r["name"] for r in rules}
    assert "gst_under_construction_rate" in names
    assert "ltv_tier_1_ratio" in names
    assert "stamp_duty_maharashtra" in names

    for r in rules:
        assert r["name"]
        assert isinstance(r["value"], (int, float))
        assert r["source"], f"Rule {r['name']} has empty source"
        assert r["status"] in ("VERIFIED", "UNVERIFIED")
        assert "last_checked" in r


def test_checker_rejects_missing_source():
    bad_data = [
        {
            "name": "tax_test",
            "value": 0.05,
            "source": "",  # missing source
            "status": "UNVERIFIED",
            "last_checked": "unrecorded",
        }
    ]
    with pytest.raises(RuleValidationError, match="missing a required source"):
        validate_rules_data(bad_data)


def test_checker_rejects_duplicate_name():
    bad_data = [
        {
            "name": "rule_a",
            "value": 0.05,
            "source": "Source 1",
            "status": "VERIFIED",
            "last_checked": "unrecorded",
        },
        {
            "name": "rule_a",  # duplicate
            "value": 0.10,
            "source": "Source 2",
            "status": "VERIFIED",
            "last_checked": "unrecorded",
        },
    ]
    with pytest.raises(RuleValidationError, match="Duplicate rule name"):
        validate_rules_data(bad_data)


@pytest.mark.parametrize("name,value", [
    ("gst_rate", 1.5),              # rate > 1.0
    ("gst_rate", -0.01),            # rate < 0.0
    ("interest_rate_pct", 105.0),   # percentage > 100
    ("interest_rate_pct", -5.0),    # percentage < 0
    ("tenure_min_yrs", 0),          # tenure <= 0
    ("afford_threshold", -500),     # threshold <= 0
])
def test_checker_rejects_number_out_of_range(name, value):
    bad_data = [
        {
            "name": name,
            "value": value,
            "source": "Doc 1",
            "status": "VERIFIED",
            "last_checked": "unrecorded",
        }
    ]
    with pytest.raises(RuleValidationError, match="out of range|must be positive|cannot be negative"):
        validate_rules_data(bad_data)


def test_checker_rejects_invalid_status():
    bad_data = [
        {
            "name": "rule_status",
            "value": 0.05,
            "source": "Source 1",
            "status": "MAYBE_VALID",  # invalid
            "last_checked": "unrecorded",
        }
    ]
    with pytest.raises(RuleValidationError, match="status must be one of"):
        validate_rules_data(bad_data)


def test_checker_rejects_missing_file(tmp_path):
    missing_file = tmp_path / "non_existent_rules.json"
    with pytest.raises(RuleValidationError, match="Rules file not found"):
        load_rules(missing_file)


def test_checker_rejects_malformed_json(tmp_path):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{ broken json", encoding="utf-8")
    with pytest.raises(RuleValidationError, match="Malformed JSON"):
        load_rules(bad_file)


def test_get_rule_and_value():
    rate = get_rule_value("gst_under_construction_rate")
    assert rate == 0.05
    rule = get_rule("gst_under_construction_rate")
    assert rule["status"] == "VERIFIED"
