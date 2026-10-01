from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from overbooking_service import booking, predict
from overbooking_service.config import settings
from overbooking_service.predictor import Predictor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.predictor = Predictor.load(settings.model_dir)
    yield


app = FastAPI(title="Overbooking Service", lifespan=lifespan)
app.include_router(predict.router)
app.include_router(booking.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
