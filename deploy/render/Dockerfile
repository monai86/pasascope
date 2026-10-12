# PasaScope API for a small host (Render free plan, 512 MB).
# Build context is the repository root. Transcription runs on a hosted service
# (PASASCOPE_ASR_HOSTED_*), so the on-device Whisper stack is not installed.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv:/srv/apps/api:/srv/src \
    PASASCOPE_LOCAL_STORAGE_ROOT=/srv/storage \
    WEB_CONCURRENCY=1 \
    PORT=8000

WORKDIR /srv

COPY apps/api/requirements.txt /tmp/api-requirements.txt
COPY deploy/render/requirements.txt /tmp/render-requirements.txt
RUN pip install --no-cache-dir -r /tmp/api-requirements.txt -r /tmp/render-requirements.txt

# Same layout as the repository, so paths resolved from the source tree hold.
COPY apps/api/app/ ./apps/api/app/
COPY apps/api/alembic.ini apps/api/alembic-assessment.ini ./apps/api/
COPY src/ ./src/
COPY packages/ ./packages/
COPY artifacts/reference_evidence/ ./artifacts/reference_evidence/
COPY artifacts/model_card_v2.md artifacts/feature_schema.json ./artifacts/
COPY data/demo/ ./data/demo/
RUN mkdir -p /srv/storage

EXPOSE 8000
WORKDIR /srv/apps/api
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
