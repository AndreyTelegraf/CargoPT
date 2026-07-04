from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.web_requests import router as web_requests_router


app = FastAPI(title="CargoPT API")
app.include_router(web_requests_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@app.get("/track/{tracking_token}", include_in_schema=False)
async def tracking_page(tracking_token: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "track" / "index.html")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
