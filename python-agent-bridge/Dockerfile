# Python Agent Bridge
FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

EXPOSE 8097
CMD ["uv", "run", "uvicorn", "agent_bridge.app:app", "--host", "0.0.0.0", "--port", "8097"]
