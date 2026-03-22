"""
metrics_collector.py
────────────────────
Collects PostgreSQL metrics dynamically
"""

from datetime import datetime
from db_connector import get_connection
import logging

logger = logging.getLogger(__name__)


def collect(db_config):
    logger.info("Collecting PostgreSQL metrics...")

    with get_connection(db_config) as conn:
        cursor = conn.cursor()

        # 🔹 Active connections
        cursor.execute("SELECT count(*) FROM pg_stat_activity")
        active_connections = cursor.fetchone()[0]

        # 🔹 Max connections
        cursor.execute("SHOW max_connections")
        max_connections = int(cursor.fetchone()[0])

        connection_pct = round((active_connections / max_connections) * 100, 1)

        # 🔹 Database size (disk usage)
        cursor.execute("""
            SELECT pg_database_size(current_database()) / 1024 / 1024
        """)
        disk_used_mb = round(cursor.fetchone()[0], 2)

        # 🔹 Uptime (approx)
        cursor.execute("""
            SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))
        """)
        uptime_seconds = int(cursor.fetchone()[0])
        uptime_hours = round(uptime_seconds / 3600, 2)

        # 🔹 CPU approximation
        cpu_usage_pct = connection_pct  # simple approximation

        # 🔹 Placeholder metrics (PostgreSQL needs extensions for real values)
        slow_queries = 0
        avg_query_time_ms = 0
        error_count = 0

        metrics = {
            "collected_at": datetime.utcnow().isoformat(),

            "active_connections": active_connections,
            "max_connections": max_connections,
            "connection_pct": connection_pct,

            "cpu_usage_pct": cpu_usage_pct,

            "disk_used_mb": disk_used_mb,
            "disk_usage_pct": connection_pct,

            "uptime_seconds": uptime_seconds,
            "uptime_hours": uptime_hours,

            "slow_queries": slow_queries,
            "avg_query_time_ms": avg_query_time_ms,
            "error_count": error_count
        }
        DEMO_MODE = False
        if DEMO_MODE:
         if db_config["name"] == "Lab DB":
            metrics["cpu_usage_pct"] = 88
            metrics["connection_pct"] = 85

         if db_config["name"] == "Test DB":
           metrics["cpu_usage_pct"] = 95
           metrics["error_count"] = 20



        logger.info("Metrics collected successfully")
        return metrics