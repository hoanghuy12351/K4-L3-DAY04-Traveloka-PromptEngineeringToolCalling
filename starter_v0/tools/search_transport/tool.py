from __future__ import annotations

from typing import Any

from tools._travel_shared import canonical_city, load_travel_data, parse_iso_date, structured_error, valid_positive_int


def search_transport(
    origin: str,
    destination: str,
    travel_date: str,
    passengers: int,
    mode: str = "all",
    max_price: int | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Search local transport options; the supplied date is request context only."""
    tool = "search_transport"
    origin_code = canonical_city(origin)
    destination_code = canonical_city(destination)
    if not origin_code:
        return structured_error(tool, "unknown_origin", "origin must be a supported canonical city code or alias.")
    if not destination_code:
        return structured_error(tool, "unknown_destination", "destination must be a supported canonical city code or alias.")
    if not parse_iso_date(travel_date):
        return structured_error(tool, "invalid_travel_date", "travel_date must use YYYY-MM-DD.")
    if not valid_positive_int(passengers):
        return structured_error(tool, "invalid_passengers", "passengers must be a positive integer.")
    if not isinstance(mode, str) or mode.lower() not in {"all", "flight", "train", "bus"}:
        return structured_error(tool, "invalid_mode", "mode must be all, flight, train, or bus.")
    if max_price is not None and (not isinstance(max_price, int) or isinstance(max_price, bool) or max_price < 0):
        return structured_error(tool, "invalid_max_price", "max_price must be a non-negative integer.")
    if not valid_positive_int(top_k):
        return structured_error(tool, "invalid_top_k", "top_k must be a positive integer.")

    normalized_mode = mode.lower()
    dataset = load_travel_data("transport.json")
    matches = [
        option
        for option in dataset["options"]
        if option["origin"] == origin_code
        and option["destination"] == destination_code
        and option["seats"] >= passengers
        and (normalized_mode == "all" or option["mode"] == normalized_mode)
        and (max_price is None or option["price"] <= max_price)
    ]
    matches.sort(key=lambda item: (item["price"], item["option_id"]))
    return {
        "tool": tool,
        "fictional": True,
        "currency": dataset.get("currency", "VND"),
        "source": "local_mock_travel_data",
        "travel_date": travel_date,
        "notice": "The date is request context; this static mock data has no date-specific inventory.",
        "results": matches[:top_k],
    }
