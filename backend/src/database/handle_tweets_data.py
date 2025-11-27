"""Functions for manipulating tweet records stored in Neon."""

import logging
from typing import Any, Dict, Optional

from psycopg2.extras import RealDictCursor

from src.database.db_connection import get_connection

logger = logging.getLogger(__name__)

TWEETS_TABLE = "gib_tweets"


def create_tweet_record(
    article_id: str,
    article_title: str,
    tweet_text: str,
    web_url: str,
    telegram_message_id: Optional[str] = None,
) -> str:
    """Insert a tweet record with pending statuses and return its ID."""
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
        VALUES (%s, %s, %s, %s, 'pending', 'pending', %s)
        RETURNING id
    """

    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (article_id, article_title, tweet_text, web_url, telegram_message_id))
        record_id = cursor.fetchone()[0]
        conn.commit()
        logger.info("Created tweet record %s for article_id=%s", record_id, article_id)
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

