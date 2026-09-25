# Overbooking Service

Decision service behind the booking application. It serves the no-show model, decides slot-level overbooking, sends confirmation and reminder messages, and reports schedule KPIs.

## Scope

- REST model-serving API called at booking time
- Rule engine for slot-level overbooking
- Scheduled confirmation and reminder jobs
- Logging for the reminder A/B comparison
- KPI dashboard: utilization, idle time, overtime

## Endpoints

See the [API contract](../docs/api-contract.md).

## Setup

To be added.
