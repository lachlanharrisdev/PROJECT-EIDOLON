#!/usr/bin/env python3
"""
Test script for the keyword monitoring system.
Fetches political news headlines, extracts entities, and shows the results.
"""
import sys
import json
import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.analysis.keyword_monitor import KeywordMonitor, refresh_political_keywords, get_political_keywords

def setup_logging():
    """Configure logging for the test script"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)

def print_entity_table(entities, limit=None):
    """Print entity information in a tabular format"""
    if not entities:
        print("\nNo entities found.")
        return
        
    # Sort entities by mention count (descending)
    sorted_entities = sorted(
        entities.items(), 
        key=lambda x: x[1]['mentions'], 
        reverse=True
    )
    
    if limit:
        sorted_entities = sorted_entities[:limit]
    
    # Print table header
    print("\n{:<30} {:<10} {:<8} {:<20}".format(
        "Entity", "Type", "Mentions", "Last Seen"
    ))
    print("-" * 70)
    
    # Print each entity
    for entity_name, entity_data in sorted_entities:
        print("{:<30} {:<10} {:<8} {:<20}".format(
            entity_name[:28] + ".." if len(entity_name) > 30 else entity_name,
            entity_data['type'],
            entity_data['mentions'],
            entity_data['last_seen'].split('T')[0]  # Just show the date part
        ))

def test_rss_connection(url):
    """Test if we can connect to the RSS feed"""
    import requests
    logger = logging.getLogger(__name__)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully connected to RSS feed: {url}")
        domain = urlparse(url).netloc
        logger.info(f"RSS source: {domain}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to RSS feed: {e}")
        return False

def run_test(rss_url=None, show_top=10, save_output=True):
    """Run the keyword monitor test"""
    logger = setup_logging()
    
    logger.info("Starting keyword monitor test")
    
    # Test RSS connection first
    if rss_url:
        if not test_rss_connection(rss_url):
            logger.error("RSS connection test failed. Please check the URL and your internet connection.")
            return False
    
    # Create monitor with custom RSS URL if provided
    monitor = None
    keywords = []
    
    try:
        if rss_url:
            monitor = KeywordMonitor(rss_url=rss_url)
            keywords = monitor.refresh()
        else:
            # Use the refresh function from the module
            keywords = refresh_political_keywords()
            monitor = KeywordMonitor()  # Create instance to access data
    
        # Show results
        print("\n" + "="*50)
        print("KEYWORD MONITORING RESULTS")
        print("="*50)
        
        # Get all keywords
        print(f"\nFound {len(keywords)} political entities in news headlines")
        
        # Get full entity data
        entities = monitor.get_keyword_stats()
        
        # Display in table format
        if entities:
            print_entity_table(entities, limit=show_top)
            
            # Show message about additional entities
            if len(entities) > show_top:
                print(f"\n...and {len(entities) - show_top} more entities")
        else:
            print("\nNo entities found in the database. This could be due to:")
            print("1. The RSS feed returned no results")
            print("2. The NLP system couldn't identify political entities")
            print("3. There was an error processing the headlines")
            print("\nTry a different RSS feed or check the logs for errors.")
        
        # Save to file if requested
        if save_output:
            output_path = Path("data") / "tests" / "keyword_monitor_results.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump({
                    "entities": entities,
                    "keywords": keywords,
                    "count": len(keywords)
                }, f, indent=2)
            
            logger.info(f"Saved results to {output_path}")
    
    except Exception as e:
        logger.error(f"Error running keyword monitor test: {e}", exc_info=True)
        return False
        
    return len(keywords) > 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the keyword monitoring system")
    parser.add_argument("--rss", help="Custom RSS feed URL", 
                      default="https://news.google.com/rss/search?q=politics")
    parser.add_argument("--top", type=int, default=10, 
                      help="Show top N entities by mentions")
    parser.add_argument("--no-save", action="store_true", 
                      help="Don't save output to file")
    
    args = parser.parse_args()
    
    success = run_test(
        rss_url=args.rss,
        show_top=args.top,
        save_output=not args.no_save
    )
    
    sys.exit(0 if success else 1)