from __future__ import annotations

import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from tools._shared import ROOT


TRAVEL_DATA_DIR = ROOT / "travel_data"


def structured_error(tool: str, error: str, message: str, **details: Any) -> dict[str, Any]:
    """Return ordinary validation failures in one stable response shape."""
    return {"tool": tool, "error": error, "message": message, **details}


def load_travel_data(filename: str) -> dict[str, Any]:
    """Load one local, fictional travel dataset."""
    path = TRAVEL_DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    """Normalize accents and punctuation for Vietnamese aliases."""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(without_marks.replace("đ", "d").replace("-", " ").replace(".", " ").split())


_CITY_ALIASES = {
    "HAN": {"han", "ha noi", "hanoi"},
    "SGN": {"sgn", "tp ho chi minh", "ho chi minh", "hcm", "sai gon", "saigon"},
    "DAD": {"dad", "da nang"},
    "DLI": {"dli", "da lat"},
    "PQC": {"pqc", "phu quoc"},
}


def canonical_city(value: str) -> str | None:
    """Convert supported city names and codes to an evaluation-safe city code."""
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = normalize_text(value)
    for code, aliases in _CITY_ALIASES.items():
        if normalized in aliases:
            return code
    return None


def parse_iso_date(value: str) -> date | None:
    """Parse an ISO date without accepting locale-dependent formats."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def valid_positive_int(value: Any) -> bool:
    """Identify positive integers while excluding booleans."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def valid_nonnegative_number(value: Any) -> bool:
    """Identify non-negative numeric values while excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
