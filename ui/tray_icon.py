"""
tray_icon.py — System tray icon management for CaseWatch.

Provides:
  - System tray icon with context menu
  - Double-click to show main window
  - Notification click to open Excel file
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QAction,
    QWidget,
)

from app_logger import get_logger

logger = get_logger("tray_icon")


def _create_default_icon() -> QIcon:
    """
    Create a programmatic app icon if no icon file exists.

    Generates a simple "CW" icon with a professional color scheme.
    """
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Background circle
    painter.setBrush(QColor(41, 128, 185))  # Professional blue
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)

    # Text
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "CW")

    painter.end()
    return QIcon(pixmap)


def _create_warning_icon() -> QIcon:
    """Create an icon variant for when overdue cases exist."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Background circle — warning orange/red
    painter.setBrush(QColor(231, 76, 60))  # Alert red
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)

    # Text
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "CW")

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """
    System tray icon for CaseWatch.

    Features:
      - Context menu: Show Window, Scan Now, Open Excel, Quit
      - Double-click to show main window
      - Notification click to open Excel file
      - Icon changes color when overdue cases exist
    """

    def __init__(
        self,
        main_window: QWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        # Create default icon
        self._normal_icon = _create_default_icon()
        self._warning_icon = _create_warning_icon()

        super().__init__(self._normal_icon, parent)
        self._main_window = main_window
        self._has_overdue = False

        # Context menu
        self._create_context_menu()

        # Signals
        self.activated.connect(self._on_activated)
        self.messageClicked.connect(self._on_message_clicked)

        # Tooltip
        self.setToolTip("CaseWatch — FSL FIR Monitoring")

    def _create_context_menu(self) -> None:
        """Build the tray icon context menu."""
        menu = QMenu()

        # Show Window
        show_action = QAction("Show Window", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        # Scan Now (connected externally by main.py)
        self._scan_action = QAction("Scan Now", menu)
        menu.addAction(self._scan_action)

        # Open Excel
        open_action = QAction("Open Excel File", menu)
        open_action.triggered.connect(self._on_open_excel)
        menu.addAction(open_action)

        self._setup_action = QAction("Setup / Change Data Source", menu)
        menu.addAction(self._setup_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit CaseWatch", menu)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def set_scan_handler(self, handler) -> None:
        """Connect the Scan Now action to an external handler."""
        self._scan_action.triggered.connect(handler)

    def set_setup_handler(self, handler) -> None:
        """Connect the Setup action to an external handler."""
        self._setup_action.triggered.connect(handler)

    def set_overdue_state(self, has_overdue: bool, count: int = 0) -> None:
        """
        Update the tray icon based on overdue status.

        Args:
            has_overdue: Whether any cases are overdue.
            count: Number of overdue cases.
        """
        self._has_overdue = has_overdue

        if has_overdue:
            self.setIcon(self._warning_icon)
            self.setToolTip(f"CaseWatch — {count} overdue case(s)")
        else:
            self.setIcon(self._normal_icon)
            self.setToolTip("CaseWatch — All cases on track")

    # --- Slots ---

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (double-click)."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _on_message_clicked(self) -> None:
        """Handle notification click — open Excel file."""
        from notifier import Notifier
        Notifier.open_excel_file()
        logger.info("Notification clicked — opening Excel file")

    def _show_window(self) -> None:
        """Show and activate the main window."""
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_open_excel(self) -> None:
        """Open the configured Excel file."""
        from notifier import Notifier
        Notifier.open_excel_file()

    @staticmethod
    def _on_quit() -> None:
        """Quit the application."""
        from PyQt5.QtWidgets import QApplication
        logger.info("Application quit from tray menu")
        QApplication.instance().quit()
