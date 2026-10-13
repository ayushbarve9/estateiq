"""Rules loader and validator.

Loads financial rules from rules.json and validates them at startup.
Refuses to start the application if any rule is broken (missing source,
duplicate name, invalid status, or number out of range).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"

ALLOWED_STATUSES = {"VERIFIED", "UNVERIFIED"}


class RuleValidationError(ValueError):
    """Raised when the rules file is invalid, broken, or contains out-of-range figures."""
    pass


def validate_rules_data(data: Any) -> list[dict[str, Any]]:
    """Validate a list of rule dictionaries against strict business and provenance checks."""
    if not isinstance(data, list):
        raise RuleValidationError(f"Rules data must be a JSON list, got {type(data).__name__}")

    if not data:
        raise RuleValidationError("Rules list is empty")

    seen_names: set[str] = set()
    validated_rules: list[dict[str, Any]] = []

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise RuleValidationError(f"Rule at index {idx} must be an object/dict")

        name = item.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            raise RuleValidationError(f"Rule at index {idx} is missing a valid 'name'")

        name = name.strip()
        if name in seen_names:
            raise RuleValidationError(f"Duplicate rule name: '{name}'")
        seen_names.add(name)

        if "value" not in item:
            raise RuleValidationError(f"Rule '{name}' is missing 'value'")
        value = item["value"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise RuleValidationError(f"Rule '{name}' value must be a number, got {type(value).__name__}")
        if math.isnan(value) or math.isinf(value):
            raise RuleValidationError(f"Rule '{name}' value cannot be NaN or infinite")

        # Range checks based on rule semantics
        if name.endswith("_pct"):
            if not (0.0 <= value <= 100.0):
                raise RuleValidationError(f"Rule '{name}' percentage value {value} out of range [0, 100]")
        elif "_rate" in name or "_ratio" in name or name.startswith("stamp_duty_"):
            if not (0.0 <= value <= 1.0):
                raise RuleValidationError(f"Rule '{name}' rate/ratio value {value} out of range [0, 1]")
        elif name.endswith("_threshold") or name.endswith("_yrs"):
            if value <= 0:
                raise RuleValidationError(f"Rule '{name}' threshold/years value {value} must be positive (> 0)")
        elif value < 0:
            raise RuleValidationError(f"Rule '{name}' value {value} cannot be negative")

        source = item.get("source")
        if not source or not isinstance(source, str) or not source.strip():
            raise RuleValidationError(f"Rule '{name}' is missing a required source")

        status = item.get("status")
        if status not in ALLOWED_STATUSES:
            raise RuleValidationError(
                f"Rule '{name}' status must be one of {sorted(ALLOWED_STATUSES)}, got '{status}'"
            )

        last_checked = item.get("last_checked")
        if last_checked is None:
            last_checked = "unrecorded"
        elif not isinstance(last_checked, str):
            raise RuleValidationError(f"Rule '{name}' last_checked must be a string or null")

        validated_rules.append({
            "name": name,
            "value": value,
            "source": source.strip(),
            "status": status,
            "last_checked": last_checked,
        })

    return validated_rules


_RULES_CACHE: list[dict[str, Any]] | None = None
_RULES_MAP: dict[str, dict[str, Any]] | None = None


def load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate rules from file. Caches in memory."""
    global _RULES_CACHE, _RULES_MAP
    target_path = path or RULES_PATH
    if not target_path.exists():
        raise RuleValidationError(f"Rules file not found at: {target_path}")

    try:
        raw_text = target_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuleValidationError(f"Malformed JSON in rules file: {exc}") from exc

    rules = validate_rules_data(data)
    _RULES_CACHE = rules
    _RULES_MAP = {r["name"]: r for r in rules}
    return rules


def get_rules() -> list[dict[str, Any]]:
    """Return all validated rules, loading from disk if not yet cached."""
    global _RULES_CACHE
    if _RULES_CACHE is None:
        load_rules()
    return list(_RULES_CACHE)


def get_rule(name: str) -> dict[str, Any]:
    """Retrieve a single rule by name."""
    global _RULES_MAP
    if _RULES_MAP is None:
        load_rules()
    if name not in _RULES_MAP:
        raise KeyError(f"Rule '{name}' not found in rules")
    return _RULES_MAP[name]


def get_rule_value(name: str) -> float | int:
    """Retrieve the numeric value of a rule by name."""
    return get_rule(name)["value"]
