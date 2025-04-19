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

# Copy application code
COPY . .

# Install the application in development mode
RUN pip install -e .

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
