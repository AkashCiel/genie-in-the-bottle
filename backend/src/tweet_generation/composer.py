"""Functions for generating tweets from Guardian articles."""

import json
import logging
from typing import Any, Dict, List

from src.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


BATCH_SYSTEM_PROMPT = """Your objective is to carefully read the article to find information about one or more of the following undesired scenarios coming true, either directly or indirectly. 
I will list the scenarios and provide some explanatory context. If you find such information, prepare the concise tweet, within 200 characters, that summarises the reported development and how it relates to the specific undesired scenario.
1. Abuse of AI by bad actors at a massive scale. Bad actors could be a nation launching hostilities against another nation, an organised group (like biohackers developing a synthetic bioweapon), or even a single individual with misanthropic motivations.
2. Development of a misaligned AI. Here, misaligned could mean two things. The AI could unintentionally develop internal drives that makes it act in ways that are misaligned with its intended purposes. Let’s call this stupid misalignment. Misaligned could also mean the AI developing internal drives that are different from what the researchers intended and the AI understands this. In this case, the AI is actively trying to achieve its internal objectives, attract resources for compute, training et cetera and avoid being shut down by the researchers. This is when the AI is adversarially misaligned.
3. Massive disruption due to AI. Disruption could mean any large-scale event in geopolitics, society or global economy that has negative consequences for most people.

You will receive multiple articles. For each article, find all unique points signalling one of the above scenarios. Generate one tweet per unique point, in 200 characters or less. If you find none, return ‘Not found’ against that article ID

IMPORTANT: You must return your output as a valid JSON object ONLY, with no additional text before or after.
The JSON format must be:
{
  "article_id_1": "tweet text for article 1",
  "article_id_1": "another tweet text for article 1",
  "article_id_2": "tweet text for article 2",
  ...
}

Where the keys are the exact article IDs provided, and values are the generated tweet text (under 200 characters each).
Use clear, accessible language."""


def aggregate_articles_for_batch_generation(articles: List[Dict[str, Any]]) -> str:
    """
    Aggregate articles into a formatted string for batch tweet generation.

    Args:
        articles: List of article dictionaries with 'id' and 'article_summary' fields.

    Returns:
        Formatted string containing all articles for the user prompt.
    """
    formatted_articles = []
    for idx, article in enumerate(articles, start=1):
        article_id = article.get("id", "")
        article_summary = article.get("article_summary", "")
        formatted_articles.append(
            f"Article {idx}:\nID: {article_id}\nSummary: {article_summary}\n"
        )
    return "\n".join(formatted_articles)


def parse_batch_tweet_output(openai_output: str) -> List[Dict[str, str]]:
    """
    Parse OpenAI batch output JSON into a list of article_id and tweet_text pairs.

    Args:
        openai_output: Raw OpenAI response string (should be JSON).

    Returns:
        List of dictionaries with 'article_id' and 'tweet_text' keys.

    Raises:
        ValueError: If parsing fails or output is not valid JSON.
    """
    try:
        # Try to extract JSON if there's any surrounding text
        output = openai_output.strip()
        
        # Find JSON object boundaries
        start_idx = output.find("{")
        end_idx = output.rfind("}")
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in OpenAI output")
        
        json_str = output[start_idx : end_idx + 1]
        parsed = json.loads(json_str)
        
        # Convert to list of dicts
        result = [
            {"article_id": article_id, "tweet_text": tweet_text}
            for article_id, tweet_text in parsed.items()
        ]
        
        logger.info(f"Successfully parsed {len(result)} tweets from batch output")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI output: {e}")
        logger.error(f"Raw output: {openai_output}")
        raise ValueError(f"Invalid JSON in OpenAI output: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error parsing batch output: {e}")
        logger.error(f"Raw output: {openai_output}")
        raise


def generate_tweets_batch(
    articles: List[Dict[str, Any]],
    openai_client: OpenAIClient,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
) -> List[Dict[str, str]]:
    """
    Generate tweets for multiple articles in a single OpenAI API call.

    Args:
        articles: List of article dictionaries with 'id' and 'article_summary' fields.
        openai_client: OpenAI client instance.
        model: OpenAI model to use.
        temperature: Temperature setting for generation.

    Returns:
        List of dictionaries with 'article_id' and 'tweet_text' keys.

    Raises:
        Exception: If batch generation fails.
    """
    try:
        logger.info(f"Generating tweets for {len(articles)} articles in batch")
        
        # Aggregate articles into user prompt
        user_prompt = aggregate_articles_for_batch_generation(articles)
        full_user_prompt = f"Generate one tweet per article:\n\n{user_prompt}\n\nReturn only valid JSON as specified."
        
        # Make OpenAI API call
        raw_output = openai_client.generate(
            system_prompt=BATCH_SYSTEM_PROMPT,
            user_prompt=full_user_prompt,
            model=model,
            temperature=temperature,
        )
        
        # Parse output
        parsed_tweets = parse_batch_tweet_output(raw_output)
        
        logger.info(f"Successfully generated {len(parsed_tweets)} tweets in batch")
        return parsed_tweets
        
    except Exception as e:
        logger.error(f"Failed to generate tweets in batch: {e}")
        raise

