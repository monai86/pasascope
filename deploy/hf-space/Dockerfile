# PasaScope API for a Hugging Face Space (Docker SDK).
# Built from the bundle that scripts/build_hf_space_bundle.sh assembles.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/home/user/app:/home/user/app/apps/api:/home/user/app/src \
    HF_HOME=/home/user/.cache/huggingface \
    PASASCOPE_LOCAL_STORAGE_ROOT=/home/user/storage \
    WEB_CONCURRENCY=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as uid 1000.
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

COPY --chown=user requirements.txt /tmp/root-requirements.txt
COPY --chown=user apps/api/requirements.txt /tmp/api-requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/root-requirements.txt -r /tmp/api-requirements.txt
ENV PATH=/home/user/.local/bin:$PATH

COPY --chown=user . .
RUN mkdir -p /home/user/storage

EXPOSE 7860
WORKDIR /home/user/app/apps/api
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
