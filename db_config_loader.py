"""
db_config_loader.py
────────────────────
Loads database configurations from PostgreSQL
(Ensures no duplicates and clean structure)
"""

import psycopg2
import logging
import config

logger = logging.getLogger(__name__)


def get_all_db_configs():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dbname=config.DB_NAME
        )

        cursor = conn.cursor()

        # ✅ DISTINCT ON ensures no duplicates (extra safety)
        cursor.execute("""
            SELECT DISTINCT ON (host, port, username, db_name)
                id, name, host, port, username, password, db_name
            FROM db_configs
            ORDER BY host, port, username, db_name, id;
        """)

        rows = cursor.fetchall()
        conn.close()

        configs = []
        for r in rows:
            configs.append({
                "id": r[0],
                "name": r[1],
                "host": r[2],
                "port": r[3],
                "user": r[4],       # ⚠️ IMPORTANT: use 'user'
                "password": r[5],
                "dbname": r[6]      # ⚠️ IMPORTANT: use 'dbname'
            })

        logger.info(f"Loaded {len(configs)} DB configs")
        return configs

    except Exception as e:
        logger.error(f"Failed to load DB configs: {e}")
        return []