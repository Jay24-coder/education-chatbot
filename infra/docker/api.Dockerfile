# Phase 1 API image for local dev. Build from repo root: docker build -f infra/docker/api.Dockerfile .
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --no-dev
COPY app ./app
COPY .env.example .env
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
