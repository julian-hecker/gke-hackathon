FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY uv.lock pyproject.toml README.md ./
COPY libs/shared-utils/pyproject.toml libs/shared-utils/
COPY libs/shared-utils/README.md libs/shared-utils/
COPY libs/adk-agents/pyproject.toml libs/adk-agents/
COPY libs/adk-agents/README.md libs/adk-agents/
COPY apps/anthos-mcp/pyproject.toml apps/anthos-mcp/
COPY apps/anthos-mcp/README.md apps/anthos-mcp/
COPY apps/voice-bridge/pyproject.toml apps/voice-bridge/
COPY apps/voice-bridge/README.md apps/voice-bridge/

RUN uv sync --locked --no-editable --no-install-workspace

COPY . .

RUN uv sync --locked


FROM python:3.13-slim AS runtime
COPY --from=builder /app /app
WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "anthos_mcp.main:app", "--host", "0.0.0.0", "--port", "8000"]
