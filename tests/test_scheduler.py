import asyncio
import pytest
from app.scheduler import schedule_task

@pytest.mark.asyncio
async def test_schedule_task():
    """
    Test that the scheduler runs a task periodically.
    """
    results = []

    async def mock_task():
        results.append("task executed")

    # Run the scheduler for 3 intervals
    task = asyncio.create_task(schedule_task(mock_task, interval=1))
    await asyncio.sleep(3.5)
    task.cancel()

    assert len(results) == 3