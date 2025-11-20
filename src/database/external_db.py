"""Functions for reading from external Juggernaut/Neon database."""

import json
import logging
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import config

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
    try:
        logger.info(f"Fetching articles for user_id={user_id}, created_at={created_at}")
        conn = psycopg2.connect(config.external_db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # TODO: Replace 'your_table_name' with actual table name from Juggernaut database
        query = """
            SELECT curated_articles
            FROM your_table_name
            WHERE user_id = %s AND created_at = %s
            LIMIT 1
        """
        cursor.execute(query, (user_id, created_at))
        result = cursor.fetchone()

        if not result:
            logger.warning(f"No articles found for user_id={user_id}, created_at={created_at}")
            return []

        # Parse JSON blob
        curated_articles_json = result["curated_articles"]
        if isinstance(curated_articles_json, str):
            articles = json.loads(curated_articles_json)
        else:
            articles = curated_articles_json

        cursor.close()
        conn.close()

        logger.info(f"Successfully fetched {len(articles)} articles")
        return articles

    except Exception as e:
        logger.error(f"Failed to fetch articles from external DB: {e}")
        raise

