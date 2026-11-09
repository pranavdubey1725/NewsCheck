FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed \
    PATH="/app/.venv/bin:$PATH" \
    PORT=7860

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY web ./web
RUN uv sync --frozen --no-dev

# Download the embedding model at build time so the first check isn't slow.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Hugging Face Spaces runs the container as user 1000.
RUN useradd -m -u 1000 user && chown -R user /app
USER user

EXPOSE 7860

# GROQ_API_KEY and TAVILY_API_KEY must be set as environment variables / secrets on the host.
# PORT defaults to 7860 (Hugging Face); hosts like Render override it.
CMD ["sh", "-c", "uvicorn web.server:app --host 0.0.0.0 --port ${PORT}"]
