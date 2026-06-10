# Fable 5 reasoning service — Cloud Run image.
# Build from the repo root:
#   docker build -f infra/fable5/Dockerfile -t fable5-reasoning .
FROM python:3.11-slim

# Run as non-root: Cloud Run does not require it, but it removes a whole class
# of container-escape findings from security review.
RUN useradd --create-home --uid 1001 appuser

WORKDIR /app

COPY infra/fable5/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/neuron_vision/fable5 src/neuron_vision/fable5
COPY src/neuron_vision/__init__.py src/neuron_vision/__init__.py

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PORT=8080

USER appuser
EXPOSE 8080

# Single worker per instance; scale horizontally with Cloud Run instances.
CMD exec uvicorn neuron_vision.fable5.api:app --host 0.0.0.0 --port ${PORT}
