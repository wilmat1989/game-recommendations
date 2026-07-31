# syntax=docker/dockerfile:1

FROM node:24-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS application

WORKDIR /app

ENV APP_ENV=production \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

COPY data/game_lookup.parquet ./data/game_lookup.parquet
COPY data/game_recommendation_lists.parquet ./data/game_recommendation_lists.parquet
COPY data/game_recommendation_lists_asymmetric.parquet ./data/game_recommendation_lists_asymmetric.parquet
COPY data/game_recommendation_lists_matrix.parquet ./data/game_recommendation_lists_matrix.parquet
COPY data/game_recommendation_lists_peabrain.parquet ./data/game_recommendation_lists_peabrain.parquet
COPY --from=frontend-build /build/frontend/dist/ ./frontend/dist/

RUN useradd --system --uid 10001 --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

CMD ["sh", "-c", "uvicorn game_recommender.app:app --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips='*' --limit-concurrency 32"]