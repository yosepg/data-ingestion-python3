# ── Data Ingestion Pipeline Service ─────────────────────────────────────────
FROM python:3.12-slim

# Build-time deps for psycopg2 compilation (slim image doesn't have them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd --create-home appuser

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Give ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# gunicorn with uvicorn worker class is required to serve FastAPI (ASGI)
# Module name is main.py → main:app   (NOT app:app)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", \
    "-k", "uvicorn.workers.UvicornWorker", "main:app"]
