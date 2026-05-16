"""
notifier.py — Desktop notification dispatcher for CaseWatch.

Sends system tray notifications for overdue FIR cases.
Supports both individual and batch (summary) notifications.
Notification click opens the monitored Excel file.
"""

import os
import platform
import subprocess
from typing import List, Optional

from PyQt5.QtWidgets import QSystemTrayIcon

from app_logger import get_logger
from config import get_config
from models import Case

logger = get_logger("notifier")


class Notifier:
    """
    Dispatches desktop notifications for overdue cases.

    Uses PyQt5's QSystemTrayIcon for cross-platform notifications.
    Supports click-to-open for the monitored Excel file.
    """

    def __init__(self, tray_icon: QSystemTrayIcon) -> None:
        """
        Initialize the notifier.

        Args:
            tray_icon: The application's system tray icon instance.
        """
        self._tray = tray_icon

    def send_notification(self, case: Case) -> None:
        """
        Send a desktop notification for a single overdue case.

        Notification contains:
          - FIR number
          - Officer name
          - Overdue duration

        Args:
            case: The overdue Case object.
        """
        title = f"Overdue FSL: {case.display_id}"
        message = (
            f"Officer: {case.officer_display}\n"
            f"Overdue by {case.overdue_days} days\n"
            f"Allotted: {case.date_allotment}"
        )

        try:
            self._tray.showMessage(
                title,
                message,
                QSystemTrayIcon.Warning,
                10000,  # Display for 10 seconds
            )
            # macOS fallback: QSystemTrayIcon.showMessage() often fails silently
            if platform.system() == "Darwin":
                self._send_macos_notification(title, message)
            logger.info(
                "Notification sent: FSL=%s, Officer=%s, Overdue=%d days",
                case.display_id,
                case.officer_display,
                case.overdue_days,
            )
        except Exception as e:
            logger.error("Failed to send notification for %s: %s", case.display_id, e)

    def send_batch_notification(self, cases: List[Case]) -> None:
        """
        Send a summary notification when many cases are overdue.

        Used when the number of overdue cases exceeds the batch threshold
        to avoid flooding the user with individual notifications.

        Args:
            cases: List of overdue Case objects.
        """
        count = len(cases)
        title = f"{count} Overdue FSL Cases"

        # Format summaries for FIRs, Officers, and Overdue Days
        fir_preview = ", ".join(c.display_id for c in cases[:3])
        officer_preview = ", ".join(c.officer_display for c in cases[:3])
        overdue_preview = ", ".join(f"{c.overdue_days}d" for c in cases[:3])
        
        if count > 3:
            suffix = f" and {count - 3} more..."
            fir_preview += suffix
            officer_preview += suffix
            overdue_preview += suffix

        message = (
            f"FSLs: {fir_preview}\n"
            f"Officers: {officer_preview}\n"
            f"Overdue: {overdue_preview}"
        )

        try:
            self._tray.showMessage(
                title,
                message,
                QSystemTrayIcon.Warning,
                15000,  # Display for 15 seconds
            )
            # macOS fallback
            if platform.system() == "Darwin":
                self._send_macos_notification(title, message)
            logger.info("Batch notification sent for %d cases", count)
        except Exception as e:
            logger.error("Failed to send batch notification: %s", e)

    @staticmethod
    def _send_macos_notification(title: str, message: str) -> None:
        """
        Send a native macOS notification using osascript in a background thread.
        Shows an alert with 'Close' and 'Open Excel' options.
        """
        import threading

        def run_script():
            try:
                # Escape double quotes for AppleScript
                safe_title = title.replace('"', '\\"')
                safe_message = message.replace('"', '\\"').replace('\n', '\\n')
                script = (
                    f'display alert "{safe_title}" '
                    f'message "{safe_message}" '
                    f'as warning '
                    f'buttons {{"Close", "Open Excel"}} '
                    f'default button "Close" '
                    f'giving up after 60'
                )
                
                # Run the script and capture output
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                
                # Check if user clicked 'Open Excel'
                if "button returned:Open Excel" in result.stdout:
                    Notifier.open_excel_file()
            except Exception as e:
                logger.warning("macOS native notification failed: %s", e)

        # Start in a background thread so we don't block the Qt event loop
        threading.Thread(target=run_script, daemon=True).start()

    @staticmethod
    def open_excel_file(file_path: Optional[str] = None) -> None:
        """
        Open the Excel file in the default application.

        Args:
            file_path: Path to the Excel file. If None, uses config path.
        """
        if file_path is None:
            file_path = get_config().excel_file_path

        if not file_path or not os.path.exists(file_path):
            logger.warning("Cannot open Excel: file not found at %s", file_path)
            return

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])

            logger.info("Opened Excel file: %s", file_path)
        except Exception as e:
            logger.error("Failed to open Excel file: %s", e)
