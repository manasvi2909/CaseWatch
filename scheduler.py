"""
scheduler.py — Periodic scan scheduler for CaseWatch.

Uses QTimer for non-blocking periodic execution of the scan cycle.
Orchestrates: Excel scan → overdue detection → notifications → highlighting.
"""

from typing import List, Optional, Set

from PyQt5.QtCore import QTimer, QObject, pyqtSignal

from app_logger import get_logger
from config import get_config
from excel_handler import scan_excel, highlight_overdue_rows
from models import Case
from notifier import Notifier
from tracker import ReminderTracker

logger = get_logger("scheduler")


class Scheduler(QObject):
    """
    Manages periodic scanning of the Excel workbook.

    Emits signals to update the UI with scan results.
    All scan logic runs on the main thread via QTimer to avoid
    threading issues with PyQt5.
    """

    # Signals for UI updates
    scan_completed = pyqtSignal(list, list)  # all_cases, overdue_cases
    scan_error = pyqtSignal(str)  # error message
    scan_started = pyqtSignal()

    def __init__(
        self,
        notifier: Notifier,
        tracker: ReminderTracker,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._notifier = notifier
        self._tracker = tracker
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.scan_now)
        self._running = False
        self._previous_overdue_rows: Set[int] = set()

    def start(self) -> None:
        """Start periodic scanning at the configured interval."""
        config = get_config()
        # Scan at the same frequency as the user's reminder interval
        # so notifications fire on time
        interval_minutes = config.reminder_cooldown_minutes
        interval_ms = interval_minutes * 60 * 1000

        self._timer.start(interval_ms)
        self._running = True

        logger.info(
            "Scheduler started (interval: %d minutes)",
            interval_minutes,
        )

        # Run initial scan immediately
        self.scan_now()

    def stop(self) -> None:
        """Stop periodic scanning."""
        self._timer.stop()
        self._running = False
        logger.info("Scheduler stopped")

    def restart(self) -> None:
        """Restart scanning with potentially updated interval."""
        self.stop()
        self.start()

    @property
    def is_running(self) -> bool:
        return self._running

    def scan_now(self) -> None:
        """
        Execute a single scan cycle.

        1. Read Excel → get List[Case]
        2. Identify overdue cases
        3. Check notification cooldowns
        4. Send notifications (individual or batch)
        5. Update tracker timestamps
        6. Apply/remove row highlighting
        7. Emit signals for UI update
        """
        config = get_config()

        if not config.validate_excel_path():
            msg = "Excel file not configured or not found"
            logger.warning(msg)
            self.scan_error.emit(msg)
            return

        self.scan_started.emit()
        logger.info("--- Scan cycle started ---")

        try:
            # Step 1: Read Excel
            all_cases = scan_excel(
                config.excel_file_path,
                sheet_name=config.sheet_name,
            )

            if not all_cases:
                logger.info("No cases found in Excel")
                self.scan_completed.emit([], [])
                return

            # Step 2: Identify overdue cases
            threshold = config.overdue_threshold_days
            overdue_cases: List[Case] = [
                c for c in all_cases if c.is_overdue(threshold)
            ]
            resolved_cases: List[Case] = [
                c for c in all_cases
                if not c.is_overdue(threshold) and c.date_reporting is not None
            ]

            logger.info(
                "Scan results: %d total, %d overdue, %d resolved",
                len(all_cases),
                len(overdue_cases),
                len(resolved_cases),
            )

            # Step 3 & 4: Notifications
            cases_to_notify: List[Case] = []
            for case in overdue_cases:
                if self._tracker.should_notify(case.case_id):
                    cases_to_notify.append(case)

            if cases_to_notify:
                if len(cases_to_notify) > config.batch_notification_threshold:
                    # Batch mode
                    self._notifier.send_batch_notification(cases_to_notify)
                else:
                    # Individual notifications
                    for case in cases_to_notify:
                        self._notifier.send_notification(case)

                # Step 5: Update tracker
                for case in cases_to_notify:
                    self._tracker.record_notification(case.case_id)

            # Clear tracking for resolved cases
            for case in resolved_cases:
                self._tracker.clear_case(case.case_id)

            # Step 6: Highlighting
            current_overdue_rows = {c.row_index for c in overdue_cases}
            resolved_rows = self._previous_overdue_rows - current_overdue_rows
            new_overdue_rows = current_overdue_rows - self._previous_overdue_rows

            if new_overdue_rows or resolved_rows:
                highlight_overdue_rows(
                    config.excel_file_path,
                    overdue_rows=new_overdue_rows,
                    resolved_rows=resolved_rows,
                    color=config.highlight_color,
                )

            self._previous_overdue_rows = current_overdue_rows

            # Step 7: Signal UI
            self.scan_completed.emit(all_cases, overdue_cases)

            logger.info("--- Scan cycle completed ---")

        except Exception as e:
            logger.error("Scan cycle failed: %s", e, exc_info=True)
            self.scan_error.emit(str(e))
