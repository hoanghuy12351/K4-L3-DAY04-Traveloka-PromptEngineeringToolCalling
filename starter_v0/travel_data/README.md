# Mock Travel Data

This folder contains fictional, deterministic data for the AI Travel Planner.
Prices are estimates in VND and must not be presented as live prices or real
availability. The data is safe for evaluation and classroom demonstrations.

## Core workflow fixed before v0

Collect missing trip constraints, search the local destination/transport/hotel/
attraction catalog, calculate an estimated budget, build an itinerary, and ask
for explicit confirmation before creating a mock booking request.

## Planned tool contract

| Tool                     | Required inputs                                               | Purpose                                                     |
| ------------------------ | ------------------------------------------------------------- | ----------------------------------------------------------- |
| `clarify`                | `question`                                                    | Ask for missing or renewed confirmation data.               |
| `search_destinations`    | `interests`, `budget_level`                                   | Recommend destinations from the local catalog.              |
| `search_transport`       | `origin`, `destination`, `travel_date`, `passengers`          | Search fictional transport options.                         |
| `search_hotels`          | `destination`, `check_in`, `check_out`, `guests`              | Search fictional accommodation options.                     |
| `search_attractions`     | `destination`, `interests`                                    | Search fictional attractions.                               |
| `calculate_trip_budget`  | cost components, `nights`, `days`, `travelers`                | Calculate a deterministic trip estimate.                    |
| `build_itinerary`        | `destination`, `start_date`, `days`, `travelers`, `interests` | Build a day-by-day itinerary from local data.               |
| `create_booking_request` | booking payload, `confirmed`                                  | Write a mock request only after exact-payload confirmation. |

The evaluation file uses city codes (`HAN`, `SGN`, `DAD`, `DLI`, `PQC`) as
canonical values. A later implementation must keep these tool names and input
conventions aligned across `tools.yaml`, the registry, and tool functions.
