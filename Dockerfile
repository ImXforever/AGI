# =============================================================================
# Kia-Agent Platform — Production Dockerfile
# Multi-stage build: python:3.12-slim, non-root, healthcheck, uvicorn
# =============================================================================

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd -r kiaagent && useradd -r -g kiaagent -d /app -s /sbin/nologin kiaagent \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.30.0" \
    "httpx>=0.27.0" \
    "asyncpg>=0.29.0" \
    "redis[hiredis]>=5.0.0" \
    "argon2-cffi>=23.1.0" \
    "itsdangerous>=2.2.0" \
    "python-dotenv>=1.0.0" \
    "pydantic>=2.7.0" \
    "python-multipart>=0.0.9" \
    "boto3>=1.34.0" \
    "aiobotocore>=2.12.0" \
    "gunicorn>=22.0.0" \
    "pyyaml>=6.0.0" \
    "aiogram>=3.0.0"

COPY . .

RUN mkdir -p /app/data /app/logs && \
    chown -R kiaagent:kiaagent /app

USER kiaagent

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,httpx; p=os.environ.get('PORT','8080'); r=httpx.get(f'http://127.0.0.1:{p}/healthz'); assert r.status_code==200"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers"]
