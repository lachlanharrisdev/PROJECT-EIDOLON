import os

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Configuration variables
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RSS_URL = os.getenv("RSS_URL", "https://news.google.com/rss/search?q=politics")
DATA_DIR = os.getenv("DATA_DIR", "data")
