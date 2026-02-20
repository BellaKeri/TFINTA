# ---------------------------------------------------------------------------
# TFINTA Realtime API – Cloud Run container
# ---------------------------------------------------------------------------
# Build:
#   docker build -t tfinta-api .
#
# Run locally:
#   docker run -p 8080:8080 tfinta-api
#
# Deploy to Cloud Run:
#   gcloud builds submit --tag gcr.io/PROJECT_ID/tfinta-api
#   gcloud run deploy tfinta-api \
#       --image gcr.io/PROJECT_ID/tfinta-api \
#       --platform managed \
#       --region REGION \
#       --allow-unauthenticated
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Poetry (locked to a specific version for reproducibility)
RUN pip install --no-cache-dir "poetry>=2.3,<3"

# Copy only dependency-specification files first (Docker cache layer)
COPY pyproject.toml poetry.lock README.md LICENSE ./

# Install runtime dependencies only (no dev group)
RUN poetry env use python3.12 --no-interaction --no-ansi \
    && poetry install --only main --no-interaction --no-ansi

# Copy the rest of the source tree
COPY src/ src/

# Cloud Run injects $PORT (defaults to 8080)
ENV PORT=8080
EXPOSE ${PORT}

# Run the API via uvicorn; Cloud Run sends SIGTERM for graceful shutdown
CMD ["sh", "-c", "uvicorn tfinta.api:app --host 0.0.0.0 --port ${PORT} --log-level info"]
