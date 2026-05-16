"""
generate_test_data.py — Generate a sample Excel workbook for testing CaseWatch.

Creates a realistic test workbook with:
  - 8 overdue cases (allotment > 13 days ago, no reporting date)
  - 7 normal cases (reporting date filled within 13 days)
  - 5 edge cases (invalid dates, empty rows, future dates)
"""

from datetime import date, timedelta
import openpyxl
from openpyxl.styles import Font, Alignment


def generate_test_excel(output_path: str = "test_data.xlsx") -> None:
    """Generate a sample Excel workbook for testing."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FIR Records"

    # Headers
    headers = [
        "Sno",
        "FSL Number",
        "FIR Number",
        "Police Station",
        "Under Section",
        "Allotted Officer",
        "Date Receiving",
        "Date Allotment",
        "Date Reporting",
    ]

    # Style headers
    header_font = Font(bold=True, size=11)
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    today = date.today()

    # ---- OVERDUE CASES (8) ----
    overdue_cases = [
        (1, "FSL/2025/001", "124/25", "Sadar PS", "302/34 IPC", "Dr. Sharma",
         today - timedelta(days=25), today - timedelta(days=20), None),
        (2, "FSL/2025/002", "135/25", "Civil Lines PS", "376 IPC", "Dr. Verma",
         today - timedelta(days=30), today - timedelta(days=28), None),
        (3, "FSL/2025/003", "142/25", "Kotwali PS", "307 IPC", "Dr. Singh",
         today - timedelta(days=18), today - timedelta(days=16), None),
        (4, "FSL/2025/004", "156/25", "Cantt PS", "420 IPC", "Dr. Gupta",
         today - timedelta(days=22), today - timedelta(days=19), None),
        (5, "FSL/2025/005", "167/25", "City PS", "304 IPC", "Dr. Kumar",
         today - timedelta(days=40), today - timedelta(days=38), None),
        (6, "FSL/2025/006", "178/25", "Model Town PS", "498A IPC", "Dr. Sharma",
         today - timedelta(days=15), today - timedelta(days=14), None),
        (7, "FSL/2025/007", "189/25", "Industrial Area PS", "379 IPC", "Dr. Verma",
         today - timedelta(days=35), today - timedelta(days=33), None),
        (8, "FSL/2025/008", "200/25", "Railway PS", "302/120B IPC", "Dr. Singh",
         today - timedelta(days=50), today - timedelta(days=48), None),
    ]

    # ---- NORMAL CASES (7) ----
    normal_cases = [
        (9, "FSL/2025/009", "210/25", "Sadar PS", "354 IPC", "Dr. Gupta",
         today - timedelta(days=20), today - timedelta(days=18),
         today - timedelta(days=10)),
        (10, "FSL/2025/010", "221/25", "Civil Lines PS", "506 IPC", "Dr. Kumar",
         today - timedelta(days=15), today - timedelta(days=12),
         today - timedelta(days=5)),
        (11, "FSL/2025/011", "232/25", "Kotwali PS", "323 IPC", "Dr. Sharma",
         today - timedelta(days=10), today - timedelta(days=8),
         today - timedelta(days=2)),
        (12, "FSL/2025/012", "243/25", "Cantt PS", "406 IPC", "Dr. Verma",
         today - timedelta(days=25), today - timedelta(days=22),
         today - timedelta(days=15)),
        (13, "FSL/2025/013", "254/25", "City PS", "304A IPC", "Dr. Singh",
         today - timedelta(days=8), today - timedelta(days=6),
         today - timedelta(days=1)),
        (14, "FSL/2025/014", "265/25", "Model Town PS", "147 IPC", "Dr. Gupta",
         today - timedelta(days=30), today - timedelta(days=28),
         today - timedelta(days=20)),
        (15, "FSL/2025/015", "276/25", "Industrial Area PS", "457 IPC", "Dr. Kumar",
         today - timedelta(days=5), today - timedelta(days=3),
         today - timedelta(days=1)),
    ]

    # ---- EDGE CASES (5) ----
    edge_cases = [
        # Recent allotment (not overdue yet)
        (16, "FSL/2025/016", "287/25", "Railway PS", "380 IPC", "Dr. Sharma",
         today - timedelta(days=5), today - timedelta(days=3), None),
        # Future allotment date (should not be overdue)
        (17, "FSL/2025/017", "298/25", "Sadar PS", "395 IPC", "Dr. Verma",
         today + timedelta(days=5), today + timedelta(days=7), None),
        # Exactly 13 days (boundary — not overdue per spec: must be > 13)
        (18, "FSL/2025/018", "309/25", "Civil Lines PS", "302 IPC", "Dr. Singh",
         today - timedelta(days=14), today - timedelta(days=13), None),
        # Allotment today
        (19, "FSL/2025/019", "320/25", "Kotwali PS", "376 IPC", "Dr. Gupta",
         today, today, None),
        # Missing FSL number
        (20, None, "331/25", "Cantt PS", "420 IPC", "Dr. Kumar",
         today - timedelta(days=20), today - timedelta(days=18), None),
    ]

    # Write all cases
    row = 2
    for cases in [overdue_cases, normal_cases, edge_cases]:
        for case_data in cases:
            for col, value in enumerate(case_data, 1):
                cell = ws.cell(row=row, column=col)
                if value is not None:
                    cell.value = value
                    if isinstance(value, date):
                        cell.number_format = "DD/MM/YYYY"
                cell.alignment = Alignment(horizontal="center")
            row += 1

    # Add an empty row (edge case: should be skipped)
    row += 1  # Row 22 is empty

    # Add a row with text in date column (edge case: invalid date)
    ws.cell(row=row, column=1, value=21)
    ws.cell(row=row, column=2, value="FSL/2025/021")
    ws.cell(row=row, column=3, value="342/25")
    ws.cell(row=row, column=4, value="City PS")
    ws.cell(row=row, column=5, value="307 IPC")
    ws.cell(row=row, column=6, value="Dr. Sharma")
    ws.cell(row=row, column=7, value="invalid-date")
    ws.cell(row=row, column=8, value="not-a-date")
    ws.cell(row=row, column=9, value=None)

    # Auto-fit column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[
            openpyxl.utils.get_column_letter(col)
        ].width = 18

    wb.save(output_path)
    print(f"Test data generated: {output_path}")
    print(f"  - 8 overdue cases (rows 2-9)")
    print(f"  - 7 normal/resolved cases (rows 10-16)")
    print(f"  - 5 edge cases (rows 17-21)")
    print(f"  - 1 empty row (row 22)")
    print(f"  - 1 invalid date row (row 23)")


if __name__ == "__main__":
    generate_test_excel()
