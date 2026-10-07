import json
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

TIMEOUT_SECONDS = 5


class OverbookingUnavailable(Exception):
    """Raised when the overbooking service cannot be reached or fails."""


class OverbookingClient:
    """Read-only access to the overbooking service's KPI and A/B endpoints."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except HTTPError as exc:
            # 404 means the doctor has no slots on the date
            if exc.code == 404:
                return None
            raise OverbookingUnavailable(f"{path} returned {exc.code}") from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise OverbookingUnavailable(f"{path} failed: {exc}") from exc

    def kpi(self, doctor_id: int, day: date) -> dict[str, Any] | None:
        """KPIs of a doctor on a date; None if the doctor has no slots on it."""
        return self._get("/kpi", {"doctor_id": doctor_id, "date": day.isoformat()})

    def ab_summary(self, unit: str = "appointment") -> dict[str, Any]:
        summary = self._get("/ab/summary", {"unit": unit})
        if summary is None:
            raise OverbookingUnavailable("/ab/summary returned 404")
        return summary
