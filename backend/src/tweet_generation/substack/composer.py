"""Functions for generating tweets from Substack articles."""

import json
import logging
from typing import Any, Dict, List

from src.openai_client import OpenAIClient
from src.tweet_generation.substack.content_cleaner import clean_substack_content

logger = logging.getLogger(__name__)


SUBSTACK_SYSTEM_PROMPT = """Your objective is to carefully read the article to find information about one or more of the following undesired scenarios coming true, either directly or indirectly. 
I will list the scenarios and provide some explanatory context. If you find such information, prepare the concise tweet, within 200 characters, that summarises the reported development and how it relates to the specific undesired scenario.
1. Abuse of AI by bad actors at a massive scale. Bad actors could be a nation launching hostilities against another nation, an organised group (like biohackers developing a synthetic bioweapon), or even a single individual with misanthropic motivations.
2. Development of a misaligned AI. Here, misaligned could mean two things. The AI could unintentionally develop internal drives that makes it act in ways that are misaligned with its intended purposes. Let's call this stupid misalignment. Misaligned could also mean the AI developing internal drives that are different from what the researchers intended and the AI understands this. In this case, the AI is actively trying to achieve its internal objectives, attract resources for compute, training et cetera and avoid being shut down by the researchers. This is when the AI is adversarially misaligned.
3. Massive disruption due to AI. Disruption could mean any large-scale event in geopolitics, society or global economy that has negative consequences for most people.

You will receive a single article. Find all unique arguments signalling one of the above scenarios. Generate one tweet per argument, in 200 characters or less. If you find none, return 'Not found' as the value.

IMPORTANT: You must return your output as a valid JSON object ONLY, with no additional text before or after.
The JSON format must be:
{
  "tweets": [
    "first tweet text here",
    "second tweet text here",
    ...
  ]
}

Or if no relevant information is found:
{
  "tweets": ["Not found"]
}

Where the "tweets" array contains the generated tweet texts (each under 200 characters).
Use clear, accessible language."""


def parse_tweet_output(openai_output: str, article_id: str) -> List[Dict[str, str]]:
    """
    Parse OpenAI output JSON for a single article into a list of article_id and tweet_text pairs.
    
    Args:
        openai_output: Raw OpenAI response string (should be JSON).
        article_id: The article ID to use for all parsed tweets.
        
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
        
        # Extract tweets array from parsed JSON
        tweets_array = parsed.get("tweets", [])
        if not isinstance(tweets_array, list):
            raise ValueError("Expected 'tweets' to be an array in OpenAI output")
        
        # Convert to list of dicts (filter out "Not found" entries)
        result = [
            {"article_id": article_id, "tweet_text": tweet_text}
            for tweet_text in tweets_array
            if tweet_text and tweet_text.lower() != "not found"
        ]
        
        logger.info(f"Successfully parsed {len(result)} tweets for article {article_id}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI output: {e}")
        logger.error(f"Raw output: {openai_output}")
        raise ValueError(f"Invalid JSON in OpenAI output: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error parsing tweet output: {e}")
        logger.error(f"Raw output: {openai_output}")
        raise


def generate_tweet_single(
    article: Dict[str, Any],
    openai_client: OpenAIClient,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
) -> List[Dict[str, str]]:
    """
    Generate tweets for a single Substack article.
    
    Args:
        article: Article dictionary with 'title' (used as article_id), 'link', and 'content' fields.
                 Content should be raw HTML from RSS feed.
        openai_client: OpenAI client instance.
        model: OpenAI model to use.
        temperature: Temperature setting for generation.
        
    Returns:
        List of dictionaries with 'article_id' and 'tweet_text' keys.
        
    Raises:
        Exception: If generation fails.
    """
    try:
        article_id = article.get("title", "")
        logger.info(f"Generating tweet for Substack article: {article_id}")
        
        # Clean content
        raw_content = article.get("content", "")
        cleaned_content = clean_substack_content(raw_content)
        
        # Create user prompt
        user_prompt = f"Article ID: {article_id}\nContent: {cleaned_content}\n\nReturn only valid JSON as specified."
        
        # Make OpenAI API call
        raw_output = openai_client.generate(
            system_prompt=SUBSTACK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
        )
        
        # Parse output
        parsed_tweets = parse_tweet_output(raw_output, article_id)
        
        logger.info(f"Successfully generated {len(parsed_tweets)} tweets for article {article_id}")
        return parsed_tweets
        
    except Exception as e:
        logger.error(f"Failed to generate tweet for article {article.get('title', 'unknown')}: {e}")
        raise

