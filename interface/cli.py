import argparse
import sys
import logging
import platform
import colorama
from colorama import Fore, Style
from pathlib import Path

# Initialize colorama for cross-platform colored output
colorama.init()

from core.utils import get_platform_info
from ingest.twitter import TwitterClient
from ingest.reddit import RedditClient
from core.detectors.twitter_base_score import compute_bot_score

logger = logging.getLogger(__name__)

# Add this to the imports at the top
from core.analysis import get_political_keywords, refresh_political_keywords

# Add this function to the cli.py file
def keywords_command(args):
    """Display and refresh political keywords being monitored"""
    print(f"{Fore.YELLOW}Fetching current political keywords...{Style.RESET_ALL}")
    
    if args.refresh:
        print(f"{Fore.YELLOW}Refreshing keywords from news sources...{Style.RESET_ALL}")
        keywords = refresh_political_keywords()
        print(f"{Fore.GREEN}Keywords refreshed!{Style.RESET_ALL}")
    else:
        keywords = get_political_keywords()
    
    if not keywords:
        print(f"{Fore.RED}No keywords found. Try refreshing with --refresh{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}Currently monitoring {len(keywords)} political keywords:{Style.RESET_ALL}")
    
    # Display in columns (3 columns)
    col_width = 25
    for i in range(0, len(keywords), 3):
        row = keywords[i:i+3]
        print("".join(word.ljust(col_width) for word in row))

def print_header():
    """Print a fancy header for the CLI"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  PROJECT EIDOLON - Bot Detection Tool  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    system_info = get_platform_info()
    print(f"\nRunning on: {Fore.GREEN}{system_info['system']} {system_info['release']} ({system_info['machine']}){Style.RESET_ALL}")
    print(f"Python version: {Fore.GREEN}{system_info['python']}{Style.RESET_ALL}\n")

def test_connectivity():
    """Test connectivity to all supported social media platforms"""
    print(f"{Fore.YELLOW}Testing social media API connectivity...{Style.RESET_ALL}")
    
    # Test Twitter
    twitter = TwitterClient()
    twitter_status = twitter.connect()
    status_str = f"{Fore.GREEN}Connected{Style.RESET_ALL}" if twitter_status else f"{Fore.RED}Failed{Style.RESET_ALL}"
    print(f"Twitter API: {status_str}")
    
    # Test Reddit
    reddit = RedditClient()
    reddit_status = reddit.connect()
    status_str = f"{Fore.GREEN}Connected{Style.RESET_ALL}" if reddit_status else f"{Fore.RED}Failed{Style.RESET_ALL}"
    print(f"Reddit API:  {status_str}")
    
    # Overall status
    if twitter_status or reddit_status:
        print(f"\n{Fore.GREEN}At least one API connection successful!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}All API connections failed. Check your credentials.{Style.RESET_ALL}")
    
    return twitter_status or reddit_status

def twitter_search(args):
    """Perform a Twitter search and analyze results for bot activity"""
    twitter = TwitterClient()
    if not twitter.connect():
        print(f"{Fore.RED}Failed to connect to Twitter API. Check your credentials.{Style.RESET_ALL}")
        return
    
    print(f"{Fore.YELLOW}Searching Twitter for: {args.query}{Style.RESET_ALL}")
    tweets = twitter.search_tweets(args.query, args.count)
    
    if not tweets:
        print(f"{Fore.RED}No tweets found for query: {args.query}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}Found {len(tweets)} tweets!{Style.RESET_ALL}")
    
    # Analyze tweets for bot activity
    print(f"\n{Fore.YELLOW}Analyzing users for bot-like behavior:{Style.RESET_ALL}")
    
    for tweet in tweets[:5]:  # Show analysis for first 5 tweets
        user = tweet["user"]
        bot_score = compute_bot_score(user)
        
        score_color = Fore.GREEN if bot_score < 0.3 else (Fore.YELLOW if bot_score < 0.6 else Fore.RED)
        
        print(f"\nUser: {user['screen_name']}")
        print(f"- Followers: {user['followers_count']}")
        print(f"- Following: {user['following_count']}")
        print(f"- Tweets/day: {user['tweets_per_day']:.1f}")
        print(f"- Bot score: {score_color}{bot_score:.2f}{Style.RESET_ALL}")
    
    # Save results to file
    file_path = twitter.save_search_results(args.query, args.count)
    if file_path:
        print(f"\n{Fore.GREEN}Results saved to: {file_path}{Style.RESET_ALL}")

def reddit_search(args):
    """Perform a Reddit search and save results"""
    reddit = RedditClient()
    if not reddit.connect():
        print(f"{Fore.RED}Failed to connect to Reddit API. Check your credentials.{Style.RESET_ALL}")
        return
    
    print(f"{Fore.YELLOW}Searching posts in r/{args.subreddit}{Style.RESET_ALL}")
    posts = reddit.search_subreddit(args.subreddit, args.query, args.count, args.sort)
    
    if not posts:
        print(f"{Fore.RED}No posts found in r/{args.subreddit}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}Found {len(posts)} posts!{Style.RESET_ALL}")
    
    # Display a few posts
    for i, post in enumerate(posts[:3]):
        if i > 0:
            print("\n" + "-" * 50)
        print(f"Title: {post['title']}")
        print(f"Author: {post['author']}")
        print(f"Score: {post['score']} (upvote ratio: {post['upvote_ratio']})")
        print(f"Comments: {post['num_comments']}")
        
        if post.get('selftext') and len(post['selftext']) > 100:
            print(f"Content: {post['selftext'][:100]}...")
        elif post.get('selftext'):
            print(f"Content: {post['selftext']}")
    
    # Save results to file
    file_path = reddit.save_subreddit_results(args.subreddit, args.query, args.count, args.sort)
    if file_path:
        print(f"\n{Fore.GREEN}Results saved to: {file_path}{Style.RESET_ALL}")

def setup_parsers():
    """Set up command line argument parsers"""
    parser = argparse.ArgumentParser(description="Project Eidolon CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Test connectivity
    test_parser = subparsers.add_parser("test", help="Test API connectivity")
    
    # Twitter search
    twitter_parser = subparsers.add_parser("twitter", help="Search Twitter")
    twitter_parser.add_argument("query", help="Search query")