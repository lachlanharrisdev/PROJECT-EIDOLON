import os
import logging
import tweepy
from tweepy import OAuthHandler
from datetime import datetime, timedelta

from core.utils import save_json, timestamp_filename

logger = logging.getLogger(__name__)

class TwitterClient:
    """Client for interacting with Twitter API"""
    
    def __init__(self):
        """Initialize Twitter API client using credentials from environment"""
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        
        self.client = None
        self.api = None
        self.connected = False
    
    def connect(self):
        """Establish connection to Twitter API"""
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            logger.error("Twitter API credentials not found in environment variables")
            return False
        
        try:
            # Auth v1
            auth = OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_secret)
            self.api = tweepy.API(auth)
            
            # Client v2
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )
            
            # Test the connection
            self.api.verify_credentials()
            self.connected = True
            logger.info("Successfully connected to Twitter API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Twitter API: {e}")
            return False
    
    def search_tweets(self, query, count=100):
        """Search for tweets matching a query"""
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            tweets = self.api.search_tweets(q=query, count=count, tweet_mode="extended")
            logger.info(f"Retrieved {len(tweets)} tweets for query: {query}")
            
            # Process and normalize the data
            results = []
            for tweet in tweets:
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.full_text,
                    "created_at": tweet.created_at,
                    "user": {
                        "id": tweet.user.id,
                        "screen_name": tweet.user.screen_name,
                        "name": tweet.user.name,
                        "followers_count": tweet.user.followers_count,
                        "following_count": tweet.user.friends_count,
                        "verified": tweet.user.verified,
                        "created_at": tweet.user.created_at,
                        "statuses_count": tweet.user.statuses_count,
                    },
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count,
                }
                
                # Calculate tweets per day
                account_age_days = (datetime.now() - tweet.user.created_at).days or 1
                tweets_per_day = tweet.user.statuses_count / account_age_days
                tweet_data["user"]["tweets_per_day"] = tweets_per_day
                
                results.append(tweet_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []
    
    def save_search_results(self, query, count=100):
        """Search for tweets and save results to file"""
        tweets = self.search_tweets(query, count)
        
        if tweets:
            filename = timestamp_filename(f"twitter_search_{query.replace(' ', '_')}")
            file_path = save_json(tweets, filename, subdir="twitter")
            return file_path
        
        return None