# Build stage
FROM python:3.12.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Final stage
FROM python:3.12.10-slim

WORKDIR /app

# Create non-root user
RUN adduser --disabled-password --gecos "" eidolon

# Copy wheels from builder stage and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Install the application in development mode (without copying all code first)
COPY pyproject.toml setup.py* ./
# If setup.py doesn't exist, this will have no effect
RUN pip install -e . || echo "No setup.py found, continuing with alternate install method"

# Copy application code - this layer will change frequently
# We put this after dependency installation to maximize cache hits
COPY . .


# Set permissions for the eidolon user
RUN chown -R eidolon:eidolon /app

# Switch to non-root user
USER eidolon

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set up entrypoint for CLI interface
ENTRYPOINT ["python", "-m", "src.core.cli.commands"]
CMD ["run"]
