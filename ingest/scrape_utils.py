import os
import logging
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Common user agents for requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
]

def get_random_user_agent():
    """Return a random user agent string"""
    return random.choice(USER_AGENTS)

def make_request(url, method="GET", headers=None, params=None, json_data=None, retry=3, backoff=1.5):
    """Make an HTTP request with retry logic"""
    if headers is None:
        headers = {"User-Agent": get_random_user_agent()}
    
    attempt = 0
    while attempt < retry:
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            attempt += 1
            wait_time = backoff ** attempt
            
            if attempt < retry:
                logger.warning(f"Request failed: {e}. Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Request failed after {retry} attempts: {e}")
                return None

def save_response_content(response, filename=None, subdir="raw_data"):
    """Save response content to file"""
    if response is None:
        return None
    
    # Generate filename if not provided
    if filename is None:
        url_path = urlparse(response.url).path
        filename = os.path.basename(url_path)
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{timestamp}"
    
    # Ensure data directory exists
    data_dir = Path("data") / subdir
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension and save
    content_type = response.headers.get("Content-Type", "")
    file_path = data_dir / filename
    
    if "json" in content_type:
        file_path = file_path.with_suffix(".json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.text)
    elif "html" in content_type:
        file_path = file_path.with_suffix(".html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.text)
    else:
        file_path = file_path.with_suffix(".bin")
        with open(file_path, "wb") as f:
            f.write(response.content)
    
    logger.info(f"Saved response to {file_path}")
    return file_path

def extract_text_from_html(html_content):
    """Extract clean text from HTML content"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text(separator=" ", strip=True)
        
        # Remove extra whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = " ".join(line for line in lines if line)
        
        return text
    except ImportError:
        logger.warning("BeautifulSoup not installed. Returning raw HTML.")
        return html_content
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""

def rate_limit_sleep(min_seconds=1, max_seconds=3):
    """Sleep for a random duration to respect rate limits"""
    sleep_time = random.uniform(min_seconds, max_seconds)
    time.sleep(sleep_time)