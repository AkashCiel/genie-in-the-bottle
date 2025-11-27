"""Utility functions for cleaning HTML content from Substack RSS feeds."""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def clean_substack_content(html_content: str) -> str:
    """
    Clean HTML content from Substack RSS feed to extract readable text.
    
    Removes:
    - Image tags and containers
    - Subscription widgets
    - Links (but keeps link text)
    - Excessive whitespace
    
    Args:
        html_content: Raw HTML content from RSS feed's <content:encoded> field.
        
    Returns:
        Cleaned plain text content suitable for LLM processing.
    """
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove image-related elements
        for img in soup.find_all("img"):
            img.decompose()
        for picture in soup.find_all("picture"):
            picture.decompose()
        for figure in soup.find_all("figure"):
            figure.decompose()
        for img_container in soup.find_all(class_=re.compile(r"image|captioned-image", re.I)):
            img_container.decompose()
        
        # Remove subscription widgets
        for widget in soup.find_all(class_=re.compile(r"subscription-widget", re.I)):
            widget.decompose()
        
        # Replace links with their text content
        for link in soup.find_all("a"):
            link_text = link.get_text(strip=True)
            link.replace_with(link_text if link_text else "")
        
        # Extract text while preserving paragraph structure
        # Get text from all block elements
        text_parts = []
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]):
            text = element.get_text(separator=" ", strip=True)
            if text:
                text_parts.append(text)
        
        # If no block elements found, get all text
        if not text_parts:
            text_parts.append(soup.get_text(separator=" ", strip=True))
        
        # Join paragraphs with double newlines, then normalize whitespace
        cleaned = "\n\n".join(text_parts)
        
        # Normalize whitespace: collapse multiple spaces/newlines
        cleaned = re.sub(r"[ \t]+", " ", cleaned)  # Multiple spaces to single
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # Multiple newlines to double
        cleaned = cleaned.strip()
        
        return cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning Substack content: {e}")
        # Fallback: try to extract text directly
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            logger.error("Failed to extract text even with fallback")
            return ""

