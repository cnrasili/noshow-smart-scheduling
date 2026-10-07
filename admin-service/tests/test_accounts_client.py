import io
import json
from urllib.error import HTTPError, URLError

import pytest

from admin_service import accounts_client
from admin_service.accounts_client import AccountRejected, AccountsClient, AccountsUnavailable


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def answer(monkeypatch: pytest.MonkeyPatch, result) -> list:
    """Replace urlopen; result is a response body or an exception to raise."""
    sent = []

    def fake_urlopen(request, timeout):
        sent.append(request)
        if isinstance(result, Exception):
            raise result
        return Response(json.dumps(result).encode() if result is not None else b"")

    monkeypatch.setattr(accounts_client, "urlopen", fake_urlopen)
    return sent


def http_error(status: int, body: dict) -> HTTPError:
    return HTTPError("url", status, "error", {}, io.BytesIO(json.dumps(body).encode()))


def test_request_carries_the_service_token(monkeypatch):
    sent = answer(monkeypatch, {"account_id": 1})
    client = AccountsClient("http://web-backend:8000/", "secret")
    assert client.create_patient({"full_name": "A"}) == {"account_id": 1}
    request = sent[0]
    assert request.full_url == "http://web-backend:8000/internal/accounts/patients"
    assert request.get_method() == "POST"
    assert request.get_header("X-internal-token") == "secret"
    assert json.loads(request.data) == {"full_name": "A"}


def test_password_reset_has_no_body_in_the_answer(monkeypatch):
    sent = answer(monkeypatch, None)
    AccountsClient("http://web-backend:8000", "secret").reset_password(7, "new password")
    assert sent[0].full_url.endswith("/internal/accounts/7/password")
    assert sent[0].get_method() == "PUT"


def test_without_token_nothing_is_sent(monkeypatch):
    sent = answer(monkeypatch, {})
    client = AccountsClient("http://web-backend:8000", "")
    assert not client.enabled
    with pytest.raises(AccountsUnavailable):
        client.create_doctor({})
    assert sent == []


@pytest.mark.parametrize(
    ("error", "expected", "message"),
    [
        (http_error(409, {"detail": "Email already in use"}), AccountRejected, "Email already"),
        (
            http_error(422, {"detail": [{"loc": ["body", "national_id"], "msg": "Invalid"}]}),
            AccountRejected,
            "national_id: Invalid",
        ),
        (http_error(401, {"detail": "Invalid service token"}), AccountsUnavailable, "401"),
        (http_error(503, {"detail": "Internal API is disabled"}), AccountsUnavailable, "503"),
        (URLError("connection refused"), AccountsUnavailable, "connection refused"),
    ],
)
def test_errors(monkeypatch, error, expected, message):
    answer(monkeypatch, error)
    with pytest.raises(expected, match=message):
        AccountsClient("http://web-backend:8000", "secret").create_patient({})
