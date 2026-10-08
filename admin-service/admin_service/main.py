from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from admin_service import accounts, auth, decisions, pages
from admin_service.config import settings
from admin_service.dependencies import NotLoggedIn
from admin_service.network import AllowedNetworksMiddleware

# No API docs: the admin service has no public API
app = FastAPI(title="Admin Service", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(AllowedNetworksMiddleware, networks=settings.allowed_networks)
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(decisions.router)
app.include_router(accounts.router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.exception_handler(NotLoggedIn)
def to_login(request: Request, exc: NotLoggedIn) -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
