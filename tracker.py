"""
tracker.py — Reminder state tracking for CaseWatch.

Manages reminders.json to track notification cooldowns per case.
Prevents duplicate notifications by enforcing cooldown intervals.
Thread-safe JSON read/write operations.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app_logger import get_logger
from config import BASE_DIR, get_config

logger = get_logger("tracker")

# Data directory
DATA_DIR = BASE_DIR / "data"
REMINDERS_FILE = DATA_DIR / "reminders.json"


class ReminderTracker:
    """
    Tracks when notifications were last issued for each case.

    Uses a JSON file to persist state across application restarts.
    Enforces cooldown intervals to prevent notification flooding.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load reminder data from disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not REMINDERS_FILE.exists():
            self._data = {}
            return

        with self._lock:
            try:
                with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self._data = {}
                    else:
                        self._data = json.loads(content)
                        if not isinstance(self._data, dict):
                            logger.warning(
                                "reminders.json contains non-dict data, resetting"
                            )
                            self._data = {}
                logger.info(
                    "Loaded reminder tracking for %d cases", len(self._data)
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.error(
                    "Failed to load reminders.json (resetting): %s", e
                )
                self._data = {}

    def _save(self) -> None:
        """Persist reminder data to disk."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except OSError as e:
            logger.error("Failed to save reminders.json: %s", e)

    def should_notify(self, case_id: str) -> bool:
        """
        Check if a notification should be sent for the given case.

        Returns True if:
          - The case has never been notified, OR
          - The cooldown period has elapsed since last notification.

        Args:
            case_id: Unique case identifier.

        Returns:
            True if notification should be sent.
        """
        config = get_config()
        cooldown = timedelta(minutes=config.reminder_cooldown_minutes)

        with self._lock:
            entry = self._data.get(case_id)

        if entry is None:
            return True

        last_notified_str = entry.get("last_notified")
        if not last_notified_str:
            return True

        try:
            last_notified = datetime.fromisoformat(last_notified_str)
            # Grace period is at most 10% of the cooldown, capped at 5 seconds
            grace_seconds = min(5.0, cooldown.total_seconds() * 0.1)
            grace_period = timedelta(seconds=grace_seconds)
            return datetime.now() - last_notified >= (cooldown - grace_period)
        except (ValueError, TypeError):
            logger.warning(
                "Invalid timestamp for case %s, allowing notification", case_id
            )
            return True

    def record_notification(self, case_id: str) -> None:
        """
        Record that a notification was sent for the given case.

        Args:
            case_id: Unique case identifier.
        """
        with self._lock:
            self._data[case_id] = {
                "last_notified": datetime.now().isoformat()
            }
            self._save()

        logger.debug("Recorded notification for case: %s", case_id)

    def clear_case(self, case_id: str) -> None:
        """
        Remove tracking data for a resolved case.

        Args:
            case_id: Unique case identifier.
        """
        with self._lock:
            if case_id in self._data:
                del self._data[case_id]
                self._save()
                logger.debug("Cleared tracking for resolved case: %s", case_id)

    def clear_all(self) -> None:
        """Clear all tracking data."""
        with self._lock:
            self._data = {}
            self._save()
        logger.info("All reminder tracking data cleared")

    def get_last_notified(self, case_id: str) -> Optional[datetime]:
        """
        Get the last notification timestamp for a case.

        Returns:
            datetime of last notification, or None if never notified.
        """
        with self._lock:
            entry = self._data.get(case_id)

        if entry is None:
            return None

        try:
            return datetime.fromisoformat(entry.get("last_notified", ""))
        except (ValueError, TypeError):
            return None

    @property
    def tracked_count(self) -> int:
        """Number of cases currently being tracked."""
        with self._lock:
            return len(self._data)
