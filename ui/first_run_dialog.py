"""
first_run_dialog.py — First-run setup wizard for CaseWatch.

Shows the user:
  1. The exact Excel format required for the system to work
  2. File picker to upload their Excel workbook
  3. Reminder interval configuration
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QWidget,
    QSizePolicy,
    QComboBox,
)

from app_logger import get_logger
from config import get_config

logger = get_logger("first_run_dialog")

# Required column specification
REQUIRED_COLUMNS = [
    ("Sno", "Integer", "Serial number of the entry"),
    ("FSL Number", "Text", "FSL case reference number (e.g. FSL/2025/001)"),
    ("FIR Number", "Text", "FIR case number (e.g. 124/25)"),
    ("Police Station", "Text", "Name of the police station"),
    ("Under Section", "Text", "IPC section(s) applicable"),
    ("Allotted Officer", "Text", "Name of the officer allotted the case"),
    ("Date Receiving", "Date", "Date the case was received at FSL"),
    ("Date Allotment", "Date (Required)", "Date the case was allotted to an officer"),
    ("Date Reporting", "Date / Empty", "Date the report was submitted — leave empty if pending"),
]


class FirstRunDialog(QDialog):
    """
    First-run setup wizard that explains the required Excel format
    and collects the workbook path + reminder interval from the user.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CaseWatch — Setup")
        self.setMinimumSize(720, 780)
        self.setModal(True)
        self._file_path: str = ""
        self._setup_ui()
        self._prefill_from_config()

    def _prefill_from_config(self) -> None:
        """Prefill UI fields from the existing config if present."""
        config = get_config()
        if config.excel_file_path:
            self._file_path = config.excel_file_path
            from pathlib import Path
            name = Path(config.excel_file_path).name
            self._file_label.setText(f"Selected: {name}")
            self._file_label.setStyleSheet("font-weight: 500; color: #111827;")
            self._start_btn.setEnabled(True)
            self._start_btn.setText(" Save & Continue")
        
        if config.reminder_cooldown:
            self._interval_spin.setValue(config.reminder_cooldown)
            self._interval_unit_combo.setCurrentText(config.reminder_cooldown_unit)
        if config.overdue_threshold_days:
            self._overdue_spin.setValue(config.overdue_threshold_days)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Center Container
        container = QWidget()
        container.setMaximumWidth(680)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 40, 40, 30)
        layout.setSpacing(0)

        # ── Welcome Header ──
        welcome = QLabel("Welcome to CaseWatch")
        welcome.setObjectName("titleText")
        layout.addWidget(welcome)

        tagline = QLabel("FSL FIR Monitoring & Reminder System")
        tagline.setObjectName("subtitleText")
        layout.addWidget(tagline)
        
        layout.addSpacing(24)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setObjectName("HLine")
        layout.addWidget(div1)
        layout.addSpacing(24)

        # ── Step 1: Excel Format ──
        s1_layout = QHBoxLayout()
        s1_layout.setContentsMargins(0, 0, 0, 16)
        s1_num = QLabel("1")
        s1_num.setObjectName("stepNumber")
        s1_num.setFixedSize(24, 24)
        s1_title = QLabel("Excel Template Guidelines")
        s1_title.setObjectName("stepTitle")
        s1_layout.addWidget(s1_num)
        s1_layout.addWidget(s1_title)
        s1_layout.addStretch()
        layout.addLayout(s1_layout)

        # Guidelines Box (contains both the column info AND the warning)
        g_frame = QFrame()
        g_frame.setObjectName("guidelinesFrame")
        g_outer = QVBoxLayout(g_frame)
        g_outer.setContentsMargins(20, 20, 20, 20)
        g_outer.setSpacing(16)

        # Row 1: icon + column text
        row1 = QHBoxLayout()
        row1.setSpacing(14)
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("assets/icons/excel.svg").pixmap(24, 24))
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignTop)
        row1.addWidget(icon_label)

        g_text = QLabel(
            "Your Excel workbook (.xlsx) must have the following<br>"
            "columns in the first row as headers:<br>"
            "<b>Sno, FSL Number, FIR Number, Police Station,<br>"
            "Under Section, Allotted Officer, Date Receiving,<br>"
            "Date Allotment.</b><br><br>"
            "(Date Reporting should be empty for pending cases)."
        )
        g_text.setTextFormat(Qt.RichText)
        row1.addWidget(g_text)
        g_outer.addLayout(row1)

        # Row 2: warning
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        w_icon = QLabel()
        w_icon.setPixmap(QIcon("assets/icons/warning.svg").pixmap(16, 16))
        w_icon.setFixedWidth(16)
        w_icon.setAlignment(Qt.AlignTop)
        row2.addWidget(w_icon)

        w_text = QLabel(
            "Important: The Date Allotment column is required\n"
            "for overdue detection. Leave Date Reporting empty\n"
            "for pending cases."
        )
        w_text.setStyleSheet("color: #6b7280;")
        row2.addWidget(w_text)
        g_outer.addLayout(row2)

        layout.addWidget(g_frame)

        layout.addSpacing(32)

        # ── Step 2: Upload File ──
        s2_layout = QHBoxLayout()
        s2_layout.setContentsMargins(0, 0, 0, 16)
        s2_num = QLabel("2")
        s2_num.setObjectName("stepNumber")
        s2_num.setFixedSize(24, 24)
        s2_title = QLabel("Data Source")
        s2_title.setObjectName("stepTitle")
        s2_layout.addWidget(s2_num)
        s2_layout.addWidget(s2_title)
        s2_layout.addStretch()
        layout.addLayout(s2_layout)

        file_frame = QFrame()
        file_frame.setObjectName("dashedFrame")
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(16, 12, 16, 12)
        
        f_icon = QLabel()
        f_icon.setPixmap(QIcon("assets/icons/folder.svg").pixmap(20, 20))
        file_layout.addWidget(f_icon)

        self._file_label = QLabel("Selected: No file")
        file_layout.addWidget(self._file_label, 1)

        browse_btn = QPushButton(" Browse...")
        browse_btn.setIcon(QIcon("assets/icons/folder.svg"))
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setObjectName("secondaryAction")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_frame)

        layout.addSpacing(32)

        # ── Step 3: Reminder Frequency ──
        s3_layout = QHBoxLayout()
        s3_layout.setContentsMargins(0, 0, 0, 16)
        s3_num = QLabel("3")
        s3_num.setObjectName("stepNumber")
        s3_num.setFixedSize(24, 24)
        s3_title = QLabel("Reminder Settings")
        s3_title.setObjectName("stepTitle")
        s3_layout.addWidget(s3_num)
        s3_layout.addWidget(s3_title)
        s3_layout.addStretch()
        layout.addLayout(s3_layout)

        # Intervals
        int_layout = QHBoxLayout()
        int_layout.setContentsMargins(40, 0, 0, 0)
        int_layout.addWidget(QLabel("Remind me every:"))
        
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 10000)
        self._interval_spin.setValue(30)
        self._interval_spin.setFixedWidth(80)
        int_layout.addWidget(self._interval_spin)

        self._interval_unit_combo = QComboBox()
        self._interval_unit_combo.addItems(["seconds", "minutes", "hours"])
        self._interval_unit_combo.setCurrentText("minutes")
        self._interval_unit_combo.setFixedWidth(100)
        int_layout.addWidget(self._interval_unit_combo)
        int_layout.addStretch()
        layout.addLayout(int_layout)

        layout.addSpacing(16)

        # Overdue Threshold
        ov_layout = QHBoxLayout()
        ov_layout.setContentsMargins(40, 0, 0, 0)
        ov_layout.addWidget(QLabel("Mark case overdue after:"))
        
        self._overdue_spin = QSpinBox()
        self._overdue_spin.setRange(1, 365)
        self._overdue_spin.setValue(13)
        self._overdue_spin.setFixedWidth(80)
        ov_layout.addWidget(self._overdue_spin)
        ov_layout.addWidget(QLabel("days"))
        ov_layout.addStretch()
        layout.addLayout(ov_layout)

        layout.addStretch() # Push everything up to top
        
        # Divider 2
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setObjectName("HLine")
        layout.addWidget(div2)
        layout.addSpacing(16)

        # ── Action Bar ──
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryAction")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)

        self._start_btn = QPushButton(" Start Monitoring")
        self._start_btn.setIcon(QIcon("assets/icons/play.svg"))
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setObjectName("primaryAction")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        action_layout.addWidget(self._start_btn)
        
        layout.addLayout(action_layout)

        # Add centered container to main layout
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(container)
        center_layout.addStretch()
        main_layout.addLayout(center_layout)


    def _browse_file(self) -> None:
        """Open file dialog to select Excel workbook."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Workbook",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if file_path:
            self._file_path = file_path
            # Show just the filename for clarity
            from pathlib import Path
            name = Path(file_path).name
            self._file_label.setText(f"Selected: {name}")
            self._file_label.setStyleSheet("font-weight: 500; color: #111827;")
            self._start_btn.setEnabled(True)
            logger.info("File selected: %s", file_path)

    def _on_start(self) -> None:
        """Validate and save configuration, then start monitoring."""
        if not self._file_path:
            QMessageBox.warning(self, "No File", "Please select an Excel workbook first.")
            return

        if not self._file_path.lower().endswith(".xlsx"):
            QMessageBox.warning(
                self, "Invalid File",
                "Please select a valid .xlsx Excel workbook."
            )
            return

        # Validate the file has required columns
        try:
            import pandas as pd
            df = pd.read_excel(self._file_path, engine="openpyxl", nrows=0)
            columns_lower = [c.strip().lower() for c in df.columns]

            # Check for the critical column: Date Allotment
            allotment_aliases = ["date allotment", "date of allotment", "allotment date"]
            has_allotment = any(alias in columns_lower for alias in allotment_aliases)

            reporting_aliases = ["date reporting", "date of reporting", "reporting date"]
            has_reporting = any(alias in columns_lower for alias in reporting_aliases)

            if not has_allotment:
                QMessageBox.critical(
                    self, "Missing Required Column",
                    'The selected Excel file does not contain a "Date Allotment" column.\n\n'
                    "This column is required for overdue detection.\n"
                    "Please check your Excel file and ensure the column header exists."
                )
                return

            if not has_reporting:
                QMessageBox.warning(
                    self, "Missing Column",
                    'The selected Excel file does not contain a "Date Reporting" column.\n\n'
                    "This column is needed to track case completion.\n"
                    "The system will still run, but cannot detect resolved cases."
                )

        except Exception as e:
            QMessageBox.critical(
                self, "File Error",
                f"Could not read the Excel file:\n\n{e}\n\n"
                "Please ensure the file is a valid .xlsx workbook."
            )
            return

        # Save configuration
        config = get_config()
        config.excel_file_path = self._file_path
        config.set("reminder_cooldown", self._interval_spin.value())
        config.set("reminder_cooldown_unit", self._interval_unit_combo.currentText())

        # Normalize and store reminder_cooldown_minutes for backward compatibility
        val = float(self._interval_spin.value())
        unit = self._interval_unit_combo.currentText().lower()
        if unit == "seconds":
            mins = val / 60.0
        elif unit == "hours":
            mins = val * 60.0
        else:
            mins = val
        config.set("reminder_cooldown_minutes", mins)
        config.set("overdue_threshold_days", self._overdue_spin.value())
        config.save()

        logger.info(
            "First-run setup complete: file=%s, interval=%d %s, overdue=%d days",
            self._file_path, self._interval_spin.value(), self._interval_unit_combo.currentText(), self._overdue_spin.value()
        )

        self.accept()

    @property
    def selected_file(self) -> str:
        return self._file_path

    @property
    def reminder_interval(self) -> int:
        return self._interval_spin.value()
