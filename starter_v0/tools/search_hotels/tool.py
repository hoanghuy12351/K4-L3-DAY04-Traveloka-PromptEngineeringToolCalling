from __future__ import annotations

from typing import Any

from tools._travel_shared import canonical_city, load_travel_data, parse_iso_date, structured_error, valid_positive_int


def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    guests: int,
    max_price_per_night: int | None = None,
    min_rating: float | None = None,
    amenities: list[str] | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Search deterministic hotel records without claiming date-specific availability."""
    tool = "search_hotels"
    destination_code = canonical_city(destination)
    check_in_date = parse_iso_date(check_in)
    check_out_date = parse_iso_date(check_out)
    if not destination_code:
        return structured_error(tool, "unknown_destination", "destination must be a supported canonical city code or alias.")
    if not check_in_date or not check_out_date:
        return structured_error(tool, "invalid_dates", "check_in and check_out must use YYYY-MM-DD.")
    if check_out_date <= check_in_date:
        return structured_error(tool, "invalid_date_range", "check_out must be after check_in.")
    if not valid_positive_int(guests):
        return structured_error(tool, "invalid_guests", "guests must be a positive integer.")
    if max_price_per_night is not None and (not isinstance(max_price_per_night, int) or isinstance(max_price_per_night, bool) or max_price_per_night < 0):
        return structured_error(tool, "invalid_max_price_per_night", "max_price_per_night must be a non-negative integer.")
    if min_rating is not None and (not isinstance(min_rating, (int, float)) or isinstance(min_rating, bool) or min_rating < 0):
        return structured_error(tool, "invalid_min_rating", "min_rating must be a non-negative number.")
    if amenities is not None and (not isinstance(amenities, list) or not all(isinstance(item, str) and item.strip() for item in amenities)):
        return structured_error(tool, "invalid_amenities", "amenities must be a list of strings when supplied.")
    if not valid_positive_int(top_k):
        return structured_error(tool, "invalid_top_k", "top_k must be a positive integer.")

    requested_amenities = {item.strip().lower() for item in amenities or []}
    dataset = load_travel_data("hotels.json")
    matches = [
        hotel
        for hotel in dataset["hotels"]
        if hotel["destination"] == destination_code
        and hotel["available"]
        and hotel["max_guests"] >= guests
        and (max_price_per_night is None or hotel["price_per_night"] <= max_price_per_night)
        and (min_rating is None or hotel["rating"] >= min_rating)
        and requested_amenities.issubset(set(hotel["amenities"]))
    ]
    matches.sort(key=lambda item: (item["price_per_night"], item["hotel_id"]))
    return {
        "tool": tool,
        "fictional": True,
        "currency": dataset.get("currency", "VND"),
        "source": "local_mock_travel_data",
        "check_in": check_in,
        "check_out": check_out,
        "notice": "Dates are request context; availability is a static fictional dataset field.",
        "results": matches[:top_k],
    }
