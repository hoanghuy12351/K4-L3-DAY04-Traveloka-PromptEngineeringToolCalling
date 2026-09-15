from __future__ import annotations

from typing import Any

from tools._travel_shared import structured_error, valid_nonnegative_number, valid_positive_int


def calculate_trip_budget(
    transport_cost_per_person: int,
    hotel_price_per_night: int,
    nights: int,
    attraction_cost_per_person: int,
    daily_food_cost_per_person: int,
    days: int,
    travelers: int,
) -> dict[str, Any]:
    """Calculate a deterministic budget using the supplied classroom inputs."""
    tool = "calculate_trip_budget"
    costs = {
        "transport_cost_per_person": transport_cost_per_person,
        "hotel_price_per_night": hotel_price_per_night,
        "attraction_cost_per_person": attraction_cost_per_person,
        "daily_food_cost_per_person": daily_food_cost_per_person,
    }
    if any(not valid_nonnegative_number(value) for value in costs.values()):
        return structured_error(tool, "invalid_cost", "All cost values must be non-negative numbers.")
    if not isinstance(nights, int) or isinstance(nights, bool) or nights < 0:
        return structured_error(tool, "invalid_nights", "nights must be a non-negative integer.")
    if not valid_positive_int(days):
        return structured_error(tool, "invalid_days", "days must be a positive integer.")
    if not valid_positive_int(travelers):
        return structured_error(tool, "invalid_travelers", "travelers must be a positive integer.")

    transport_total = transport_cost_per_person * travelers
    hotel_total = hotel_price_per_night * nights
    attraction_total = attraction_cost_per_person * travelers
    food_total = daily_food_cost_per_person * days * travelers
    total = transport_total + hotel_total + attraction_total + food_total
    return {
        "tool": tool,
        "fictional": True,
        "currency": "VND",
        "travelers": travelers,
        "days": days,
        "nights": nights,
        "breakdown": {
            "transport": transport_total,
            "hotel": hotel_total,
            "attractions": attraction_total,
            "food": food_total,
        },
        "total": total,
    }
