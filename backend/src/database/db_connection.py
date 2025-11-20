"""Shared database connection utilities."""

import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg2

from src.config import config

logger = logging.getLogger(__name__)


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    """Context manager that yields a psycopg2 connection to the Neon database."""
    conn = None
    try:
        conn = psycopg2.connect(config.database_url)
        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to close Postgres connection")

