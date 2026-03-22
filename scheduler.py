"""
scheduler.py
────────────
Runs the reporting pipeline on a weekly schedule using the `schedule` library.

By default reads SCHEDULE_DAY and SCHEDULE_TIME from config (set via .env).
Defaults: every Monday at 08:00 UTC.

Usage:
    python scheduler.py

Keep this process running (e.g. via systemd, supervisor, screen, or nohup):
    nohup python scheduler.py > logs/scheduler.log 2>&1 &

Alternatively, use a cron job (no need to run scheduler.py):
    0 8 * * 1 /path/to/venv/bin/python /path/to/main.py >> /path/to/logs/cron.log 2>&1
"""

import logging
import signal
import sys
import time

import schedule

import config

# Logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def job():
    """The scheduled task: import and run the full pipeline."""
    logger.info("Scheduled run triggered.")
    # Import here so any config changes are picked up at runtime
    from main import run_pipeline
    try:
        success = run_pipeline()
        if success:
            logger.info("Scheduled run completed successfully.")
        else:
            logger.warning("Scheduled run completed with errors.")
    except Exception as exc:
        logger.error("Unhandled exception during scheduled run: %s", exc, exc_info=True)


def _register_schedule():
    """Register the weekly job based on config."""
    day = config.SCHEDULE_DAY.lower()
    time_str = config.SCHEDULE_TIME  # e.g. "08:00"

    schedule_map = {
        "monday":    schedule.every().monday,
        "tuesday":   schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday":  schedule.every().thursday,
        "friday":    schedule.every().friday,
        "saturday":  schedule.every().saturday,
        "sunday":    schedule.every().sunday,
    }

    if day not in schedule_map:
        logger.warning(
            "Invalid SCHEDULE_DAY '%s'. Defaulting to 'monday'.", day
        )
        day = "monday"

    schedule_map[day].at(time_str).do(job)
    logger.info(
        "Scheduler registered: every %s at %s UTC.", day.capitalize(), time_str
    )


def _handle_signal(signum, frame):
    logger.info("Received signal %s — shutting down scheduler.", signum)
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("AI Database Health Reporter — Scheduler Starting")
    logger.info("Schedule: %s at %s UTC", config.SCHEDULE_DAY, config.SCHEDULE_TIME)

    _register_schedule()

    logger.info(
        "Next scheduled run: %s",
        schedule.next_run(),
    )
    logger.info("Scheduler running. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)   # check every 30 seconds


if __name__ == "__main__":
    main()
