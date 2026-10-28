FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY ecommerce/pyproject.toml ecommerce/pyproject.toml
RUN uv sync --frozen --no-dev --package ecommerce --no-install-workspace

COPY ecommerce ecommerce
RUN uv sync --frozen --no-dev --package ecommerce

RUN useradd --system --no-create-home app
USER app
