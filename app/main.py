import asyncio
import logging
from app.scheduler import schedule_task
from core.analysis.keyword_monitor import refresh_political_keywords

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def async_refresh_political_keywords():
    """
    Asynchronous wrapper for the refresh_political_keywords function.
    """
    refresh_political_keywords()

async def main():
    """
    Main entry point for the application.
    Runs the dynamic keyword detection engine periodically.
    """
    logger.info("Starting Project Eidolon...")
    
    # Schedule the keyword refresh task to run every hour
    await schedule_task(async_refresh_political_keywords, interval=3600)

if __name__ == "__main__":
    asyncio.run(main())