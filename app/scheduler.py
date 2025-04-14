import asyncio
import logging

logger = logging.getLogger(__name__)

async def schedule_task(task, interval: int):
    """
    Schedule a task to run periodically.

    Args:
        task: The coroutine function to execute.
        interval: Time interval in seconds between executions.
    """
    while True:
        try:
            logger.info(f"Running task: {task.__name__}")
            await task()
        except Exception as e:
            logger.error(f"Error while running task {task.__name__}: {e}")
        await asyncio.sleep(interval)