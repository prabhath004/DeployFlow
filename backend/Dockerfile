# --- builder: install deps into a venv we can copy ---
FROM python:3.13-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build deps needed for asyncpg / argon2-cffi C extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# setuptools is needed because some OpenTelemetry packages still import
# pkg_resources, which was removed in setuptools 81+. Pin below that.
RUN pip install --upgrade pip "setuptools<80" wheel

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt


# --- runtime: slim, non-root, copy the venv from builder ---
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}"

# A non-root user — never run web processes as root in containers.
RUN groupadd --system app && useradd --system --gid app --home /app app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && chown -R app:app /app

USER app

ENTRYPOINT ["entrypoint.sh"]
CMD ["api"]
