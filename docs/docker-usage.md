# Docker Usage

This guide explains how to use Project Eidolon with Docker for easy deployment and usage.

## Installation Options

There are several ways to get started with the Eidolon Docker image:

### Option 1: Pull from GitHub Container Registry (recommended for users)

```bash
# Pull the latest stable version
docker pull ghcr.io/lachlanharrisdev/project-eidolon:latest

# Or pull a specific version
docker pull ghcr.io/lachlanharrisdev/project-eidolon:1.0.0

# Create a simpler name for the image
docker tag ghcr.io/lachlanharrisdev/project-eidolon:latest eidolon
```

### Option 2: Build from Source (recommended for developers)

```bash
# Clone the repository
git clone https://github.com/your-username/project-eidolon.git
cd project-eidolon

# Build the Docker image with a simple name
docker build -t eidolon -f docker/Dockerfile .
```

### Option 3: Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-username/project-eidolon.git
cd project-eidolon

# Start with docker-compose
docker-compose up

# Or build and start in one command
docker-compose up --build
```

## Quick Start

The simplest way to get started is with Docker Compose:

```bash
docker-compose up
```

This will start Eidolon with the default pipeline.

## Available Commands

The Docker image uses the Eidolon CLI as its entrypoint, allowing you to run any command:

```bash
# Run with a specific pipeline
docker run eidolon run custom_pipeline

# List available modules
docker run eidolon list modules

# List pipelines
docker run eidolon list pipeline

# Validate the installation
docker run eidolon validate

# View configuration
docker run eidolon config logging.level

# Update configuration (requires a volume mount to persist changes)
docker run -v ./src/settings:/app/src/settings eidolon config logging.level DEBUG
```

### Using the GitHub Container Registry image:

If you prefer to use the registry image directly without tagging, you can use the full path:

```bash
# Run with a specific pipeline
docker run ghcr.io/lachlanharrisdev/project-eidolon run custom_pipeline
```

### Running Commands with Docker Compose:

```bash
# Run a specific command using docker-compose
docker-compose run eidolon list modules
docker-compose run eidolon validate
docker-compose run eidolon config logging.level
```

## Environment Variables

You can configure the Eidolon container using environment variables:

- `LOG_LEVEL`: Sets the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Example:

```bash
docker-compose run -e LOG_LEVEL=DEBUG eidolon run
```

## Building the Docker Image

If you've made changes to the Dockerfile, you can build the image locally:

```bash
docker build -t eidolon:local -f docker/Dockerfile .
```


Available tags:
- `latest`: Latest stable build from the main branch
- `x.y.z`: Specific version releases
- `x.y`: Major.minor version releases
- `sha-abcdef`: Specific commit builds