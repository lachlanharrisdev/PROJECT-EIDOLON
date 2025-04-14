def compute_bot_score(user_data: dict) -> float:
    """
    Very dumb bot scoring system.
    """
    followers = user_data.get('followers_count', 1)
    following = user_data.get('following_count', 1)
    tweet_freq = user_data.get('tweets_per_day', 0)
    verified = user_data.get('verified', False)

    score = 0

    if tweet_freq > 50: score += 0.5
    if following > followers * 5: score += 0.3
    if not verified and followers < 50: score += 0.2

    return min(score, 1.0)
