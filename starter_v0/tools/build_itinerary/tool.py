from __future__ import annotations

from datetime import timedelta
from typing import Any

from tools._travel_shared import canonical_city, load_travel_data, parse_iso_date, structured_error, valid_positive_int


def build_itinerary(
    destination: str,
    start_date: str,
    days: int,
    travelers: int,
    interests: list[str],
    daily_budget: int | None = None,
) -> dict[str, Any]:
    """Build a deterministic day-by-day plan using only mock attractions."""
    tool = "build_itinerary"
    destination_code = canonical_city(destination)
    start = parse_iso_date(start_date)
    if not destination_code:
        return structured_error(tool, "unknown_destination", "destination must be a supported canonical city code or alias.")
    if not start:
        return structured_error(tool, "invalid_start_date", "start_date must use YYYY-MM-DD.")
    if not valid_positive_int(days):
        return structured_error(tool, "invalid_days", "days must be a positive integer.")
    if not valid_positive_int(travelers):
        return structured_error(tool, "invalid_travelers", "travelers must be a positive integer.")
    if not isinstance(interests, list) or not interests or not all(isinstance(item, str) and item.strip() for item in interests):
        return structured_error(tool, "invalid_interests", "interests must be a non-empty list of strings.")
    if daily_budget is not None and (not isinstance(daily_budget, int) or isinstance(daily_budget, bool) or daily_budget < 0):
        return structured_error(tool, "invalid_daily_budget", "daily_budget must be a non-negative integer.")

    requested_interests = {item.strip().lower() for item in interests}
    dataset = load_travel_data("attractions.json")
    candidates = [item for item in dataset["attractions"] if item["destination"] == destination_code]
    candidates.sort(key=lambda item: (-len(requested_interests.intersection(item["interests"])), item["attraction_id"], item["name"]))
    matching_candidates = [item for item in candidates if requested_interests.intersection(item["interests"])]
    ranked_candidates = matching_candidates or candidates
    if daily_budget is not None:
        ranked_candidates = [item for item in ranked_candidates if item["price"] * travelers <= daily_budget]

    itinerary: list[dict[str, Any]] = []
    for day_index in range(days):
        selected = ranked_candidates[day_index % len(ranked_candidates)] if ranked_candidates else None
        itinerary.append({
            "day": day_index + 1,
            "date": (start + timedelta(days=day_index)).isoformat(),
            "attractions": [selected] if selected else [],
            "attraction_cost_for_travelers": selected["price"] * travelers if selected else 0,
        })
    return {
        "tool": tool,
        "fictional": True,
        "currency": dataset.get("currency", "VND"),
        "source": "local_mock_travel_data",
        "destination": destination_code,
        "travelers": travelers,
        "notice": "This is a fictional classroom itinerary built only from local attraction records.",
        "itinerary": itinerary,
    }
