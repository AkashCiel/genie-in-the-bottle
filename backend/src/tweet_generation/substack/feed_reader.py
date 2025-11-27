"""Functions for reading and parsing Substack RSS feeds."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# Project root: Use GITHUB_WORKSPACE in CI, otherwise calculate from file location
_PROJECT_ROOT = Path(os.getenv("GITHUB_WORKSPACE"))


def read_substack_feed(feed_url: str) -> List[Dict[str, Any]]:
    """
    Read and parse a Substack RSS feed using rss2json API.
    
    Uses rss2json.com API to convert RSS to JSON, which handles malformed XML
    and encoding issues better than direct feedparser parsing.
    
    Args:
        feed_url: URL of the Substack RSS feed (format: https://<account>.substack.com/feed)
        
    Returns:
        List of article dictionaries with keys: title, link, content
    """
    try:
        # Use rss2json API to convert RSS to JSON (handles malformed XML better)
        api_url = f"https://api.rss2json.com/v1/api.json?rss_url={quote(feed_url, safe='')}"
        
        logger.debug(f"Fetching RSS feed via rss2json API: {api_url}")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") != "ok":
            error_msg = data.get("message", "Unknown error from rss2json API")
            raise ValueError(f"rss2json API returned error: {error_msg}")
        
        items = data.get("items", [])
        if not items:
            logger.warning(f"No items found in RSS feed: {feed_url}")
            return []
        
        articles = []
        for item in items:
            # rss2json returns: title, link, description (content), content (sometimes), pubDate, etc.
            article = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                # Use 'content' if available, otherwise fall back to 'description'
                "content": item.get("content", "") or item.get("description", ""),
            }
            articles.append(article)
            logger.debug(f"Parsed article: {article['title']}")
        
        logger.info(f"Successfully parsed {len(articles)} articles from {feed_url}")
        return articles
        
    except requests.RequestException as e:
        logger.error(f"HTTP error reading Substack feed {feed_url}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading Substack feed {feed_url}: {e}")
        raise


def load_substack_accounts(config_path: str = "backend/config/substack_accounts.yaml") -> List[str]:
    """
    Load Substack account names from config file.
    
    Args:
        config_path: Path to the YAML config file (relative to project root if not absolute).
        
    Returns:
        List of account names.
    """
    import yaml
    
    # Handle both absolute and relative paths
    if not os.path.isabs(config_path):
        # Resolve relative to project root
        config_path = str(_PROJECT_ROOT / config_path)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            accounts = config.get("accounts", [])
            logger.info(f"Loaded {len(accounts)} Substack accounts from config")
            return accounts
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        raise


def get_substack_feed_url(account_name: str) -> str:
    """
    Generate RSS feed URL for a Substack account.
    
    Args:
        account_name: Substack account name.
        
    Returns:
        RSS feed URL.
    """
    return f"https://{account_name}.substack.com/feed"

