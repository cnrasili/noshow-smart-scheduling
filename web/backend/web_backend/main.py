import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from web_backend import appointments, auth, doctors, internal_accounts, public, slots

app = FastAPI(title="Appointment Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic hardening headers on every response; the API serves JSON only
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(internal_accounts.router)
app.include_router(public.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
