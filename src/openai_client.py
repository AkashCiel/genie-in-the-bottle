"""General-purpose OpenAI client for making API calls."""

import logging
from typing import Optional

from openai import OpenAI

from src.config import config

logger = logging.getLogger(__name__)


class OpenAIClient:
    """General-purpose OpenAI client for making API calls."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key. If not provided, uses config.
        """
        self.client = OpenAI(api_key=api_key or config.openai_api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> str:
        """
        Make an OpenAI API call and return the generated text.

        Args:
            system_prompt: System prompt for the API call.
            user_prompt: User prompt for the API call.
            model: OpenAI model to use (default: gpt-4o-mini).
            temperature: Temperature setting (default: 0.7).

        Returns:
            Generated text from OpenAI.

        Raises:
            Exception: If the API call fails.
        """
        try:
            logger.info(f"Making OpenAI API call with model: {model}, temperature: {temperature}")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("OpenAI returned empty response")
            logger.info("OpenAI API call successful")
            return generated_text.strip()
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

