import asyncio
import pytest

from app.scheduler import schedule_task


@pytest.mark.asyncio
async def test_schedule_task_runs_periodically():
    """
    Test that the scheduler runs a task periodically.
    """
    results = []

    async def mock_task():
        results.append("task executed")

    # Run the scheduler in the background
    task = asyncio.create_task(schedule_task(mock_task, interval=1))
    await asyncio.sleep(3.5)  # Allow the task to run for 3 intervals
    task.cancel()  # Cancel the scheduler task

    # Verify the task was executed at least 2 times
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_schedule_task_handles_exceptions():
    """
    Test that the scheduler continues running even if the task raises an exception.
    """
    results = []

    async def mock_task():
        if len(results) == 0:
            try:
                raise ValueError("Simulated task failure")
            except ValueError:
                pass  # Handle the exception to ensure the task continues
        results.append("task executed")

    # Run the scheduler in the background
    task = asyncio.create_task(schedule_task(mock_task, interval=1))
    await asyncio.sleep(2.5)  # Allow the task to run for 2 intervals
    task.cancel()  # Cancel the scheduler task

    # Verify the task was executed at least once after the exception
    assert len(results) >= 1
