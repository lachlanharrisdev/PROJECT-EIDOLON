# Build stage
FROM python:3.12.10-slim AS builder

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
COPY [pyproject.toml](http://_vscodecontentref_/6) ./
# If setup.py doesn't exist, this will have no effect

# Copy application code - this layer will change frequently
# We put this after dependency installation to maximize cache hits
COPY . .

RUN pip install .


# Set permissions for the eidolon user
RUN chown -R eidolon:eidolon /app

# Switch to non-root user
USER eidolon

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set up entrypoint using the installed script
ENTRYPOINT ["eidolon"]
CMD ["run"]
