"""
settings_dialog.py — Settings configuration dialog for CaseWatch.

Allows users to configure:
  - Excel file path (re-upload)
  - Reminder interval (prominently featured)
  - Scan interval
  - Overdue threshold
  - Auto-start on Windows boot
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QDialogButtonBox,
    QMessageBox,
    QWidget,
    QFrame,
    QComboBox,
)

from app_logger import get_logger
from config import get_config

logger = get_logger("settings_dialog")


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring CaseWatch parameters.

    The reminder interval is given primary prominence since
    users need to control how often they are reminded about
    pending cases.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CaseWatch — Settings")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self) -> None:
        """Build the settings form."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Title
        title = QLabel("Settings")
        title.setObjectName("titleText")
        layout.addWidget(title)

        # ── Reminder Interval (PRIMARY setting) ──
        reminder_group = QGroupBox("Reminder Interval")
        reminder_layout = QVBoxLayout(reminder_group)

        reminder_desc = QLabel(
            "How often should CaseWatch repeat a reminder notification\n"
            "for each overdue case that is still pending?"
        )
        reminder_desc.setObjectName("subtitleText")
        reminder_desc.setWordWrap(True)
        reminder_layout.addWidget(reminder_desc)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Repeat every:"))

        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(1, 10000)
        self._cooldown_spin.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._cooldown_spin.setFixedWidth(100)
        self._cooldown_spin.setMinimumHeight(36)
        self._cooldown_spin.setToolTip(
            "Minimum time between repeated reminders for the same overdue case."
        )
        interval_row.addWidget(self._cooldown_spin)

        self._cooldown_unit_combo = QComboBox()
        self._cooldown_unit_combo.addItems(["seconds", "minutes", "hours"])
        self._cooldown_unit_combo.setCurrentText("minutes")
        self._cooldown_unit_combo.setFixedWidth(120)
        self._cooldown_unit_combo.setMinimumHeight(36)
        self._cooldown_unit_combo.setFont(QFont("Segoe UI", 12))
        interval_row.addWidget(self._cooldown_unit_combo)

        interval_row.addStretch()
        reminder_layout.addLayout(interval_row)

        # Quick presets
        presets_row = QHBoxLayout()
        presets_label = QLabel("Quick set:")
        presets_label.setObjectName("subtitleText")
        presets_row.addWidget(presets_label)

        def apply_preset(val, unit):
            self._cooldown_spin.setValue(val)
            self._cooldown_unit_combo.setCurrentText(unit)

        presets = [("15 min", 15, "minutes"), ("30 min", 30, "minutes"), ("1 hour", 1, "hours"), ("2 hours", 2, "hours")]
        for label, val, unit in presets:
            btn = QPushButton(label)
            btn.setMaximumWidth(70)
            btn.setMaximumHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, v=val, u=unit: apply_preset(v, u))
            presets_row.addWidget(btn)

        presets_row.addStretch()
        reminder_layout.addLayout(presets_row)

        layout.addWidget(reminder_group)

        # ── Excel File ──
        excel_group = QGroupBox("Excel Workbook")
        excel_layout = QHBoxLayout(excel_group)

        self._file_input = QLineEdit()
        self._file_input.setPlaceholderText("Path to .xlsx file...")
        self._file_input.setReadOnly(True)
        self._file_input.setMinimumHeight(32)
        excel_layout.addWidget(self._file_input, 1)

        browse_btn = QPushButton("Change File...")
        browse_btn.setIcon(self.style().standardIcon(self.style().SP_DirIcon))
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_file)
        excel_layout.addWidget(browse_btn)

        layout.addWidget(excel_group)

        # ── Advanced Settings ──
        advanced_group = QGroupBox("Advanced")
        advanced_layout = QFormLayout(advanced_group)
        advanced_layout.setSpacing(12)

        # Scan interval
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 120)
        self._interval_spin.setSuffix(" minutes")
        self._interval_spin.setToolTip(
            "How often the system checks the Excel file for changes"
        )
        advanced_layout.addRow("Excel scan interval:", self._interval_spin)

        # Overdue threshold
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(1, 365)
        self._threshold_spin.setSuffix(" days")
        self._threshold_spin.setToolTip(
            "Number of days after allotment before a case is marked overdue"
        )
        advanced_layout.addRow("Overdue after:", self._threshold_spin)

        # Auto-start
        self._auto_start_check = QCheckBox("Launch CaseWatch on Windows startup")
        self._auto_start_check.setToolTip(
            "Automatically start CaseWatch when Windows boots (Windows only)"
        )
        advanced_layout.addRow(self._auto_start_check)

        layout.addWidget(advanced_group)

        # Footer note about Highlight synchronization
        self._sync_note = QLabel("Highlight synchronization will apply automatically after the workbook is saved and closed.")
        self._sync_note.setStyleSheet("color: #6B7280; font-size: 11px; font-style: italic; margin-bottom: 4px;")
        layout.addWidget(self._sync_note)

        # ── Buttons ──
        layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_current_settings(self) -> None:
        """Populate form with current configuration values."""
        config = get_config()
        self._file_input.setText(config.excel_file_path)
        self._cooldown_spin.setValue(config.reminder_cooldown)
        self._cooldown_unit_combo.setCurrentText(config.reminder_cooldown_unit)
        self._interval_spin.setValue(config.scan_interval_minutes)
        self._threshold_spin.setValue(config.overdue_threshold_days)
        self._auto_start_check.setChecked(config.auto_start)

    def _browse_file(self) -> None:
        """Open file dialog to select Excel workbook."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Workbook",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if file_path:
            self._file_input.setText(file_path)

    def _save_settings(self) -> None:
        """Validate and save all settings."""
        file_path = self._file_input.text().strip()

        if not file_path:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please select an Excel workbook file.",
            )
            return

        if not file_path.lower().endswith(".xlsx"):
            QMessageBox.warning(
                self,
                "Validation Error",
                "The selected file must be an .xlsx Excel workbook.",
            )
            return

        config = get_config()
        config.excel_file_path = file_path
        config.set("reminder_cooldown", self._cooldown_spin.value())
        config.set("reminder_cooldown_unit", self._cooldown_unit_combo.currentText())

        # Normalize and store reminder_cooldown_minutes for backward compatibility
        val = float(self._cooldown_spin.value())
        unit = self._cooldown_unit_combo.currentText().lower()
        if unit == "seconds":
            mins = val / 60.0
        elif unit == "hours":
            mins = val * 60.0
        else:
            mins = val
        config.set("reminder_cooldown_minutes", mins)
        config.set("scan_interval_minutes", self._interval_spin.value())
        config.set("overdue_threshold_days", self._threshold_spin.value())
        config.set("auto_start", self._auto_start_check.isChecked())
        config.save()

        logger.info(
            "Settings saved: reminder_interval=%d %s, scan_interval=%d min, threshold=%d days",
            self._cooldown_spin.value(),
            self._cooldown_unit_combo.currentText(),
            self._interval_spin.value(),
            self._threshold_spin.value(),
        )
        self.accept()
