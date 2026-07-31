"""
scheduler.py — APScheduler-based weekly scan trigger.

Runs the device security scan every Friday at 08:00 local time.
The on_scan_complete callback is called with the scan report dict.
"""

import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config

logger = logging.getLogger(__name__)


class ScanScheduler:
    """Wraps APScheduler to fire the scan job every Friday morning."""

    def __init__(self, scan_fn: Callable[[], None]):
        """
        Parameters
        ----------
        scan_fn : Callable
            Zero-argument function to call when the scheduled scan fires.
        """
        self._scan_fn  = scan_fn
        try:
            self._scheduler = BackgroundScheduler(
                job_defaults={"misfire_grace_time": 3600},  # tolerate 1h miss
            )
        except Exception as e:
            logger.warning(f"BackgroundScheduler init fallback: {e}")
            self._scheduler = BackgroundScheduler()
        self._job = None

    def start(self):
        """Start the scheduler (non-blocking background thread)."""
        trigger = CronTrigger(
            day_of_week=config.SCAN_DAY_OF_WEEK,
            hour=config.SCAN_HOUR,
            minute=config.SCAN_MINUTE,
        )
        self._job = self._scheduler.add_job(
            self._run_scan,
            trigger=trigger,
            id="weekly_security_scan",
            replace_existing=True,
        )
        self._scheduler.start()

        next_run = self._job.next_run_time
        logger.info(
            f"Scheduler started. Next scan: "
            f"{next_run.strftime('%A %Y-%m-%d %H:%M') if next_run else 'N/A'}"
        )

    def stop(self):
        """Gracefully shut down the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def next_run_time(self) -> str:
        """Returns human-readable next scan time, or 'N/A'."""
        if self._job and self._job.next_run_time:
            return self._job.next_run_time.strftime("%A %d %b %Y at %H:%M")
        return "N/A"

    def _run_scan(self):
        logger.info("Scheduled scan triggered.")
        try:
            self._scan_fn()
        except Exception as e:
            logger.error(f"Scheduled scan failed: {e}", exc_info=True)
