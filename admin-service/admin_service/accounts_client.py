import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from admin_service.turkish import api_error

TIMEOUT_SECONDS = 10


class AccountsUnavailable(Exception):
    """The internal account API is disabled, rejects the token or cannot be reached."""


class AccountRejected(Exception):
    """The internal account API refused the request; the message explains why in Turkish."""


def _rejection(status: int, body: bytes) -> str:
    """Turkish message for the administrator from the API's error answer."""
    try:
        detail = json.loads(body).get("detail")
    except (ValueError, AttributeError):
        detail = None
    return api_error(status, detail)


class AccountsClient:
    """Client of the web backend's internal account API."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _send(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            raise AccountsUnavailable("INTERNAL_API_TOKEN is not set")
        request = Request(
            f"{self.base_url}/internal/accounts{path}",
            data=json.dumps(body).encode(),
            method=method,
            headers={"Content-Type": "application/json", "X-Internal-Token": self.token},
        )
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            if exc.code in (401, 503):
                raise AccountsUnavailable(f"Internal account API answered {exc.code}") from exc
            raise AccountRejected(_rejection(exc.code, exc.read())) from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise AccountsUnavailable(f"Internal account API failed: {exc}") from exc

    def create_patient(self, patient: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/patients", patient)

    def create_doctor(self, doctor: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/doctors", doctor)

    def reset_password(self, account_id: int, password: str) -> None:
        self._send("PUT", f"/{account_id}/password", {"password": password})
