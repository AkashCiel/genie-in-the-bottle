"""Vercel API route handler for Juggernaut webhook."""

import json
import logging
import sys
import traceback
from typing import Any, Dict

# Configure logging to output to stdout/stderr (captured by Vercel)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Try to import modules and log any import errors
try:
    from src.config import config
    from src.database.external_db import fetch_articles_by_user_and_date
    from src.database.internal_db import create_tweet_record, update_telegram_message_id
    from src.openai_client import OpenAIClient
    from src.telegram.bot import send_status_notification, send_tweet_for_approval
    from src.tweet_generation.composer import generate_tweets_batch
    logger.info("All modules imported successfully")
except Exception as e:
    logger.error(f"Failed to import modules: {e}")
    logger.error(traceback.format_exc())
    # Re-raise to fail fast and show error in Vercel
    raise


def handler(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle webhook request from Juggernaut.

    Expected request body:
        {
            "user_id": "string",
            "created_at": "string"
        }

    Returns:
        HTTP response dictionary with statusCode and body.
    """
    try:
        # Parse request body
        if isinstance(request.get("body"), str):
            body = json.loads(request["body"])
        else:
            body = request.get("body", {})

        user_id = body.get("user_id")
        created_at = body.get("created_at")

        if not user_id or not created_at:
            logger.error("Missing required fields: user_id or created_at")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields: user_id and created_at"}),
            }

        logger.info(f"Processing webhook: user_id={user_id}, created_at={created_at}")

        # Fetch articles from external database
        articles = fetch_articles_by_user_and_date(user_id, created_at)
        if not articles:
            logger.warning("No articles found for the given criteria")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No articles found", "processed": 0}),
            }

        # Initialize OpenAI client
        openai_client = OpenAIClient()

        # Generate tweets in batch
        try:
            generated_tweets = generate_tweets_batch(articles, openai_client)
        except Exception as e:
            logger.error(f"Batch tweet generation failed: {e}")
            # Send failure notification to Telegram
            error_message = (
                f"❌ Batch tweet generation failed\n\n"
                f"User ID: {user_id}\n"
                f"Created At: {created_at}\n"
                f"Error: {str(e)}"
            )
            try:
                send_status_notification(error_message)
            except Exception as telegram_error:
                logger.error(f"Failed to send Telegram notification: {telegram_error}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Batch tweet generation failed", "details": str(e)}),
            }

        # Create a mapping of article_id to article data for quick lookup
        article_map = {article.get("id", ""): article for article in articles}

        # Process each generated tweet
        processed_count = 0
        for tweet_data in generated_tweets:
            try:
                article_id = tweet_data.get("article_id", "")
                tweet_text = tweet_data.get("tweet_text", "")

                # Find matching article data
                article = article_map.get(article_id)
                if not article:
                    logger.warning(f"Article ID mismatch: {article_id} not found in fetched articles")
                    continue

                # Create tweet record in internal DB (placeholder)
                record_id = create_tweet_record(
                    article_id=article_id,
                    article_title=article.get("title", ""),
                    tweet_text=tweet_text,
                )

                # Send to Telegram for approval
                telegram_message_id = send_tweet_for_approval(
                    article_summary=article.get("article_summary", ""),
                    tweet_text=tweet_text,
                    article_id=article_id,
                )

                # Update record with Telegram message ID (placeholder)
                update_telegram_message_id(record_id, telegram_message_id)

                processed_count += 1
                logger.info(f"Processed article {article_id} (record_id={record_id})")

            except Exception as e:
                logger.error(f"Failed to process tweet for article_id={tweet_data.get('article_id', 'unknown')}: {e}")
                # Continue processing other tweets
                continue

        logger.info(f"Webhook processing complete: {processed_count}/{len(generated_tweets)} tweets processed")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Processing complete",
                    "processed": processed_count,
                    "total": len(generated_tweets),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
        }


# Vercel serverless function entry point
# Vercel will call this function with a request object
def vercel_handler(req: Any) -> Dict[str, Any]:
    """
    Vercel serverless function entry point.

    Args:
        req: Vercel request object with .body and .headers attributes.

    Returns:
        HTTP response dictionary with statusCode and body.
    """
    try:
        # Extract body - Vercel provides it as bytes or string
        body = req.body
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        if isinstance(body, str):
            body = json.loads(body) if body else {}
        else:
            body = body or {}

        request_dict = {
            "body": body,
            "headers": dict(req.headers) if hasattr(req, "headers") else {},
        }
        return handler(request_dict)
    except Exception as e:
        logger.error(f"Error in vercel_handler: {e}")
        logger.error(traceback.format_exc())
        # Also print to stderr for Vercel to capture
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
        }

