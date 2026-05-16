"""
models.py — Data models for CaseWatch.

Defines the Case dataclass representing a single FIR record
parsed from the Excel workbook.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Case:
    """Represents a single FIR/case record from the Excel sheet."""

    row_index: int  # 1-based Excel row index (for highlighting)
    sno: Optional[int] = None
    fsl_number: Optional[str] = None
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    under_section: Optional[str] = None
    allotted_officer: Optional[str] = None
    date_receiving: Optional[date] = None
    date_allotment: Optional[date] = None
    date_reporting: Optional[date] = None

    @property
    def case_id(self) -> str:
        """
        Unique identifier for tracking purposes.
        Uses FIR number + row index to handle duplicates.
        """
        fir = self.fir_number or "UNKNOWN"
        return f"{fir}_row{self.row_index}"

    @property
    def display_id(self) -> str:
        """Human-readable identifier for notifications."""
        if self.fsl_number:
            return self.fsl_number
        return self.fir_number or f"Row {self.row_index}"

    @property
    def overdue_days(self) -> int:
        """
        Number of days since allotment.
        Returns 0 if allotment date is missing or in the future.
        """
        if self.date_allotment is None:
            return 0
        today = date.today()
        delta = (today - self.date_allotment).days
        return max(0, delta)

    def is_overdue(self, threshold_days: int = 13) -> bool:
        """
        Determine if this case is overdue.

        A case is overdue when:
          - date_allotment is present and valid
          - date_reporting is empty/None
          - (today - date_allotment) > threshold_days

        Args:
            threshold_days: Number of days after which a case is overdue.
                            Defaults to 13 per spec.

        Returns:
            True if the case is overdue.
        """
        if self.date_allotment is None:
            return False
        if self.date_reporting is not None:
            return False
        return self.overdue_days > threshold_days

    @property
    def officer_display(self) -> str:
        """Officer name for display, with fallback."""
        return self.allotted_officer or "Unassigned"

    def __str__(self) -> str:
        status = "OVERDUE" if self.is_overdue() else "OK"
        return (
            f"Case({self.display_id}, Officer={self.officer_display}, "
            f"Allotted={self.date_allotment}, Reported={self.date_reporting}, "
            f"Status={status})"
        )
