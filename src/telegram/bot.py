"""Functions for sending and receiving Telegram messages."""

import logging
from typing import Optional

import requests

from src.config import config

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def send_tweet_for_approval(
    article_summary: str,
    tweet_text: str,
    article_id: str,
) -> str:
    """
    Send a tweet to Telegram for approval.

    Args:
        article_summary: Article summary (trailText from external DB).
        tweet_text: Generated tweet text.
        article_id: Guardian article ID for reference.

    Returns:
        Telegram message ID.

    Raises:
        Exception: If sending message fails.
    """
    try:
        message = f"{article_summary}\n\n{tweet_text}"
        url = f"{TELEGRAM_API_BASE}{config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": message,
        }

        logger.info(f"Sending tweet for approval to Telegram (article_id={article_id})")
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Telegram API error: {result.get('description')}")

        message_id = str(result["result"]["message_id"])
        logger.info(f"Successfully sent message to Telegram (message_id={message_id})")
        return message_id

    except Exception as e:
        logger.error(f"Failed to send message to Telegram: {e}")
        raise


def send_status_notification(message: str) -> None:
    """
    Send a status notification to Telegram.

    Args:
        message: Status message to send.

    Raises:
        Exception: If sending message fails.
    """
    try:
        url = f"{TELEGRAM_API_BASE}{config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": message,
        }

        logger.info("Sending status notification to Telegram")
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Telegram API error: {result.get('description')}")

        logger.info("Successfully sent status notification to Telegram")

    except Exception as e:
        logger.error(f"Failed to send status notification to Telegram: {e}")
        raise


def parse_telegram_webhook(webhook_data: dict) -> Optional[dict]:
    """
    Parse Telegram webhook data to extract message information.

    Args:
        webhook_data: Raw webhook data from Telegram.

    Returns:
        Dictionary with 'message_id', 'text', 'reply_to_message_id', 'chat_id',
        or None if not a valid message.
    """
    try:
        if "message" not in webhook_data:
            return None

        message = webhook_data["message"]
        if "text" not in message:
            return None

        return {
            "message_id": str(message["message_id"]),
            "text": message["text"],
            "reply_to_message_id": str(message.get("reply_to_message", {}).get("message_id", "")),
            "chat_id": str(message["chat"]["id"]),
        }
    except Exception as e:
        logger.error(f"Failed to parse Telegram webhook: {e}")
        return None

