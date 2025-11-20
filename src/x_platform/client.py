"""Functions for posting tweets to X (Twitter)."""

import logging
from typing import Any, Optional

from tweepy import Client, TweepyException

from src.config import config

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def _get_client() -> Client:
    """Get or create X API client."""
    global _client
    if _client is None:
        _client = Client(
            consumer_key=config.x_api_key,
            consumer_secret=config.x_api_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
        )
    return _client


def post_tweet(tweet_text: str) -> str:
    """
    Post a tweet to X (Twitter).

    Args:
        tweet_text: Text content of the tweet.

    Returns:
        X tweet ID.

    Raises:
        TweepyException: If posting fails.
    """
    try:
        logger.info("Posting tweet to X")
        client = _get_client()
        response: Any = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        logger.info(f"Successfully posted tweet to X (tweet_id={tweet_id})")
        return str(tweet_id)
    except TweepyException as e:
        logger.error(f"Failed to post tweet to X: {e}")
        raise

