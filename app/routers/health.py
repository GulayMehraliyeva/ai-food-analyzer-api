import time

from fastapi import APIRouter

from app.config import API_PREFIX, API_VERSION
from app.errors import success_response
from app.store import store, utc_now_iso

router = APIRouter(prefix=API_PREFIX, tags=["System"])
_STARTED = time.monotonic()


@router.get("/health", summary="Health check")
async def health():
    return success_response(
        "API is running.",
        {
            "status": "ok",
            "version": API_VERSION,
            "time": utc_now_iso(),
            "uptimeSeconds": int(time.monotonic() - _STARTED),
            "mealsInStore": store.count(),
            "storage": "in-memory mock data (resets on restart)",
        },
    )
