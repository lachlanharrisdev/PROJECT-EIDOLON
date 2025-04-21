"""
Utilities for version checking and updating the Eidolon tool.
"""

import os
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import requests
from rich.console import Console
from rich.progress import Progress

from core.constants import (
    API_RELEASES_URL,
    REPOSITORY_URL,
    DEFAULT_VERSION,
    VERSION_CACHE_FILE,
)

# Initialize console for rich output
console = Console()


def get_current_version() -> str:
    """
    Get the current version of the application.
    First checks if we're in a git repository, otherwise uses the fallback version.

    Returns:
        str: The current version string (e.g., "v0.3.0")
    """
    # Try to get version from git tags first
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Get the most recent tag
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fallback to the default version if git commands fail
    return DEFAULT_VERSION


def _read_cached_version_data() -> Dict[str, Any]:
    """
    Read cached version data from the cache file.

    Returns:
        Dict[str, Any]: The cached version data as a dictionary
    """
    cache_path = Path.home() / VERSION_CACHE_FILE

    if not cache_path.exists():
        return {}

    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _write_cached_version_data(data: Dict[str, Any]) -> None:
    """
    Write version data to the cache file.

    Args:
        data (Dict[str, Any]): The version data to cache
    """
    cache_path = Path.home() / VERSION_CACHE_FILE

    try:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    except IOError:
        pass  # Silently fail if we can't write to the cache file


def check_for_updates(force: bool = False) -> Tuple[bool, str, str]:
    """
    Check if there are updates available for the application.

    Args:
        force (bool): Force check even if the cache is still valid

    Returns:
        Tuple[bool, str, str]: (update_available, current_version, latest_version)
    """
    current_version = get_current_version()

    # Check the cache first (unless force is True)
    if not force:
        cache_data = _read_cached_version_data()
        last_check = cache_data.get("last_check")

        # If we checked less than 24 hours ago, use the cached result
        if last_check and (
            datetime.now() - datetime.fromisoformat(last_check)
        ) < timedelta(hours=24):
            latest_version = cache_data.get("latest_version")
            if latest_version:
                return (
                    current_version != latest_version,
                    current_version,
                    latest_version,
                )

    # Fetch the latest release from GitHub API
    try:
        response = requests.get(API_RELEASES_URL, timeout=10)
        response.raise_for_status()

        releases = response.json()
        if releases and isinstance(releases, list) and len(releases) > 0:
            latest_version = releases[0]["tag_name"]

            # Cache the result
            _write_cached_version_data(
                {
                    "last_check": datetime.now().isoformat(),
                    "latest_version": latest_version,
                }
            )

            return current_version != latest_version, current_version, latest_version
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        console.print(f"Error checking for updates: {e}", style="yellow")

    # Return no update available if we couldn't check
    return False, current_version, current_version


def download_update() -> bool:
    """
    Download and install the latest version of the application.

    Returns:
        bool: True if the update was successful, False otherwise
    """
    update_available, current_version, latest_version = check_for_updates(force=True)

    if not update_available:
        console.print("You are already using the latest version.", style="green")
        return True

    console.print(f"Updating from {current_version} to {latest_version}...")

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Clone the repository to get the latest version
        with Progress() as progress:
            task = progress.add_task("[cyan]Downloading...", total=100)

            try:
                # Do a shallow clone with depth 1 to only get the latest version
                process = subprocess.Popen(
                    ["git", "clone", "--depth", "1", REPOSITORY_URL, temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Show progress while waiting for the clone to complete
                while process.poll() is None:
                    progress.update(task, advance=1)
                    time.sleep(0.1)

                    # Don't go beyond 95% until we know it's done
                    if progress.tasks[task].completed > 95:
                        progress.update(task, completed=95)

                if process.returncode != 0:
                    console.print("Failed to download update.", style="red")
                    return False

                # Complete the progress bar
                progress.update(task, completed=100)
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                console.print(f"Error during update: {e}", style="red")
                return False

        # Install the new version using pip
        console.print("Installing update...", style="blue")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(temp_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            console.print(f"Successfully updated to {latest_version}!", style="green")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"Failed to install update: {e}", style="red")
            console.print(f"Error output: {e.stderr}", style="red")
            return False


def print_version_info() -> None:
    """
    Print information about the current version and available updates.
    """
    current_version = get_current_version()
    console.print(f"Current version: {current_version}", style="blue")

    # Check for updates
    try:
        update_available, _, latest_version = check_for_updates()

        if update_available:
            console.print(f"New version available: {latest_version}", style="yellow")
            console.print(
                f"Run 'eidolon update' to update to the latest version.", style="yellow"
            )
        else:
            console.print("You are using the latest version.", style="green")
    except Exception as e:
        console.print(f"Failed to check for updates: {e}", style="red")
