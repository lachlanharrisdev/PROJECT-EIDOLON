#!/usr/bin/env python3
import os
import argparse
import logging
from dotenv import load_dotenv

# Import our modules
from interface.cli import run_cli
from interface.api import start_api

# Load environment variables
load_dotenv()

def setup_logging():
    """Configure logging for the application"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)

def main():
    """Main entry point for the application"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description="Project Eidolon - Social Media Bot Detection")
    parser.add_argument("--mode", choices=["cli", "api"], default="cli", help="Run mode (cli or api)")
    args = parser.parse_args()
    
    if args.mode == "api":
        logger.info("Starting in API mode")
        start_api()
    else:
        logger.info("Starting in CLI mode")
        run_cli()

if __name__ == "__main__":
    main()