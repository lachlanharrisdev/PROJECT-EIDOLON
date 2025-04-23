# Docker Usage Guide

This guide explains how to set up and run Project Eidolon using Docker and Docker Compose.

## Why Use Docker for Project Eidolon?

Running Project Eidolon within Docker containers offers several advantages over a traditional local installation:

1.  **Consistent Environment:** Docker ensures that Project Eidolon runs in the exact same environment regardless of your host operating system (Linux, macOS, Windows). This eliminates "works on my machine" problems caused by differences in Python versions, system libraries, or dependencies.
2.  **Simplified Dependency Management:** The `Dockerfile` defines all necessary system packages and Python libraries. Docker handles the installation, so you don't need to manage complex dependencies or worry about conflicts with other projects on your system.
3.  **Isolation:** The application runs in an isolated container, preventing it from interfering with your host system's configuration or other installed software.
4.  **Easy Deployment:** Docker makes it straightforward to package and deploy Project Eidolon to servers or cloud environments. The container includes everything needed to run the application.
5.  **Reproducibility:** Anyone can build and run the exact same setup by using the provided `Dockerfile` and `docker-compose.yaml`.

In short, Docker provides a reliable, reproducible, and isolated way to run Project Eidolon, simplifying setup and deployment.

## Prerequisites

