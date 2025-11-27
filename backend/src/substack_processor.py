"""Script to process Substack feeds and generate tweets.
This can be run manually or via GitHub Actions."""

import logging
import sys
from typing import Any, Dict

from src.database.handle_tweets_data import (
    create_tweet_record,
    get_earliest_queued_tweet,
    update_approval_status,
    update_telegram_message_id,
)
from src.openai_client import OpenAIClient
from src.telegram.bot import send_tweet_for_approval
from src.tweet_generation.substack.composer import generate_tweets_batch
from src.tweet_generation.substack.feed_reader import (
    get_substack_feed_url,
    load_substack_accounts,
    read_substack_feed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_substack_feeds() -> Dict[str, Any]:
    """
    Process all Substack feeds, generate tweets, and queue them.
    Then send the earliest queued tweet for approval.
    
    Returns:
        Dictionary with processing results.
    """
    try:
        accounts = load_substack_accounts()
        logger.info(f"Processing {len(accounts)} Substack accounts")
        
        all_articles = []
        for account in accounts:
            try:
                feed_url = get_substack_feed_url(account)
                logger.info(f"Reading feed: {feed_url}")
                articles = read_substack_feed(feed_url)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error processing account {account}: {e}")
                continue
        
        if not all_articles:
            logger.info("No articles found in any feed")
            return {"message": "No articles found", "processed": 0}
        
        logger.info(f"Found {len(all_articles)} articles total")
        
        # Prepare articles for batch generation
        articles_for_generation = []
        for article in all_articles:
            articles_for_generation.append({
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "content": article.get("content", ""),
            })
        
        # Generate tweets
        openai_client = OpenAIClient()
        try:
            generated_tweets = generate_tweets_batch(articles_for_generation, openai_client)
        except Exception as e:
            logger.error(f"Failed to generate tweets: {e}")
            raise
        
        # Create tweet records with queued status
        processed_count = 0
        article_map = {article.get("title", ""): article for article in all_articles}
        
        for tweet_data in generated_tweets:
            article_id = tweet_data.get("article_id", "")  # This is the title
            tweet_text = tweet_data.get("tweet_text", "")
            article = article_map.get(article_id)
            
            if not article:
                logger.warning(f"Article ID {article_id} not found in feed results")
                continue
            
            article_link = article.get("link", "")
            if not article_link:
                logger.warning(f"Article {article_id} missing link – skipping")
                continue
            
            try:
                create_tweet_record(
                    article_id=article_id,
                    article_title=article_id,  # Same as article_id (title)
                    tweet_text=tweet_text,
                    web_url=article_link,
                    approval_status="queued",
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to create tweet record for article {article_id}: {e}")
                continue
        
        logger.info(f"Created {processed_count} tweet records with queued status")
        
        # Send earliest queued tweet for approval
        _send_earliest_queued_tweet_for_approval()
        
        return {
            "message": "Processing complete",
            "processed": processed_count,
            "total": len(generated_tweets),
        }
        
    except Exception as e:
        logger.error(f"Error processing Substack feeds: {e}")
        raise


def _send_earliest_queued_tweet_for_approval() -> None:
    """Find the earliest queued tweet and send it to Telegram for approval."""
    try:
        queued_tweet = get_earliest_queued_tweet()
        if not queued_tweet:
            logger.info("No queued tweets found")
            return
        
        record_id = str(queued_tweet["id"])
        tweet_text = queued_tweet.get("tweet_text", "")
        article_id = queued_tweet.get("article_id", "")
        web_url = queued_tweet.get("web_url", "")
        
        telegram_message_id = send_tweet_for_approval(
            tweet_text=tweet_text,
            article_id=article_id,
            web_url=web_url,
        )
        
        update_telegram_message_id(record_id, telegram_message_id)
        update_approval_status(record_id, "pending")
        logger.info(f"Sent earliest queued tweet for approval (record_id={record_id})")
        
    except Exception as e:
        logger.error(f"Failed to send earliest queued tweet for approval: {e}")


if __name__ == "__main__":
    try:
        result = process_substack_feeds()
        logger.info(f"Substack processing completed: {result}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Substack processing failed: {e}")
        sys.exit(1)

