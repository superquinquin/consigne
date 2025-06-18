FROM python:3.12-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/root/.local/bin/:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    gcc \
    libzbar-dev \
    curl \
    build-essential

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

COPY ./api /app
WORKDIR /app
RUN uv pip install -r pyproject.toml
RUN find / -name "inspector.py" -path "*/tracerite/*" -exec sed -i 's/except AttributeError, TypeError:/except (AttributeError, TypeError):/' {} \; 