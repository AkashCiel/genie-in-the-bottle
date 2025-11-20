"""Configuration management for environment variables."""

import os

from dotenv import load_dotenv


class Config:
    """Centralized configuration loaded from environment variables."""

    def __init__(self) -> None:
        """Load environment variables from .env file."""
        load_dotenv()

    # OpenAI Configuration
    @property
    def openai_api_key(self) -> str:
        """OpenAI API key."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return key

    # X (Twitter) API Configuration
    @property
    def x_api_key(self) -> str:
        """X API consumer key."""
        key = os.getenv("API_Key")
        if not key:
            raise ValueError("API_Key environment variable is required")
        return key

    @property
    def x_api_secret(self) -> str:
        """X API consumer secret."""
        secret = os.getenv("API_Key_Secret")
        if not secret:
            raise ValueError("API_Key_Secret environment variable is required")
        return secret

    @property
    def x_access_token(self) -> str:
        """X API access token."""
        token = os.getenv("Access_Token")
        if not token:
            raise ValueError("Access_Token environment variable is required")
        return token

    @property
    def x_access_token_secret(self) -> str:
        """X API access token secret."""
        secret = os.getenv("Access_Token_Secret")
        if not secret:
            raise ValueError("Access_Token_Secret environment variable is required")
        return secret

    # Telegram Bot Configuration
    @property
    def telegram_bot_token(self) -> str:
        """Telegram bot token."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        return token

    @property
    def telegram_chat_id(self) -> str:
        """Telegram chat ID for approval messages."""
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
        return chat_id

    # Neon Database Configuration
    @property
    def database_url(self) -> str:
        """Neon database connection URL."""
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is required")
        return url


# Global config instance
config = Config()

