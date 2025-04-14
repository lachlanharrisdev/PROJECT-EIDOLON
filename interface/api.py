import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

from ingest.twitter import TwitterClient
from ingest.reddit import RedditClient
from core.detectors.twitter_base_score import compute_bot_score

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Project Eidolon API",
    description="API for social media bot detection and misinformation analysis",
    version="0.1.0",
)

# API models
class SearchQuery(BaseModel):
    query: str
    count: Optional[int] = 100

class SubredditQuery(BaseModel):
    subreddit: str
    query: Optional[str] = None
    count: Optional[int] = 100
    sort: Optional[str] = "hot"

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None

# Twitter client instance
twitter_client = TwitterClient()

# Reddit client instance
reddit_client = RedditClient()

@app.get("/", response_model=ApiResponse)
async def root():
    """Root endpoint to check if API is running"""
    return ApiResponse(
        status="success",
        message="Project Eidolon API is running",
        data={"version": "0.1.0"}
    )

@app.get("/health", response_model=ApiResponse)
async def health():
    """Health check endpoint"""
    return ApiResponse(
        status="success",
        message="API is healthy",
        data={"status": "UP"}
    )

@app.post("/twitter/search", response_model=ApiResponse)
async def search_twitter(query: SearchQuery):
    """Search Twitter for posts matching a query"""
    try:
        if not twitter_client.connected:
            twitter_client.connect()
        
        tweets = twitter_client.search_tweets(query.query, query.count)
        
        # Add bot scores to each tweet
        for tweet in tweets:
            tweet["user"]["bot_score"] = compute_bot_score(tweet["user"])
        
        return ApiResponse(
            status="success",
            message=f"Found {len(tweets)} tweets matching query '{query.query}'",
            data=tweets
        )
    except Exception as e:
        logger.error(f"Error searching Twitter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reddit/search", response_model=ApiResponse)
async def search_reddit(query: SubredditQuery):
    """Search Reddit for posts in a subreddit"""
    try:
        if not reddit_client.connected:
            reddit_client.connect()
        
        posts = reddit_client.search_subreddit(
            query.subreddit,
            query.query,
            query.count,
            query.sort
        )
        
        return ApiResponse(
            status="success",
            message=f"Found {len(posts)} posts in r/{query.subreddit}",
            data=posts
        )
    except Exception as e:
        logger.error(f"Error searching Reddit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def start_api():
    """Start the FastAPI server"""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_api()