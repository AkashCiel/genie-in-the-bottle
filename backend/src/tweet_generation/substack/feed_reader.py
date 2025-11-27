"""Functions for reading and parsing Substack RSS feeds."""

import logging
from typing import Any, Dict, List

import feedparser

logger = logging.getLogger(__name__)


def read_substack_feed(feed_url: str) -> List[Dict[str, Any]]:
    """
    Read and parse a Substack RSS feed.
    
    Args:
        feed_url: URL of the Substack RSS feed (format: https://<account>.substack.com/feed)
        
    Returns:
        List of article dictionaries with keys: title, link, content
    """
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning(f"Feed parsing warnings for {feed_url}: {feed.bozo_exception}")
        
        articles = []
        for entry in feed.entries:
            article = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "content": entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
            }
            articles.append(article)
            logger.debug(f"Parsed article: {article['title']}")
        
        logger.info(f"Successfully parsed {len(articles)} articles from {feed_url}")
        return articles
        
    except Exception as e:
        logger.error(f"Error reading Substack feed {feed_url}: {e}")
        raise


def load_substack_accounts(config_path: str = "backend/config/substack_accounts.yaml") -> List[str]:
    """
    Load Substack account names from config file.
    
    Args:
        config_path: Path to the YAML config file.
        
    Returns:
        List of account names.
    """
    import yaml
    import os
    
    # Handle both absolute and relative paths
    if not os.path.isabs(config_path):
        # Try to find the config relative to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(project_root, config_path)
    
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

