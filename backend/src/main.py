"""Main FastAPI application exposing webhook endpoints."""

import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request

from src.database.handle_tweets_data import (
    create_tweet_record,
    get_tweet_by_telegram_message_id,
    send_earliest_queued_tweet_for_approval,
    update_approval_status,
    update_post_status,
)
from src.database.read_juggernaut_feeds import fetch_articles_by_user_and_date
from src.openai_client import OpenAIClient
from src.telegram.bot import (
    parse_telegram_webhook,
    send_status_notification,
    send_tweet_for_approval,
)
from src.tweet_generation.guardian_composer import generate_tweets_batch
from src.x_platform.client import post_tweet

logger = logging.getLogger(__name__)
app = FastAPI(title="Genie in the Bottle Webhooks", version="0.1.0")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok", "service": "genie-in-the-bottle"}


def _validate_juggernaut_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    user_id = payload.get("user_id")
    created_at = payload.get("created_at")

    if not user_id or not created_at:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: user_id and created_at",
        )

    return {"user_id": user_id, "created_at": created_at}


@app.post("/webhook/juggernaut")
async def juggernaut_webhook(request: Request) -> Dict[str, Any]:
    """Handle webhook request from Juggernaut."""
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    params = _validate_juggernaut_payload(payload)
    user_id = params["user_id"]
    created_at = params["created_at"]

    logger.info("Processing Juggernaut webhook user_id=%s created_at=%s", user_id, created_at)

    articles = fetch_articles_by_user_and_date(user_id, created_at)
    if not articles:
        return {"message": "No articles found", "processed": 0}

    openai_client = OpenAIClient()

    try:
        generated_tweets = generate_tweets_batch(articles, openai_client)
    except Exception as exc:  # noqa: BLE001
        error_message = (
            "❌ Batch tweet generation failed\n\n"
            f"User ID: {user_id}\n"
            f"Created At: {created_at}\n"
            f"Error: {str(exc)}"
        )
        try:
            send_status_notification(error_message)
        except Exception as telegram_exc:  # noqa: BLE001
            logger.error("Failed to send Telegram notification: %s", telegram_exc)
        raise HTTPException(status_code=500, detail="Batch tweet generation failed") from exc

    article_map = {article.get("id", ""): article for article in articles}
    processed_count = 0

    for tweet_data in generated_tweets:
        article_id = tweet_data.get("article_id", "")
        tweet_text = tweet_data.get("tweet_text", "")
        article = article_map.get(article_id)

        if not article:
            logger.warning("Article ID %s from OpenAI output not found in DB results", article_id)
            continue

        web_url = article.get("webUrl")
        if not web_url:
            logger.warning("Article %s missing webUrl – skipping", article_id)
            continue

        try:
            create_tweet_record(
                article_id=article_id,
                article_title=article.get("title", ""),
                tweet_text=tweet_text,
                web_url=web_url,
                approval_status="queued",
            )
            processed_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to process tweet for article %s: %s", article_id, exc)
            continue

    # Send earliest queued tweet for approval
    send_earliest_queued_tweet_for_approval()

    return {
        "message": "Processing complete",
        "processed": processed_count,
        "total": len(generated_tweets),
    }


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """Handle webhook request from Telegram."""
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    message_data = parse_telegram_webhook(payload)
    if not message_data:
        return {"message": "Not a message update"}

    reply_to_message_id = message_data.get("reply_to_message_id")
    if not reply_to_message_id:
        return {"message": "Not a reply to a tweet"}

    try:
        tweet_record = get_tweet_by_telegram_message_id(reply_to_message_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read tweet record: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read tweet record") from exc

    if not tweet_record:
        return {"message": "Tweet record not found"}

    reply_text = (message_data.get("text") or "").strip()
    record_id = tweet_record["id"]
    lower_text = reply_text.lower()

    if lower_text in {"/reject", "reject", "no"}:
        update_approval_status(record_id, "rejected")
        # Send next queued tweet for approval
        send_earliest_queued_tweet_for_approval()
        return {"message": "Tweet rejected"}

    update_approval_status(record_id, "approved")
    original_tweet = tweet_record.get("tweet_text", "")
    web_url = tweet_record.get("web_url", "")

    if lower_text in {"/approve", "approve", "yes"}:
        tweet_to_post = original_tweet
    else:
        tweet_to_post = reply_text

    # Append web URL if available
    if web_url:
        tweet_to_post = f"{tweet_to_post}\n{web_url}"

    try:
        x_tweet_id = post_tweet(tweet_to_post)
        update_post_status(record_id, "posted", x_tweet_id)
        send_status_notification(f"✅ Tweet posted successfully!\nTweet ID: {x_tweet_id}")
        
        # Send next queued tweet for approval
        send_earliest_queued_tweet_for_approval()
        
        return {"message": "Tweet posted", "tweet_id": x_tweet_id}
    except Exception as exc:  # noqa: BLE001
        update_post_status(record_id, "failed")
        send_status_notification(f"❌ Failed to post tweet to X: {str(exc)}")
        raise HTTPException(status_code=500, detail="Failed to post tweet to X") from exc

