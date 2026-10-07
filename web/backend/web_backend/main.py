import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web_backend import appointments, auth, doctors, internal_accounts, slots

app = FastAPI(title="Appointment Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(internal_accounts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
