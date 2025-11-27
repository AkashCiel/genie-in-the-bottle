"""Script to process Substack feeds and generate tweets.
This can be run manually or via GitHub Actions."""

import logging
import sys
import time
from typing import Any, Dict

from src.database.handle_tweets_data import (
    create_tweet_record,
    get_all_existing_web_urls,
    send_earliest_queued_tweet_for_approval,
)
from src.openai_client import OpenAIClient
from src.tweet_generation.substack.composer import generate_tweet_single
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
    Process all Substack feeds, generate tweets sequentially, and queue them.
    Then send the earliest queued tweet for approval.
    
    Returns:
        Dictionary with processing results.
    """
    try:
        # Load existing web URLs to check for duplicates
        existing_urls = get_all_existing_web_urls()
        logger.info(f"Loaded {len(existing_urls)} existing URLs for duplicate checking")
        
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
        
        # Filter out articles that already exist in database
        new_articles = [
            article for article in all_articles
            if article.get("link", "") not in existing_urls
        ]
        
        logger.info(f"After duplicate filtering: {len(new_articles)} new articles to process")
        
        if not new_articles:
            logger.info("No new articles to process")
            # Still send earliest queued tweet if any exist
            send_earliest_queued_tweet_for_approval()
            return {"message": "No new articles", "processed": 0}
        
        # Process articles sequentially
        openai_client = OpenAIClient()
        processed_count = 0
        total_tweets_generated = 0
        
        for idx, article in enumerate(new_articles, start=1):
            article_id = article.get("title", "")
            article_link = article.get("link", "")
            
            if not article_link:
                logger.warning(f"Article {article_id} missing link – skipping")
                continue
            
            logger.info(f"Processing article {idx}/{len(new_articles)}: {article_id}")
            
            try:
                # Generate tweets for this article
                generated_tweets = generate_tweet_single(article, openai_client)
                
                if not generated_tweets:
                    logger.info(f"No tweets generated for article {article_id}")
                    # Still wait 60 seconds before next article
                    if idx < len(new_articles):
                        logger.info("Waiting 60 seconds before processing next article...")
                        time.sleep(60)
                    continue
                
                # Create tweet records for each generated tweet
                for tweet_data in generated_tweets:
                    tweet_text = tweet_data.get("tweet_text", "")
                    if not tweet_text:
                        continue
                    
                    try:
                        create_tweet_record(
                            article_id=article_id,
                            article_title=article_id,  # Same as article_id (title)
                            tweet_text=tweet_text,
                            web_url=article_link,
                            approval_status="queued",
                        )
                        total_tweets_generated += 1
                    except Exception as e:
                        logger.error(f"Failed to create tweet record for article {article_id}: {e}")
                        continue
                
                processed_count += 1
                logger.info(f"Successfully processed article {article_id} ({total_tweets_generated} tweets generated so far)")
                
                # Wait 60 seconds before processing next article (except for the last one)
                if idx < len(new_articles):
                    logger.info("Waiting 60 seconds before processing next article...")
                    time.sleep(60)
                    
            except Exception as e:
                logger.error(f"Failed to process article {article_id}: {e}")
                # Still wait 60 seconds before next article to respect rate limits
                if idx < len(new_articles):
                    logger.info("Waiting 60 seconds before processing next article...")
                    time.sleep(60)
                continue
        
        logger.info(f"Created {total_tweets_generated} tweet records with queued status from {processed_count} articles")
        
        # Send earliest queued tweet for approval
        send_earliest_queued_tweet_for_approval()
        
        return {
            "message": "Processing complete",
            "processed": processed_count,
            "total_tweets": total_tweets_generated,
            "total_articles": len(new_articles),
        }
        
    except Exception as e:
        logger.error(f"Error processing Substack feeds: {e}")
        raise


if __name__ == "__main__":
    try:
        result = process_substack_feeds()
        logger.info(f"Substack processing completed: {result}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Substack processing failed: {e}")
        sys.exit(1)

