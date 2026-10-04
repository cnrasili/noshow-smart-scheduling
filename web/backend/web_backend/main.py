import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web_backend import auth, slots

app = FastAPI(title="Appointment Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(slots.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
