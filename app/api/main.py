from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.web_requests import router as web_requests_router
from app.api.meta_operations import router as meta_operations_router
from app.api.rate_limit import WebRequestRateLimitMiddleware
from app.config import settings


app = FastAPI(title="CargoPT API")
app.add_middleware(
    WebRequestRateLimitMiddleware,
    max_requests=settings.web_request_rate_limit_count,
    window_seconds=settings.web_request_rate_limit_window_seconds,
    max_body_bytes=settings.web_request_max_body_bytes,
)
app.include_router(web_requests_router, prefix="/api/v1")
app.include_router(meta_operations_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@app.get("/track/{tracking_token}", include_in_schema=False)
async def tracking_page(tracking_token: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "track" / "index.html")


@app.get("/en/track/{tracking_token}", include_in_schema=False)
async def tracking_page_en(tracking_token: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "en" / "track" / "index.html")


@app.get("/ru/track/{tracking_token}", include_in_schema=False)
async def tracking_page_ru(tracking_token: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "ru" / "track" / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
