"""Deployment entry point: serves the frontend and mounts the existing newscheck API.

The project code is untouched. The existing app (newscheck.api:app) is mounted under
/api, so POST /api/check streams the same Server-Sent Events as POST /check does locally.

Run:  uv run uvicorn web.server:app --host 0.0.0.0 --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastembed import TextEmbedding

from newscheck.api import app as newscheck_api

# fastembed embeds 256 passages per batch by default, which peaks near 1.9 GB of RAM
# on a real check. Batches of 8 peak under 300 MB at the same speed, so the app fits
# on a 512 MB instance. (Long term this belongs in newscheck/embeddings.py.)
_passage_embed = TextEmbedding.passage_embed


def _passage_embed_small_batches(self, texts, **kwargs):
    kwargs.setdefault("batch_size", 8)
    return _passage_embed(self, texts, **kwargs)


TextEmbedding.passage_embed = _passage_embed_small_batches

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="newscheck web", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.mount("/api", newscheck_api)                                  # /api/check, /api/docs
app.mount("/", StaticFiles(directory=STATIC, html=True), name="web")
