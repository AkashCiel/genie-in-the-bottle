"""Functions for manipulating tweet records stored in Neon."""

import logging
from typing import Any, Dict, Optional, Set

from psycopg2.extras import RealDictCursor

from src.database.db_connection import get_connection
from src.telegram.bot import send_tweet_for_approval

logger = logging.getLogger(__name__)

TWEETS_TABLE = "gib_tweets"


def create_tweet_record(
    article_id: str,
    article_title: str,
    tweet_text: str,
    web_url: str,
    telegram_message_id: Optional[str] = None,
    approval_status: str = "queued",
) -> str:
    """Insert a tweet record with specified approval status and return its ID."""
    query = f"""
        INSERT INTO {TWEETS_TABLE} (
            article_id,
            article_title,
            tweet_text,
            web_url,
            approval_status,
            post_status,
            telegram_message_id
        )
        VALUES (%s, %s, %s, %s, %s, 'pending', %s)
        RETURNING id
    """

    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (article_id, article_title, tweet_text, web_url, approval_status, telegram_message_id))
        record_id = cursor.fetchone()[0]
        conn.commit()
        logger.info("Created tweet record %s for article_id=%s with approval_status=%s", record_id, article_id, approval_status)
        return str(record_id)


def update_approval_status(record_id: str, approval_status: str) -> None:
    """Update approval status."""
    query = (
        f"UPDATE {TWEETS_TABLE} "
        "SET approval_status = %s, updated_at = NOW() "
        "WHERE id = %s"
    )
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (approval_status, record_id))
        conn.commit()
        logger.info("Updated approval status for %s to %s", record_id, approval_status)


def update_post_status(record_id: str, post_status: str, x_tweet_id: Optional[str] = None) -> None:
    """Update post status and optional tweet ID."""
    query = (
        f"UPDATE {TWEETS_TABLE} "
        "SET post_status = %s, x_tweet_id = %s, updated_at = NOW() "
        "WHERE id = %s"
    )
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (post_status, x_tweet_id, record_id))
        conn.commit()
        logger.info("Updated post status for %s to %s", record_id, post_status)


def get_tweet_by_telegram_message_id(telegram_message_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the tweet record associated with a Telegram message ID."""
    query = f"""
        SELECT *
        FROM {TWEETS_TABLE}
        WHERE telegram_message_id = %s
        LIMIT 1
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (telegram_message_id,))
        record = cursor.fetchone()
        return dict(record) if record else None


def update_telegram_message_id(record_id: str, telegram_message_id: str) -> None:
    """Store Telegram message ID after sending approval request."""
    query = (
        f"UPDATE {TWEETS_TABLE} "
        "SET telegram_message_id = %s, updated_at = NOW() "
        "WHERE id = %s"
    )
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (telegram_message_id, record_id))
        conn.commit()
        logger.info("Stored telegram_message_id for %s", record_id)


def get_earliest_queued_tweet() -> Optional[Dict[str, Any]]:
    """Fetch the earliest tweet with approval_status='queued', sorted by created_at."""
    query = f"""
        SELECT *
        FROM {TWEETS_TABLE}
        WHERE approval_status = 'queued'
        ORDER BY created_at ASC
        LIMIT 1
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        record = cursor.fetchone()
        return dict(record) if record else None


def get_all_existing_web_urls() -> Set[str]:
    """Fetch all unique web_url values from gib_tweets table."""
    query = f"SELECT DISTINCT web_url FROM {TWEETS_TABLE} WHERE web_url IS NOT NULL"
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
        web_urls = {row[0] for row in results}
        logger.info(f"Loaded {len(web_urls)} existing web URLs from database")
        return web_urls


def send_earliest_queued_tweet_for_approval() -> None:
    """
    Find the earliest queued tweet and send it to Telegram for approval.
    Updates its approval_status to 'pending'.
    """
    if _is_any_tweet_pending():
        logger.info("There are pending tweets in the pipeline")
        return
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
        logger.info("Sent earliest queued tweet for approval (record_id=%s)", record_id)
        
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send earliest queued tweet for approval: %s", exc)


def _is_any_tweet_pending() -> bool:
    """Check if there are any tweets with approval_status='pending'."""
    query = f"""
        SELECT COUNT(*) FROM {TWEETS_TABLE} WHERE approval_status = 'pending'
    """
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0] > 0