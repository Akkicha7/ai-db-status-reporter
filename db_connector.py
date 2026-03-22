"""
db_connector.py
───────────────
Handles PostgreSQL connection dynamically using selected DB config
"""

import psycopg2
import logging

logger = logging.getLogger(__name__)


def get_connection(db_config):
    """
    Connect to PostgreSQL using selected database config
    """
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            dbname=db_config["dbname"],
            sslmode="require"
        )
        logger.info(f"Connected to DB: {db_config['name']}")
        return conn

    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise e