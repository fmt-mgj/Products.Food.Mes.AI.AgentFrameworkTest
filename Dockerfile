# Multi-stage Docker build for BMAD to PocketFlow Application
# Stage 1: Builder - Generate PocketFlow code from BMAD sources
# Stage 2: Runtime - Minimal production image

# =============================================================================
# BUILDER STAGE - Generate code from BMAD sources
# =============================================================================
FROM python:3.10-alpine AS builder

# Set working directory for build stage
WORKDIR /build

# Install build dependencies for Python packages
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers

# Copy requirements for generation phase
COPY requirements.txt requirements-dev.txt ./

# Install generation dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy PocketFlow framework core
COPY pocketflow/ ./pocketflow/

# Copy BMAD source files
COPY bmad/ ./bmad/
COPY config/ ./config/

# Copy generator scripts and templates
COPY scripts/ ./scripts/

# Generate PocketFlow code from BMAD sources
RUN python scripts/bmad2pf.py --src ./bmad --out ./generated

# Verify generated code structure
RUN ls -la ./generated/ && \
    python -m py_compile generated/app.py && \
    echo "Generated code validation: PASSED"

# =============================================================================
# RUNTIME STAGE - Minimal production image
# =============================================================================
FROM python:3.10-alpine AS runtime

# Set working directory for runtime
WORKDIR /app

# Install runtime system dependencies only
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers && \
    apk add --no-cache curl

# Copy production requirements
COPY requirements.txt ./

# Install production Python dependencies and clean up build deps
RUN pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Copy PocketFlow framework (needed at runtime)
COPY --from=builder /build/pocketflow ./pocketflow

# Copy generated application code from builder
COPY --from=builder /build/generated ./generated

# Copy configuration files (runtime.yaml, etc.)
COPY --from=builder /build/config ./config

# Copy documentation for runtime reference
COPY docs/ ./docs/

# Create memory directory for file-based storage
RUN mkdir -p ./memory

# Environment variables with sensible defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    WORKERS=1 \
    LOG_LEVEL=info \
    MEMORY_BACKEND=file \
    MAX_AGENTS=10 \
    TIMEOUT=300

# Required environment variables (override in deployment)
# OPENAI_API_KEY - Required for LLM operations
# REDIS_URL - Optional, for Redis memory backend

# Expose port
EXPOSE $PORT

# Health check using built-in /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start uvicorn server with production settings
CMD uvicorn generated.app:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    --access-log