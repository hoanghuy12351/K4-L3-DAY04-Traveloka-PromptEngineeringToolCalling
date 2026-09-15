from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .clarify.tool import ask_user
from .build_itinerary.tool import build_itinerary
from .calculate_trip_budget.tool import calculate_trip_budget
from .create_booking_request.tool import create_booking_request
from .search_attractions.tool import search_attractions
from .search_destinations.tool import search_destinations
from .search_hotels.tool import search_hotels
from .search_transport.tool import search_transport


TOOL_FUNCTIONS = {
    "clarify": ask_user,
    "search_destinations": search_destinations,
    "search_transport": search_transport,
    "search_hotels": search_hotels,
    "search_attractions": search_attractions,
    "calculate_trip_budget": calculate_trip_budget,
    "build_itinerary": build_itinerary,
    "create_booking_request": create_booking_request,
}


def load_tool_declarations(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["tools"]


def to_openai_tools(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "type": "function",
        "function": {
            "name": item["name"],
            "description": item.get("description", ""),
            "parameters": item.get("parameters", {"type": "object", "properties": {}}),
        },
    } for item in declarations]
