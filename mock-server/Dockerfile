# ── Mock Customer Data Server ────────────────────────────────────────────────
FROM python:3.12-slim

# Install curl for the Docker healthcheck (python:3.12-slim ships without it)
RUN apt-get update && apt-get install -y --no-install-recommends \
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

EXPOSE 5000

# Use gunicorn for production-quality serving
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
