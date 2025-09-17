# Stage 1: Build dependencies in a venv
FROM python:3.13-slim AS builder
WORKDIR /app

# Copy dependency files for caching
COPY pyproject.toml uv.lock ./
COPY libs/adk-agents/pyproject.toml libs/adk-agents/pyproject.toml
COPY libs/adk-agents/README.md libs/adk-agents/README.md
COPY libs/shared-utils/pyproject.toml libs/shared-utils/pyproject.toml
COPY libs/shared-utils/README.md libs/shared-utils/README.md
COPY apps/voice-bridge/pyproject.toml apps/voice-bridge/pyproject.toml
COPY apps/voice-bridge/README.md apps/voice-bridge/README.md

# Create venv and install dependencies using uv (only in builder)
RUN pip install uv
RUN uv venv /venv
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:$PATH"
RUN uv pip install --upgrade pip
RUN uv pip install --editable libs/adk-agents --editable libs/shared-utils --editable apps/voice-bridge

# Copy the rest of the monorepo
COPY . .


# Stage 2: Final runtime image
FROM python:3.13-slim AS runtime
WORKDIR /app

# Copy venv and app files from builder
COPY --from=builder /venv /venv
COPY --from=builder /app /app

# Set environment variables
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/app/libs/adk-agents/src:/app/libs/shared-utils/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/apps/voice-bridge/src
EXPOSE 8000
CMD ["uvicorn", "voice_bridge.main:app", "--host", "0.0.0.0", "--port", "8000"]
