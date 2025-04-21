# Docker Usage Guide

Project Eidolon provides Docker support for easy deployment and consistent execution environments. This document explains how to use Docker with Project Eidolon.

## Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) for multi-container setups

## Quick Start

The simplest way to run Project Eidolon with Docker is using the provided Docker Compose file:

```bash
# Start the containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the containers
docker-compose down
```

## Docker Compose Configuration

The default `docker-compose.yaml` file includes:

```yaml
version: '3'

services:
  eidolon:
    build: .
    image: eidolon:latest
    volumes:
      - ./src:/app/src
      - ./reports:/app/reports
    environment:
      - LOG_LEVEL=INFO
      - PIPELINE=default
    ports:
      - "8000:8000"
```

## Customizing the Environment

You can customize the Docker environment by:

1. Modifying the environment variables in the `docker-compose.yaml` file
2. Creating a `.env` file with your environment variables
3. Passing environment variables on the command line

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | INFO |
| `PIPELINE` | Name of the pipeline to run | default |
| `CONFIG_PATH` | Path to a custom configuration file | src/settings/configuration.yaml |

### Example Custom Setup

```bash
# Create a .env file
echo "LOG_LEVEL=DEBUG" > .env
echo "PIPELINE=custom_osint_pipeline" >> .env

# Run with the .env file
docker-compose up -d
```

## Building a Custom Image

You can build a custom Docker image with your own modules:

```bash
# Build a custom image
docker build -t custom-eidolon:1.0 .

# Run the custom image
docker run -d \
  -v ./src/modules:/app/src/modules \
  -v ./reports:/app/reports \
  -e PIPELINE=custom_pipeline \
  custom-eidolon:1.0
```

## Mounting Custom Modules

You can mount your modules into the container:

```bash
docker run -d \
  -v ./src/modules/custom_module:/app/src/modules/custom_module \
  -v ./reports:/app/reports \
  eidolon:latest
```

## Production Deployment

For production use, consider these best practices:

1. Use specific image tags rather than `latest`
2. Mount volumes for persistent data
3. Set appropriate resource limits
4. Use Docker Compose or a container orchestration platform (Kubernetes, Docker Swarm)

Example production docker-compose.yaml:

```yaml
version: '3'

services:
  eidolon:
    image: eidolon:1.2.3
    volumes:
      - eidolon-data:/app/data
      - eidolon-reports:/app/reports
    environment:
      - LOG_LEVEL=WARNING
      - PIPELINE=production_pipeline
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: unless-stopped

volumes:
  eidolon-data:
  eidolon-reports:
```


## Extending the Docker Image

You can create your own Dockerfile that extends the base image:

```dockerfile
FROM eidolon:latest

# Install additional dependencies
RUN pip install --no-cache-dir pandas scikit-learn tensorflow

# Copy custom modules
COPY ./custom_modules /app/src/modules/

# Set default pipeline
ENV PIPELINE=custom_osint_pipeline

# Override default command if needed
CMD ["python", "main.py", "--pipeline", "${PIPELINE}"]
```

## Troubleshooting

### Common Issues

1. **Container exits immediately**
   - Check logs: `docker logs <container_id>`
   - Ensure volumes are mounted correctly
   - Verify environment variables

2. **Module not found**
   - Check module path in volume mounts
   - Verify pipeline configuration

3. **Permission issues**
   - Fix permissions: `chown -R 1000:1000 ./src`

4. **Performance issues**
   - Increase Docker resource limits
   - Use volume mounts for frequently accessed files

## Further Reading

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Project Eidolon Pipeline Configuration](pipelines/1-overview.md)