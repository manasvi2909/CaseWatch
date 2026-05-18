"""
config.py — Configuration management for CaseWatch.

Loads, validates, and persists application settings from config.json.
Thread-safe singleton pattern ensures consistent config access.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional


# Base directory: where the application files live
BASE_DIR = Path(__file__).resolve().parent

# Default configuration values
DEFAULTS = {
    "excel_file_path": "",
    "scan_interval_minutes": 5,
    "reminder_cooldown": 30,
    "reminder_cooldown_unit": "minutes",
    "overdue_threshold_days": 13,
    "sheet_name": None,  # None = first sheet
    "auto_start": True,
    "highlight_color": "FFC7CE",  # openpyxl uses hex without #
    "log_level": "INFO",
    "max_backups": 10,
    "batch_notification_threshold": 1,
}

CONFIG_FILE = BASE_DIR / "config.json"


class _Config:
    """
    Singleton configuration manager.

    Reads from config.json on first access, merges with defaults,
    and provides thread-safe get/set operations.
    """

    _instance: Optional["_Config"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "_Config":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._data: dict[str, Any] = {}
        self._file_lock = threading.Lock()
        self._load()
        self._initialized = True

    def _load(self) -> None:
        """Load configuration from disk, merging with defaults."""
        self._data = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                if isinstance(user_config, dict):
                    self._data.update(user_config)
            except (json.JSONDecodeError, OSError) as e:
                # Corrupted config — fall back to defaults
                print(f"[Config] Warning: Failed to load config.json: {e}")

    def save(self) -> None:
        """Persist current configuration to disk."""
        with self._file_lock:
            try:
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, default=str)
            except OSError as e:
                print(f"[Config] Error: Failed to save config.json: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value (does not auto-save)."""
        self._data[key] = value

    @property
    def excel_file_path(self) -> str:
        return self._data.get("excel_file_path", "")

    @excel_file_path.setter
    def excel_file_path(self, value: str) -> None:
        self._data["excel_file_path"] = value

    @property
    def scan_interval_minutes(self) -> int:
        return int(self._data.get("scan_interval_minutes", 5))

    @property
    def reminder_cooldown(self) -> int:
        return int(self._data.get("reminder_cooldown", self._data.get("reminder_cooldown_minutes", 30)))

    @property
    def reminder_cooldown_unit(self) -> str:
        return str(self._data.get("reminder_cooldown_unit", "minutes"))

    @property
    def reminder_cooldown_minutes(self) -> float:
        if "reminder_cooldown_minutes" in self._data and "reminder_cooldown" not in self._data:
            return float(self._data["reminder_cooldown_minutes"])
        
        val = float(self.reminder_cooldown)
        unit = self.reminder_cooldown_unit.lower()
        if unit == "seconds":
            return val / 60.0
        elif unit == "hours":
            return val * 60.0
        return val # minutes

    @property
    def overdue_threshold_days(self) -> int:
        return int(self._data.get("overdue_threshold_days", 13))

    @property
    def sheet_name(self) -> Optional[str]:
        return self._data.get("sheet_name")

    @property
    def highlight_color(self) -> str:
        return self._data.get("highlight_color", "FFC7CE")

    @property
    def log_level(self) -> str:
        return self._data.get("log_level", "INFO")

    @property
    def max_backups(self) -> int:
        return int(self._data.get("max_backups", 10))

    @property
    def batch_notification_threshold(self) -> int:
        return int(self._data.get("batch_notification_threshold", 5))

    @property
    def auto_start(self) -> bool:
        return bool(self._data.get("auto_start", True))

    @property
    def is_first_run(self) -> bool:
        """True if no Excel file has been configured yet."""
        return not self.excel_file_path

    def validate_excel_path(self) -> bool:
        """Check if the configured Excel path exists and is a .xlsx file."""
        path = self.excel_file_path
        if not path:
            return False
        p = Path(path)
        return p.exists() and p.suffix.lower() == ".xlsx"

    def reload(self) -> None:
        """Force reload from disk."""
        self._load()


def get_config() -> _Config:
    """Get the singleton configuration instance."""
    return _Config()
