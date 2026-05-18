"""
main_window.py — Main application window for CaseWatch.

Displays a table of all FIR cases with overdue status,
provides manual scan control, and minimizes to system tray.
"""

from datetime import datetime
from typing import List, Optional

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon, QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QStatusBar,
    QMenuBar,
    QAction,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSizePolicy,
)

from app_logger import get_logger
from config import get_config
from models import Case

logger = get_logger("main_window")

# Colors
COLOR_OVERDUE_BG = QColor(255, 199, 206)     # Soft red #FFC7CE
COLOR_OVERDUE_TEXT = QColor(156, 0, 6)        # Dark red text
COLOR_OK_BG = QColor(198, 239, 206)           # Soft green
COLOR_OK_TEXT = QColor(0, 97, 0)              # Dark green text
COLOR_HEADER_BG = QColor(44, 62, 80)          # Dark blue-gray
COLOR_HEADER_TEXT = QColor(255, 255, 255)      # White


class MainWindow(QMainWindow):
    """
    Main application window for CaseWatch.

    Features:
      - Case table with overdue status highlighting
      - Status bar with last scan time, total cases, overdue count
      - Menu bar: File, Settings, Help
      - Close event minimizes to tray instead of quitting
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._all_cases: List[Case] = []
        self._overdue_cases: List[Case] = []

    def _setup_ui(self) -> None:
        """Initialize all UI components."""
        self.setWindowTitle("CaseWatch — FSL FIR Monitoring System")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)

        # Load stylesheet
        self._load_stylesheet()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Stats bar
        self._stats_frame = self._create_stats_bar()
        layout.addWidget(self._stats_frame)

        # Case table
        self._table = self._create_table()
        layout.addWidget(self._table)

        # Footer note about Highlight synchronization
        self._sync_note = QLabel("Highlight synchronization will apply automatically after the workbook is saved and closed.")
        self._sync_note.setStyleSheet("color: #6B7280; font-size: 11px; font-style: italic; margin-top: 8px; margin-bottom: 8px;")
        layout.addWidget(self._sync_note)

        # Status bar
        self._status_label = QLabel("Ready")
        self.statusBar().addWidget(self._status_label, 1)

        # Menu bar
        self._create_menu_bar()

    def _load_stylesheet(self) -> None:
        """Load QSS stylesheet from assets."""
        from config import get_asset_path
        from pathlib import Path
        qss_path = Path(get_asset_path("assets/styles/app_style.qss"))
        if qss_path.exists():
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except OSError:
                pass

    def _create_header(self) -> QFrame:
        """Create the header section with title and scan button."""
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)

        # Title
        title = QLabel("CaseWatch")
        title.setObjectName("appTitle")
        title_font = QFont("Segoe UI", 20, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("FSL FIR Monitoring & Reminder System")
        subtitle.setObjectName("appSubtitle")
        subtitle_font = QFont("Segoe UI", 10)
        subtitle.setFont(subtitle_font)
        layout.addWidget(subtitle)

        layout.addStretch()

        # Scan Now button
        self._scan_btn = QPushButton("Scan Now")
        self._scan_btn.setIcon(self.style().standardIcon(self.style().SP_BrowserReload))
        self._scan_btn.setObjectName("primaryAction")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.setMinimumSize(130, 38)
        layout.addWidget(self._scan_btn)

        return frame

    def _create_stats_bar(self) -> QFrame:
        """Create the statistics summary bar."""
        frame = QFrame()
        frame.setObjectName("statsFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(32)

        # Total cases
        self._total_label = QLabel("Total Cases: 0")
        self._total_label.setObjectName("statLabel")
        layout.addWidget(self._total_label)

        # Overdue
        self._overdue_label = QLabel("Overdue: 0")
        self._overdue_label.setObjectName("statLabelOverdue")
        layout.addWidget(self._overdue_label)

        # On track
        self._ok_label = QLabel("On Track: 0")
        self._ok_label.setObjectName("statLabelOk")
        layout.addWidget(self._ok_label)

        layout.addStretch()

        # Last scan time
        self._last_scan_label = QLabel("Last scan: —")
        self._last_scan_label.setObjectName("lastScanLabel")
        layout.addWidget(self._last_scan_label)

        return frame

    def _create_table(self) -> QTableWidget:
        """Create the case data table."""
        headers = [
            "S.No",
            "FSL Number",
            "FIR Number",
            "Police Station",
            "Under Section",
            "Allotted Officer",
            "Date Receiving",
            "Date Allotment",
            "Date Reporting",
            "Status",
            "Overdue Days",
        ]

        table = QTableWidget()
        table.setObjectName("caseTable")
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)

        # Column sizing
        header_view = table.horizontalHeader()
        header_view.setStretchLastSection(True)
        header_view.setSectionResizeMode(QHeaderView.Interactive)

        # Set reasonable default widths
        col_widths = [50, 100, 100, 130, 120, 140, 110, 110, 110, 90, 90]
        for i, width in enumerate(col_widths):
            table.setColumnWidth(i, width)

        return table

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        select_action = QAction("Select Excel File...", self)
        select_action.setShortcut("Ctrl+O")
        select_action.triggered.connect(self._on_select_file)
        file_menu.addAction(select_action)

        open_excel_action = QAction("Open Excel File", self)
        open_excel_action.setShortcut("Ctrl+E")
        open_excel_action.triggered.connect(self._on_open_excel)
        file_menu.addAction(open_excel_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self._on_quit)
        file_menu.addAction(quit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("About CaseWatch", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # --- Public methods for Scheduler signals ---

    def update_cases(self, all_cases: List[Case], overdue_cases: List[Case]) -> None:
        """
        Update the table with fresh scan data.

        Args:
            all_cases: Complete list of parsed cases.
            overdue_cases: Subset of overdue cases.
        """
        self._all_cases = all_cases
        self._overdue_cases = overdue_cases
        config = get_config()

        # Update stats
        total = len(all_cases)
        overdue = len(overdue_cases)
        on_track = total - overdue

        self._total_label.setText(f"Total Cases: {total}")
        self._overdue_label.setText(f"Overdue: {overdue}")
        self._ok_label.setText(f"On Track: {on_track}")
        self._last_scan_label.setText(
            f"Last scan: {datetime.now().strftime('%H:%M:%S')}"
        )

        # Populate table
        self._table.setSortingEnabled(False)
        self._table.setRowCount(total)

        overdue_row_indices = {c.row_index for c in overdue_cases}

        for i, case in enumerate(all_cases):
            is_case_overdue = case.row_index in overdue_row_indices

            items = [
                str(case.sno or ""),
                case.fsl_number or "",
                case.fir_number or "",
                case.police_station or "",
                case.under_section or "",
                case.allotted_officer or "",
                str(case.date_receiving or ""),
                str(case.date_allotment or ""),
                str(case.date_reporting or ""),
                "OVERDUE" if is_case_overdue else "OK",
                str(case.overdue_days) if is_case_overdue else "",
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)

                if is_case_overdue:
                    item.setBackground(COLOR_OVERDUE_BG)
                    if col == 9:  # Status column
                        item.setForeground(COLOR_OVERDUE_TEXT)
                        item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                elif col == 9 and case.date_reporting is not None:
                    item.setBackground(COLOR_OK_BG)
                    item.setForeground(COLOR_OK_TEXT)
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))

                self._table.setItem(i, col, item)

        self._table.setSortingEnabled(True)
        self._update_status(f"Scan complete — {total} cases, {overdue} overdue")

    def update_error(self, message: str) -> None:
        """Show scan error in status bar."""
        self._update_status(f"Error: {message}")

    def set_scan_button_handler(self, handler) -> None:
        """Connect the Scan Now button to an external handler."""
        self._scan_btn.clicked.connect(handler)

    # --- Private slots ---

    def _on_select_file(self) -> None:
        """Open file dialog to select Excel workbook."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Workbook",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if file_path:
            config = get_config()
            config.excel_file_path = file_path
            config.save()
            self._update_status(f"Excel file set: {file_path}")
            logger.info("Excel file selected: %s", file_path)

    def _on_open_excel(self) -> None:
        """Open the configured Excel file."""
        from notifier import Notifier
        Notifier.open_excel_file()

    def _on_quit(self) -> None:
        """Actually quit the application."""
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()

    def _on_about(self) -> None:
        """Show about dialog."""
        from config import APP_VERSION
        QMessageBox.about(
            self,
            "About CaseWatch",
            "<h2>CaseWatch</h2>"
            "<p><b>FSL FIR Monitoring & Reminder System</b></p>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>Monitors FIR case files and automatically identifies<br>"
            "overdue reports for district FSL labs.</p>"
            "<hr>"
            "<p>Designed for Windows desktop environments.</p>",
        )

    def _update_status(self, text: str) -> None:
        """Update the status bar text."""
        self._status_label.setText(text)

    # --- Window events ---

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimize to tray instead of quitting on close."""
        event.ignore()
        self.hide()
        logger.info("Main window minimized to tray")
