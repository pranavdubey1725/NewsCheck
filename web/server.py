"""Deployment entry point: serves the frontend and mounts the existing newscheck API.

The project code is untouched. The existing app (newscheck.api:app) is mounted under
/api, so POST /api/check streams the same Server-Sent Events as POST /check does locally.

Run:  uv run uvicorn web.server:app --host 0.0.0.0 --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from newscheck.api import app as newscheck_api

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="newscheck web", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.mount("/api", newscheck_api)                                  # /api/check, /api/docs
app.mount("/", StaticFiles(directory=STATIC, html=True), name="web")
