"""
main.py — Application entry point for CaseWatch.

Initializes all components, wires signals, and starts the application.
Handles first-run setup, single-instance enforcement, and graceful shutdown.
"""

import sys
import os
import platform
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import QSharedMemory

from app_logger import setup_logging, get_logger
from config import get_config, get_asset_path
from tracker import ReminderTracker
from notifier import Notifier
from scheduler import Scheduler
from ui.main_window import MainWindow
from ui.tray_icon import TrayIcon
from ui.settings_dialog import SettingsDialog
from ui.first_run_dialog import FirstRunDialog


def _enforce_single_instance() -> QSharedMemory:
    """
    Ensure only one instance of CaseWatch is running.

    Returns:
        QSharedMemory object (must stay alive for the duration of the app).
    """
    shared_mem = QSharedMemory("CaseWatch_SingleInstance_Lock")

    if shared_mem.attach():
        # Another instance is already running
        QMessageBox.warning(
            None,
            "CaseWatch",
            "CaseWatch is already running.\n"
            "Check your system tray for the existing instance.",
        )
        sys.exit(0)

    if not shared_mem.create(1):
        # Failed to create shared memory (edge case)
        pass  # Continue anyway — non-critical

    return shared_mem


def _first_run_setup() -> bool:
    """
    Handle first-run configuration.

    Shows the setup wizard which:
      1. Explains the required Excel column format
      2. Lets the user upload their .xlsx workbook
      3. Lets the user set their preferred reminder interval

    Returns:
        True if setup was completed, False if user cancelled.
    """
    config = get_config()

    if not config.is_first_run:
        return True

    dialog = FirstRunDialog()
    if dialog.exec_():
        return True
    else:
        return False


def _register_auto_start() -> None:
    """
    Register CaseWatch for automatic startup on Windows.

    Creates a registry entry in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
    Only runs on Windows. Silently skips on other platforms.
    """
    if platform.system() != "Windows":
        return

    config = get_config()
    if not config.auto_start:
        return

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        exe_path = sys.executable
        if getattr(sys, "frozen", False):
            # Running as PyInstaller bundle
            exe_path = sys.executable
        winreg.SetValueEx(key, "CaseWatch", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        get_logger("main").info("Auto-start registered in Windows registry")
    except Exception as e:
        get_logger("main").warning("Failed to register auto-start: %s", e)


def main() -> None:
    """Application entry point."""
    # Initialize Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("CaseWatch")
    app.setOrganizationName("FSL")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Load Global Stylesheet
    qss_path = Path(get_asset_path("assets/styles/app_style.qss"))
    if qss_path.exists():
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            get_logger("main").warning("Failed to load stylesheet: %s", e)

    # Single instance check
    shared_mem = _enforce_single_instance()

    # Initialize logging
    config = get_config()
    setup_logging(config.log_level)
    logger = get_logger("main")
    logger.info("=" * 60)
    logger.info("CaseWatch starting up...")
    logger.info("Platform: %s", platform.platform())
    logger.info("Python: %s", sys.version)
    logger.info("=" * 60)

    # First-run setup
    if not _first_run_setup():
        logger.info("First-run setup cancelled by user")
        sys.exit(0)

    # Create main window
    main_window = MainWindow()

    # Create tray icon
    tray_icon = TrayIcon(main_window)
    tray_icon.show()

    # Create components
    tracker = ReminderTracker()
    notifier = Notifier(tray_icon)
    scheduler = Scheduler(notifier, tracker)

    # Wire signals
    scheduler.scan_completed.connect(main_window.update_cases)
    scheduler.scan_completed.connect(
        lambda all_c, overdue_c: tray_icon.set_overdue_state(
            len(overdue_c) > 0, len(overdue_c)
        )
    )
    scheduler.scan_error.connect(main_window.update_error)

    # Wire buttons
    main_window.set_scan_button_handler(scheduler.scan_now)
    tray_icon.set_scan_handler(scheduler.scan_now)

    # Settings dialog handler
    def open_settings():
        dialog = FirstRunDialog(main_window)
        if dialog.exec_():
            # Settings changed — restart scheduler with new interval
            scheduler.restart()
            # Run immediate scan so UI updates with new file
            scheduler.scan_now()
            logger.info("Setup updated, scheduler restarted")

    tray_icon.set_setup_handler(open_settings)

    # Add settings to menu
    settings_action = main_window.menuBar().addAction("&Setup / Change Data Source")
    settings_action.triggered.connect(open_settings)

    # Register auto-start (Windows only)
    _register_auto_start()

    # Show main window on startup
    main_window.show()

    # Start scheduler
    scheduler.start()

    logger.info("CaseWatch initialized successfully")

    # Run event loop
    exit_code = app.exec_()

    # Cleanup
    scheduler.stop()
    logger.info("CaseWatch shutting down (exit code: %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