-   [Docker Engine](https://docs.docker.com/engine/install/) installed on your system.
-   [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop or installed as a plugin).

## Understanding the Docker Setup

Project Eidolon uses two main files for its Docker configuration:

1.  **`Dockerfile`**: This file contains instructions for building the Docker *image*. It defines the base operating system (Python slim), installs system dependencies, sets up a non-root user, copies the application code, and installs Python packages defined in `requirements.txt` and `pyproject.toml`. It also defines the default entrypoint and command for the container.
2.  **`docker-compose.yaml`**: This file defines how to run the Docker *container(s)* based on the image built by the `Dockerfile`. It specifies:
    *   Which image to use (`build: .` tells it to build from the local `Dockerfile`).
    *   **Volumes:** These map directories from your host machine into the container. This is crucial for:
        *   Persisting reports (`./reports:/app/reports`).
        *   Allowing you to modify pipelines (`./src/pipelines:/app/src/pipelines`), modules (`./src/modules:/app/src/modules`), and settings (`./src/settings:/app/src/settings`) without rebuilding the image.
    *   **Environment Variables:** Configuration options like `LOG_LEVEL`.
    *   **Restart Policy:** Ensures the container restarts if it stops unexpectedly.

## Quick Start with Docker Compose

Docker Compose is the recommended way to run Project Eidolon in Docker.

1.  **Build and Start:**
    Navigate to the project's root directory (where `docker-compose.yaml` is located) in your terminal and run:
    ```bash
    # Build the image (if not already built) and start the container in detached mode (-d)
    docker-compose up --build -d
    ```
    This command performs the following:
    *   `--build`: Tells Docker Compose to build the image using the `Dockerfile` before starting the container. You only *need* this the first time or after changing `Dockerfile` or `requirements.txt`, but it's safe to include.
    *   `-d`: Runs the container in the background (detached mode).

2.  **View Logs:**
    To see the output from the running container:
    ```bash
    docker-compose logs -f
    ```
    Press `Ctrl+C` to stop following the logs.

3.  **Run Specific Commands:**
    The default command runs the pipeline specified in your configuration. To run other `eidolon` CLI commands (like listing modules or running a specific pipeline), use `docker-compose run`:
    ```bash
    # List available modules
    docker-compose run --rm eidolon list-modules

    # Run a specific pipeline (e.g., 'aethon')
    docker-compose run --rm eidolon run --pipeline aethon

    # Get help for the run command
    docker-compose run --rm eidolon run --help
    ```
    *   `--rm`: Automatically removes the temporary container created by `run` after the command finishes.
    *   `eidolon`: Specifies the service name defined in `docker-compose.yaml`.
    *   The rest of the command (`list-modules`, `run --pipeline aethon`, etc.) is passed directly to the container's entrypoint (`python -m src.core.cli.commands`).

4.  **Stop and Remove Containers:**
    To stop the services defined in `docker-compose.yaml` and remove the containers, networks, and volumes created by `up`:
    ```bash
    docker-compose down
    ```
    If you want to remove the image as well, use:
    ```bash
    docker-compose down --rmi all
    ```

## Working with Custom Modules

The `docker-compose.yaml` file already mounts the `./src/modules` directory from your host into the container at `/app/src/modules`.

To add a custom module:

1.  Create your module directory (e.g., `my_custom_module`) inside the `src/modules` directory on your host machine.
2.  Place your module's Python code and any necessary configuration files within `src/modules/my_custom_module`.
3.  Update your pipeline configuration (`src/pipelines/*.yaml`) or main configuration (`src/settings/configuration.yaml`) to reference your new module.
4.  Restart the container if it's already running: `docker-compose restart eidolon` (or `docker-compose up -d` if it was down).

Your custom module code is now accessible inside the container without needing to rebuild the image.

## Building and Running Without Docker Compose

While Docker Compose is recommended, you can build and run the image manually.

1.  **Build the Image:**
    ```bash
    # Build the image and tag it as 'eidolon:latest'
    docker build -t eidolon:latest .
    ```

2.  **Run the Container:**
    You need to manually specify volumes and environment variables.
    ```bash
    docker run -d --name my-eidolon-container \
      -v "$(pwd)/src/pipelines":/app/src/pipelines \
      -v "$(pwd)/src/modules":/app/src/modules \
      -v "$(pwd)/src/settings":/app/src/settings \
      -v "$(pwd)/reports":/app/reports \
      -e LOG_LEVEL=INFO \
      --restart unless-stopped \
      eidolon:latest
    ```
    *   `-d`: Detached mode.
    *   `--name`: Assigns a name to the container.
    *   `-v`: Mounts volumes (syntax might vary slightly depending on your shell, e.g., use `${PWD}` instead of `$(pwd)` in PowerShell).
    *   `-e`: Sets environment variables.
    *   `--restart`: Sets the restart policy.
    *   `eidolon:latest`: The image to use.

    To run specific commands:
    ```bash
    docker run --rm \
      -v "$(pwd)/src/pipelines":/app/src/pipelines \
      -v "$(pwd)/src/modules":/app/src/modules \
      -v "$(pwd)/src/settings":/app/src/settings \
      -v "$(pwd)/reports":/app/reports \
      eidolon:latest list-modules
    ```

## Production Deployment Considerations

For production environments:

1.  **Use Specific Image Tags:** Instead of `latest`, build and push tagged versions (e.g., `your-registry/eidolon:1.2.3`) to a container registry. Update `docker-compose.yaml` to use the specific tag (`image: your-registry/eidolon:1.2.3`).
2.  **Manage Configuration:** Use environment variables, configuration management tools, or Docker secrets for sensitive information instead of mounting the entire `settings` directory if appropriate.
3.  **Resource Limits:** Set CPU and memory limits in your `docker-compose.yaml` (using the `deploy` key) or via your orchestration platform (Kubernetes, Docker Swarm) to prevent resource exhaustion.
4.  **Logging:** Configure Docker's logging drivers to send logs to a centralized logging system (e.g., ELK stack, Splunk, Loki).
5.  **Persistent Data:** If modules require persistent storage beyond reports (e.g., databases, caches), define named volumes in `docker-compose.yaml` and mount them to the appropriate paths within the container.

Example snippet for resource limits in `docker-compose.yaml` (v3+):
```yaml
# ...
services:
  eidolon:
    image: eidolon:1.2.3 # Use a specific tag
    # ... other settings ...
    deploy:
      resources:
        limits:
          cpus: '1.0' # Limit to 1 CPU core
          memory: 2G  # Limit to 2GB RAM
# ...
```

## Extending the Docker Image

If you need to install additional system packages or Python libraries not included in the base requirements, you can create a custom `Dockerfile` that inherits from the base image.

**Example `custom.Dockerfile`:**

```dockerfile
# Use the official image as a base
FROM eidolon:latest

# Switch to root temporarily to install packages
USER root

# Install system packages (example: graphviz)
RUN apt-get update && apt-get install -y --no-install-recommends graphviz && rm -rf /var/lib/apt/lists/*

# Install additional Python packages
RUN pip install --no-cache-dir pandas matplotlib

# Copy custom modules (if not mounting via volume)
# COPY ./my_extra_modules /app/src/modules/my_extra_modules

# Switch back to the non-root user
USER eidolon

# You can override the default command or entrypoint if needed
# ENV LOG_LEVEL=DEBUG
# CMD ["run", "--pipeline", "my_custom_pipeline"]
```

**Build and Run the Custom Image:**

1.  Build: `docker build -t custom-eidolon:1.0 -f custom.Dockerfile .`
2.  Update `docker-compose.yaml` to use `image: custom-eidolon:1.0` instead of `build: .`, or run manually using `docker run custom-eidolon:1.0 ...`.

## Troubleshooting

### Common Issues

1.  **Container Exits Immediately:**
    *   Check logs: `docker-compose logs eidolon` or `docker logs <container_id>`. Look for Python errors or startup failures.
    *   Verify volume mounts: Ensure the paths in `docker-compose.yaml` correctly point to existing directories on your host.
    *   Check configuration: Ensure `src/settings/configuration.yaml` and pipeline files are valid YAML.

2.  **Module Not Found / Import Error:**
    *   Verify the module exists in the mounted `src/modules` directory.
    *   Check for typos in module names in your pipeline configuration.
    *   Ensure the module's `__init__.py` is present if it's a package.
    *   If the module has extra dependencies, they might need to be added to `requirements.txt` (and rebuild the image) or installed in an extended Dockerfile.

3.  **Permission Denied Errors (Volume Mounts):**
    *   Docker Desktop on macOS/Windows usually handles permissions well.
    *   On Linux, ensure the user running Docker (or the `eidolon` user *inside* the container, UID 1000 by default if created with `adduser`) has the necessary permissions for the mounted host directories (`./src`, `./reports`). You might need `sudo chown -R 1000:1000 ./src ./reports` on the host, but be cautious with `chown`.
    *   Check file permissions *within* the container: `docker-compose exec eidolon ls -l /app/src`.

4.  **`docker-compose up` Fails During Build:**
    *   Check the build output for errors (e.g., failed package installations). Ensure network connectivity.
    *   Verify `requirements.txt` and `pyproject.toml` are correctly formatted.

5.  **Changes to Code/Config Not Reflected:**
    *   Ensure you are mounting the correct directories as volumes in `docker-compose.yaml`.
    *   If you changed Python code within mounted volumes (`src/modules`, `src/pipelines`, `src/settings`), you usually just need to restart the service: `docker-compose restart eidolon`.
    *   If you changed `requirements.txt`, `pyproject.toml`, or the `Dockerfile` itself, you need to rebuild the image: `docker-compose up --build -d`.

## Further Reading

-   [Docker Documentation](https://docs.docker.com/)
-   [Docker Compose Documentation](https://docs.docker.com/compose/)
-   [Project Eidolon Pipeline Configuration](pipelines/1-overview.md)