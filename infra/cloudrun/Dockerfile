# Cloud Run image for the RoboQC API surface.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --upgrade pip \
    && pip install .

RUN useradd --create-home --uid 1001 appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"

CMD exec uvicorn roboqc_agent.api:app \
    --host 0.0.0.0 \
    --port "${PORT}"
