"""Functions for generating tweets from Guardian articles."""

import logging
from typing import Any, Dict

from src.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a social media content creator focused on AI safety and existential risks.
Your task is to create concise, engaging tweets that highlight important developments in AI research
that could pose risks to humanity. The tweets should be informative, urgent but not alarmist,
and encourage awareness of these critical issues.

Keep tweets under 280 characters. Use clear, accessible language."""

USER_PROMPT_TEMPLATE = """Create a tweet about this article:

Title: {title}
Summary: {trail_text}
URL: {url}
Published: {published_date}

Generate a compelling tweet that captures the key risk or development mentioned in this article."""


def generate_tweet_from_article(
    article: Dict[str, Any],
    openai_client: OpenAIClient,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
) -> str:
    """
    Generate a tweet from a Guardian article using OpenAI.

    Args:
        article: Article dictionary with fields: title, trailText, webUrl, publishedDate.
        openai_client: OpenAI client instance.
        model: OpenAI model to use.
        temperature: Temperature setting for generation.

    Returns:
        Generated tweet text.

    Raises:
        Exception: If tweet generation fails.
    """
    try:
        logger.info(f"Generating tweet for article: {article.get('id', 'unknown')}")
        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=article.get("title", ""),
            trail_text=article.get("trailText", ""),
            url=article.get("webUrl", ""),
            published_date=article.get("publishedDate", ""),
        )

        tweet_text = openai_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        )

        logger.info(f"Successfully generated tweet (length: {len(tweet_text)})")
        return tweet_text

    except Exception as e:
        logger.error(f"Failed to generate tweet from article: {e}")
        raise

