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

    # Run the scheduler for 3 intervals
    await asyncio.wait_for(schedule_task(mock_task, interval=1), timeout=3.5)

    # Verify the task was executed 3 times
    assert len(results) == 3


@pytest.mark.asyncio
async def test_schedule_task_handles_exceptions():
    """
    Test that the scheduler continues running even if the task raises an exception.
    """
    results = []

    async def mock_task():
        if len(results) == 0:
            raise ValueError("Simulated task failure")
        results.append("task executed")

    # Run the scheduler for 2 intervals
    await asyncio.wait_for(schedule_task(mock_task, interval=1), timeout=2.5)

    # Verify the task was executed at least once after the exception
    assert len(results) == 1