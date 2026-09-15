from __future__ import annotations

from typing import Any

from tools._travel_shared import canonical_city, load_travel_data, structured_error, valid_positive_int


def search_attractions(
    destination: str,
    interests: list[str],
    max_price: int | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Find local fictional attractions ranked by matching interests."""
    tool = "search_attractions"
    destination_code = canonical_city(destination)
    if not destination_code:
        return structured_error(tool, "unknown_destination", "destination must be a supported canonical city code or alias.")
    if not isinstance(interests, list) or not interests or not all(isinstance(item, str) and item.strip() for item in interests):
        return structured_error(tool, "invalid_interests", "interests must be a non-empty list of strings.")
    if max_price is not None and (not isinstance(max_price, int) or isinstance(max_price, bool) or max_price < 0):
        return structured_error(tool, "invalid_max_price", "max_price must be a non-negative integer.")
    if not valid_positive_int(top_k):
        return structured_error(tool, "invalid_top_k", "top_k must be a positive integer.")

    requested_interests = {item.strip().lower() for item in interests}
    dataset = load_travel_data("attractions.json")
    matches = [
        attraction
        for attraction in dataset["attractions"]
        if attraction["destination"] == destination_code
        and requested_interests.intersection(attraction["interests"])
        and (max_price is None or attraction["price"] <= max_price)
    ]
    matches.sort(key=lambda item: (-len(requested_interests.intersection(item["interests"])), item["attraction_id"], item["name"]))
    return {
        "tool": tool,
        "fictional": True,
        "currency": dataset.get("currency", "VND"),
        "source": "local_mock_travel_data",
        "results": matches[:top_k],
    }
