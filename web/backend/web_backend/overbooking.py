# Client for the overbooking service; the contract is in docs/api-contract.md
import logging
import os
from dataclasses import dataclass
from datetime import date

import httpx2

OVERBOOKING_SERVICE_URL = os.getenv("OVERBOOKING_SERVICE_URL", "http://localhost:8001")
# Booking must not hang on the service; on timeout the booking falls back to empty slots only
TIMEOUT_SECONDS = 3.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BookingDecision:
    allow: bool
    overbook: bool
    p_noshow: float
    reason: str


class OverbookingClient:
    def __init__(
        self,
        base_url: str = OVERBOOKING_SERVICE_URL,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self._http = httpx2.Client(base_url=base_url, timeout=TIMEOUT_SECONDS, transport=transport)

    def booking_decision(
        self, patient_id: int, slot_id: int, booking_date: date
    ) -> BookingDecision | None:
        """Ask whether the patient may be booked into the slot.

        Returns None when the service cannot answer: timeout, connection error, an error
        status such as 503, or an unexpected response body.
        """
        try:
            response = self._http.post(
                "/booking-decision",
                json={
                    "patient_id": patient_id,
                    "slot_id": slot_id,
                    "booking_date": booking_date.isoformat(),
                },
            )
            response.raise_for_status()
            body = response.json()
            return BookingDecision(
                allow=bool(body["allow"]),
                overbook=bool(body["overbook"]),
                p_noshow=float(body["p_noshow"]),
                reason=str(body["reason"]),
            )
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            logger.warning("Booking decision for slot %s unavailable: %r", slot_id, error)
            return None


_client: OverbookingClient | None = None


def get_overbooking_client() -> OverbookingClient:
    global _client
    if _client is None:
        _client = OverbookingClient()
    return _client
