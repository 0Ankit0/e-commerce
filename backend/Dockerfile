FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-install-project --no-dev --no-group test

COPY . .
RUN uv sync --frozen --no-dev --no-group test \
    && groupadd --system appuser \
    && useradd --system --create-home --gid appuser appuser \
    && mkdir -p /app/media /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
