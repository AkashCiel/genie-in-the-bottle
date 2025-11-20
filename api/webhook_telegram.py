"""Vercel API route handler for Telegram webhook."""

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
    from src.database.internal_db import get_tweet_by_telegram_message_id, update_approval_status, update_post_status
    from src.telegram.bot import parse_telegram_webhook, send_status_notification
    from src.x_platform.client import post_tweet
    logger.info("All modules imported successfully")
except Exception as e:
    logger.error(f"Failed to import modules: {e}")
    logger.error(traceback.format_exc())
    # Re-raise to fail fast and show error in Vercel
    raise


def handler(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle webhook request from Telegram.

    Expected request body: Telegram webhook format.

    Returns:
        HTTP response dictionary with statusCode and body.
    """
    try:
        # Parse request body
        if isinstance(request.get("body"), str):
            body = json.loads(request["body"])
        else:
            body = request.get("body", {})

        # Parse Telegram webhook data
        message_data = parse_telegram_webhook(body)
        if not message_data:
            logger.info("Received non-message update from Telegram, ignoring")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Not a message update"}),
            }

        # Check if this is a reply to a pending tweet
        reply_to_message_id = message_data.get("reply_to_message_id")
        if not reply_to_message_id:
            logger.info("Received message that is not a reply, ignoring")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Not a reply to a tweet"}),
            }

        # Get tweet record from internal DB (placeholder)
        tweet_record = get_tweet_by_telegram_message_id(reply_to_message_id)
        if not tweet_record:
            logger.warning(f"No tweet record found for telegram_message_id={reply_to_message_id}")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Tweet record not found"}),
            }

        # Determine approval status from reply text
        reply_text = message_data.get("text", "").strip().lower()
        record_id = tweet_record["id"]  # Assuming record has 'id' field

        if reply_text in ["/reject", "reject", "no"]:
            # Reject tweet
            update_approval_status(record_id, "rejected")
            logger.info(f"Tweet {record_id} rejected")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Tweet rejected"}),
            }

        # Approve tweet (either explicit approval or modified text)
        update_approval_status(record_id, "approved")

        # Determine tweet text to post
        original_tweet = tweet_record.get("tweet_text", "")
        if reply_text in ["/approve", "approve", "yes"]:
            # Approve as-is
            tweet_to_post = original_tweet
        else:
            # User provided modified text
            tweet_to_post = message_data.get("text", "").strip()

        # Post to X
        try:
            x_tweet_id = post_tweet(tweet_to_post)
            update_post_status(record_id, "posted", x_tweet_id)
            send_status_notification(f"✅ Tweet posted successfully!\nTweet ID: {x_tweet_id}")
            logger.info(f"Tweet {record_id} posted successfully to X (tweet_id={x_tweet_id})")

        except Exception as e:
            # Update post status to failed
            update_post_status(record_id, "failed")
            error_message = f"❌ Failed to post tweet to X: {str(e)}"
            send_status_notification(error_message)
            logger.error(f"Failed to post tweet {record_id} to X: {e}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Tweet processed"}),
        }

    except Exception as e:
        logger.error(f"Telegram webhook handler error: {e}")
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

