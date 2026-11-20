import logging

#from app.routers import greeting
from app.routers import greeting, meals

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import API_PREFIX, PROJECT_NAME
from app.errors import register_exception_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title=f"{PROJECT_NAME} API",
    version="1.0.0",
    description=(
        "Prototype REST API with mocked in-memory data. "
        "Use `Authorization: Bearer user-a-token | user-b-token | admin-token`."
    ),
)

register_exception_handlers(app)
app.include_router(greeting.router)
app.include_router(meals.router)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url=f"{API_PREFIX}/greeting")