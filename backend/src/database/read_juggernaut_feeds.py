"""Functions for reading from external Juggernaut/Neon database."""

import json
import logging
from typing import Any, Dict, List

from psycopg2.extras import RealDictCursor

from src.database.db_connection import get_connection

logger = logging.getLogger(__name__)


def fetch_articles_by_user_and_date(user_id: str, created_at: str) -> List[Dict[str, Any]]:
    """
    Fetch curated articles from external Neon database.

    Args:
        user_id: User ID to query.
        created_at: Created at timestamp to query.

    Returns:
        List of article dictionaries with fields:
        - id: Article ID
        - title: Article title
        - webUrl: Article URL
        - section: Section name
        - trailText: Article summary
        - publishedDate: Publication date
        - relevanceScore: Relevance score

    Raises:
        Exception: If database query fails.
    """
    logger.info("Fetching articles for user_id=%s, created_at=%s", user_id, created_at)
    query = """
        SELECT curated_articles
        FROM curated_feeds
        WHERE user_id = %s AND created_at = %s
        LIMIT 1
    """

    try:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (user_id, created_at))
            result = cursor.fetchone()

            if not result:
                logger.warning(
                    "No articles found for user_id=%s, created_at=%s", user_id, created_at
                )
                return []

            curated_articles_json = result["curated_articles"]
            if isinstance(curated_articles_json, str):
                articles = json.loads(curated_articles_json)
            else:
                articles = curated_articles_json

            logger.info("Successfully fetched %s articles", len(articles))
            return articles
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch articles from Neon: %s", exc)
        raise

