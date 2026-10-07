from collections.abc import Sequence
from ipaddress import ip_address

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from admin_service.config import Network


def is_allowed(host: str | None, networks: Sequence[Network]) -> bool:
    if host is None:
        return False
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in networks)


class AllowedNetworksMiddleware:
    """Reject clients outside the allowed networks before any route runs.

    The direct peer address is used; forwarded headers are ignored, so a client cannot
    claim an internal address.
    """

    def __init__(self, app: ASGIApp, networks: Sequence[Network]) -> None:
        self.app = app
        self.networks = networks

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            client = scope.get("client")
            if not is_allowed(client[0] if client else None, self.networks):
                response = PlainTextResponse(
                    "The admin service is only available from the hospital network.",
                    status_code=403,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
