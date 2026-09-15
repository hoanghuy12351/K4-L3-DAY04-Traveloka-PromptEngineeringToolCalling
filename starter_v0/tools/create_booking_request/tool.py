from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from tools._shared import ROOT
from tools._travel_shared import load_travel_data, parse_iso_date, structured_error, valid_positive_int


BOOKING_REQUEST_DIR = ROOT / "booking_requests"


def create_booking_request(
    booking_type: str,
    option_id: str,
    start_date: str,
    end_date: str | None = None,
    travelers: int = 1,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Persist a simulated booking request only after exact explicit confirmation."""
    tool = "create_booking_request"
    if confirmed is not True:
        return {
            "tool": tool,
            "status": "needs_confirmation",
            "message": "Create this mock request only after explicit confirmation of the exact current payload.",
        }
    if not isinstance(booking_type, str) or booking_type.lower() not in {"hotel", "transport"}:
        return structured_error(tool, "invalid_booking_type", "booking_type must be hotel or transport.")
    if not isinstance(option_id, str) or not option_id.strip():
        return structured_error(tool, "invalid_option_id", "option_id must be a non-empty string.")
    if not parse_iso_date(start_date):
        return structured_error(tool, "invalid_start_date", "start_date must use YYYY-MM-DD.")
    if end_date is not None and not parse_iso_date(end_date):
        return structured_error(tool, "invalid_end_date", "end_date must use YYYY-MM-DD when supplied.")
    if end_date is not None and parse_iso_date(end_date) <= parse_iso_date(start_date):
        return structured_error(tool, "invalid_date_range", "end_date must be after start_date.")
    if not valid_positive_int(travelers):
        return structured_error(tool, "invalid_travelers", "travelers must be a positive integer.")

    normalized_type = booking_type.lower()
    normalized_option_id = option_id.strip().upper()
    if normalized_type == "hotel":
        if end_date is None:
            return structured_error(tool, "missing_end_date", "Hotel booking requests require end_date.")
        records = load_travel_data("hotels.json")["hotels"]
        record = next((item for item in records if item["hotel_id"] == normalized_option_id), None)
        if record is None:
            return structured_error(tool, "unknown_option_id", "No hotel record matches option_id.")
        if not record["available"]:
            return structured_error(tool, "unavailable_option", "This fictional hotel record is marked unavailable.")
        if record["max_guests"] < travelers:
            return structured_error(tool, "insufficient_capacity", "The fictional hotel capacity is lower than travelers.")
    else:
        records = load_travel_data("transport.json")["options"]
        record = next((item for item in records if item["option_id"] == normalized_option_id), None)
        if record is None:
            return structured_error(tool, "unknown_option_id", "No transport record matches option_id.")
        if record["seats"] < travelers:
            return structured_error(tool, "insufficient_capacity", "The fictional transport seats are lower than travelers.")

    now = datetime.now(timezone.utc)
    payload = {
        "booking_type": normalized_type,
        "option_id": normalized_option_id,
        "start_date": start_date,
        "end_date": end_date,
        "travelers": travelers,
        "confirmed": True,
        "fictional": True,
        "source": "local_mock_travel_data",
    }
    seed = f"{now.isoformat()}|{json.dumps(payload, sort_keys=True)}"
    request_id = "MOCK-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10].upper()
    request = {"request_id": request_id, "created_at": now.isoformat(), **payload}
    try:
        BOOKING_REQUEST_DIR.mkdir(parents=True, exist_ok=True)
        path = BOOKING_REQUEST_DIR / f"{request_id}.json"
        path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        return structured_error(tool, "write_error", str(exc))
    return {
        "tool": tool,
        "status": "created_mock_request",
        "request_id": request_id,
        "message": "Simulated request created. No real reservation or payment was made.",
        "fictional": True,
        "path": str(path),
        "request": request,
    }
