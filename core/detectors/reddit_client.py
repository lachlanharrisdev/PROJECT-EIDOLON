import os
import logging
import praw
from datetime import datetime

from core.utils import save_json, timestamp_filename

logger = logging.getLogger(__name__)

class RedditClient:
    """Client for interacting with Reddit API"""
    
    def __init__(self):
        """Initialize Reddit API client using credentials from environment"""
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = os.getenv("REDDIT_USER_AGENT")
        
        self.reddit = None
        self.connected = False
    
    def connect(self):
        """Establish connection to Reddit API"""
        if not all([self.client_id, self.client_secret, self.user_agent]):
            logger.error("Reddit API credentials not found in environment variables")
            return False
        
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            self.connected = True
            logger.info("Successfully connected to Reddit API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Reddit API: {e}")
            return False
    
    def search_subreddit(self, subreddit_name, query=None, limit=100, sort='hot'):
        """Search for posts in a subreddit"""
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Choose the sorting method
            if sort == 'hot':
                posts = subreddit.hot(limit=limit)
            elif sort == 'new':
                posts = subreddit.new(limit=limit)
            elif sort == 'top':
                posts = subreddit.top(limit=limit)
            else:
                posts = subreddit.hot(limit=limit)
            
            # Process and normalize the data
            results = []
            for post in posts:
                # Skip if query is specified and not in title or body
                if query and query.lower() not in post.title.lower() and (
                    not hasattr(post, 'selftext') or query.lower() not in post.selftext.lower()
                ):
                    continue
                
                post_data = {
                    "id": post.id,
                    "title": post.title,
                    "created_utc": datetime.fromtimestamp(post.created_utc).isoformat(),
                    "score": post.score,
                    "upvote_ratio": post.upvote_ratio if hasattr(post, 'upvote_ratio') else None,
                    "url": post.url,
                    "permalink": post.permalink,
                    "num_comments": post.num_comments,
                    "author": post.author.name if post.author else "[deleted]",
                    "is_self": post.is_self,
                }
                
                # Add selftext if it exists
                if hasattr(post, 'selftext'):
                    post_data["selftext"] = post.selftext
                
                # Get top level comments
                post_data["comments"] = []
                post.comments.replace_more(limit=0)  # Only get readily available comments
                for comment in post.comments[:10]:  # Get top 10 comments
                    if comment.author:
                        comment_data = {
                            "id": comment.id,
                            "body": comment.body,
                            "score": comment.score,
                            "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat(),
                            "author": comment.author.name,
                        }
                        post_data["comments"].append(comment_data)
                
                results.append(post_data)
            
            logger.info(f"Retrieved {len(results)} posts from r/{subreddit_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching subreddit: {e}")
            return []
    
    def save_subreddit_results(self, subreddit_name, query=None, limit=100, sort='hot'):
        """Search for posts in a subreddit and save results to file"""
        posts = self.search_subreddit(subreddit_name, query, limit, sort)
        
        if posts:
            filename = timestamp_filename(f"reddit_{subreddit_name}")
            file_path = save_json(posts, filename, subdir="reddit")
            return file_path
        
        return None