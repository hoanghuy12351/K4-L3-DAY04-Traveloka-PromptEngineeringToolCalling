from __future__ import annotations

from typing import Any

from tools._travel_shared import load_travel_data, structured_error


def search_destinations(
    interests: list[str],
    budget_level: str,
    top_k: int = 5,
    region: str | None = None,
) -> dict[str, Any]:
    """Find deterministic destination recommendations from the mock catalog."""
    tool = "search_destinations"
    if not isinstance(interests, list) or not interests or not all(isinstance(item, str) and item.strip() for item in interests):
        return structured_error(tool, "invalid_interests", "interests must be a non-empty list of strings.")
    if not isinstance(budget_level, str) or not budget_level.strip():
        return structured_error(tool, "invalid_budget_level", "budget_level must be a non-empty string.")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        return structured_error(tool, "invalid_top_k", "top_k must be a positive integer.")
    if region is not None and (not isinstance(region, str) or not region.strip()):
        return structured_error(tool, "invalid_region", "region must be a non-empty string when supplied.")

    requested_interests = {item.strip().lower() for item in interests}
    normalized_budget = budget_level.strip().lower()
    normalized_region = region.strip().lower() if region else None
    dataset = load_travel_data("destinations.json")
    matches = [
        destination
        for destination in dataset["destinations"]
        if requested_interests.issubset(set(destination["interests"]))
        and normalized_budget in destination["budget_levels"]
        and (normalized_region is None or destination["region"] == normalized_region)
    ]
    matches.sort(key=lambda item: item["code"])
    return {
        "tool": tool,
        "fictional": True,
        "currency": dataset.get("currency", "VND"),
        "source": "local_mock_travel_data",
        "results": matches[:top_k],
    }
