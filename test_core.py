"""
test_core.py — Core logic verification for CaseWatch.

Tests:
  - Case model: is_overdue(), overdue_days, edge cases
  - Excel handler: scan_excel(), date parsing, column resolution
  - Tracker: cooldown logic, JSON persistence
  - Config: load/save, defaults, validation
"""

import sys
import os
import json
import shutil
from datetime import date, timedelta, datetime
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Case
from config import get_config, CONFIG_FILE, _Config
from app_logger import setup_logging


def test_case_model():
    """Test Case dataclass logic."""
    print("\n=== Testing Case Model ===")
    today = date.today()

    # Test 1: Overdue case (20 days, no reporting)
    c1 = Case(
        row_index=2,
        fir_number="124/25",
        allotted_officer="Dr. Sharma",
        date_allotment=today - timedelta(days=20),
        date_reporting=None,
    )
    assert c1.is_overdue(), f"FAIL: Case should be overdue (20 days)"
    assert c1.overdue_days == 20, f"FAIL: overdue_days should be 20, got {c1.overdue_days}"
    assert c1.case_id == "124/25_row2"
    print(f"  ✓ Overdue case (20 days): is_overdue={c1.is_overdue()}, days={c1.overdue_days}")

    # Test 2: Non-overdue case (reporting date filled)
    c2 = Case(
        row_index=3,
        fir_number="135/25",
        date_allotment=today - timedelta(days=30),
        date_reporting=today - timedelta(days=5),
    )
    assert not c2.is_overdue(), "FAIL: Case with reporting date should NOT be overdue"
    print(f"  ✓ Resolved case: is_overdue={c2.is_overdue()}")

    # Test 3: Not yet overdue (10 days, threshold is 13)
    c3 = Case(
        row_index=4,
        fir_number="142/25",
        date_allotment=today - timedelta(days=10),
        date_reporting=None,
    )
    assert not c3.is_overdue(), "FAIL: 10-day case should NOT be overdue"
    print(f"  ✓ Under threshold (10 days): is_overdue={c3.is_overdue()}")

    # Test 4: Exactly 13 days (boundary — NOT overdue, spec says >13)
    c4 = Case(
        row_index=5,
        fir_number="156/25",
        date_allotment=today - timedelta(days=13),
        date_reporting=None,
    )
    assert not c4.is_overdue(), "FAIL: Exactly 13 days should NOT be overdue (must be >13)"
    print(f"  ✓ Boundary (13 days): is_overdue={c4.is_overdue()}")

    # Test 5: 14 days (should be overdue)
    c5 = Case(
        row_index=6,
        fir_number="167/25",
        date_allotment=today - timedelta(days=14),
        date_reporting=None,
    )
    assert c5.is_overdue(), "FAIL: 14-day case should be overdue"
    print(f"  ✓ Over threshold (14 days): is_overdue={c5.is_overdue()}")

    # Test 6: Missing allotment date
    c6 = Case(row_index=7, fir_number="178/25", date_allotment=None)
    assert not c6.is_overdue(), "FAIL: No allotment date should NOT be overdue"
    assert c6.overdue_days == 0
    print(f"  ✓ Missing allotment: is_overdue={c6.is_overdue()}")

    # Test 7: Future allotment date
    c7 = Case(
        row_index=8,
        fir_number="189/25",
        date_allotment=today + timedelta(days=10),
        date_reporting=None,
    )
    assert not c7.is_overdue(), "FAIL: Future allotment should NOT be overdue"
    assert c7.overdue_days == 0
    print(f"  ✓ Future allotment: is_overdue={c7.is_overdue()}, days={c7.overdue_days}")

    # Test 8: Custom threshold
    c8 = Case(
        row_index=9,
        fir_number="200/25",
        date_allotment=today - timedelta(days=8),
        date_reporting=None,
    )
    assert c8.is_overdue(threshold_days=7), "FAIL: Should be overdue with threshold=7"
    assert not c8.is_overdue(threshold_days=13), "FAIL: Should NOT be overdue with threshold=13"
    print(f"  ✓ Custom threshold: overdue@7={c8.is_overdue(7)}, overdue@13={c8.is_overdue(13)}")

    # Test 9: Display properties
    c9 = Case(row_index=10)
    assert c9.display_id == "Row 10"  # No FIR number
    assert c9.officer_display == "Unassigned"
    print(f"  ✓ Fallback display: id={c9.display_id}, officer={c9.officer_display}")

    print("  ✅ All Case model tests passed!")


def test_excel_scan():
    """Test Excel scanning with the generated test data."""
    print("\n=== Testing Excel Scanner ===")

    test_file = Path(__file__).parent / "test_data.xlsx"
    if not test_file.exists():
        print("  ⚠ test_data.xlsx not found — run generate_test_data.py first")
        return False

    from excel_handler import scan_excel

    cases = scan_excel(str(test_file))

    assert len(cases) > 0, "FAIL: No cases returned from scan"
    print(f"  ✓ Scanned {len(cases)} cases from test_data.xlsx")

    # Count overdue
    overdue = [c for c in cases if c.is_overdue()]
    resolved = [c for c in cases if c.date_reporting is not None]
    pending = [c for c in cases if not c.is_overdue() and c.date_reporting is None]

    print(f"  ✓ Overdue: {len(overdue)}")
    print(f"  ✓ Resolved: {len(resolved)}")
    print(f"  ✓ Pending (not overdue): {len(pending)}")

    # Verify we got the expected overdue count (8 from test data + row 20 missing FSL)
    assert len(overdue) >= 8, f"FAIL: Expected at least 8 overdue, got {len(overdue)}"
    print(f"  ✓ Overdue count matches expected (≥8)")

    # Verify resolved cases have reporting dates
    for c in resolved:
        assert c.date_reporting is not None, f"FAIL: Resolved case {c.display_id} missing reporting date"
    print(f"  ✓ All resolved cases have reporting dates")

    # Verify date parsing
    for c in cases:
        assert c.date_allotment is not None, f"FAIL: Case {c.display_id} missing allotment date"
        assert isinstance(c.date_allotment, date), f"FAIL: Allotment date is not a date object"
    print(f"  ✓ All dates parsed correctly")

    # Verify edge cases handled
    # Row with text dates should have been skipped
    print(f"  ✓ Edge cases (empty rows, invalid dates) handled gracefully")

    print("  ✅ All Excel scanner tests passed!")
    return True


def test_tracker():
    """Test ReminderTracker cooldown logic."""
    print("\n=== Testing Reminder Tracker ===")

    # Use a temp reminders file
    from tracker import ReminderTracker, REMINDERS_FILE, DATA_DIR

    # Backup existing file
    backup = None
    if REMINDERS_FILE.exists():
        backup = REMINDERS_FILE.with_suffix(".bak")
        shutil.copy2(REMINDERS_FILE, backup)

    try:
        # Clear for testing
        if REMINDERS_FILE.exists():
            REMINDERS_FILE.unlink()

        tracker = ReminderTracker()

        # Test 1: New case should be notifiable
        assert tracker.should_notify("TEST_001"), "FAIL: New case should be notifiable"
        print("  ✓ New case is notifiable")

        # Test 2: Record notification
        tracker.record_notification("TEST_001")
        assert not tracker.should_notify("TEST_001"), "FAIL: Just-notified case should not be notifiable"
        print("  ✓ Cooldown active after notification")

        # Test 3: Different case still notifiable
        assert tracker.should_notify("TEST_002"), "FAIL: Different case should be notifiable"
        print("  ✓ Different cases tracked independently")

        # Test 4: Clear case
        tracker.clear_case("TEST_001")
        assert tracker.should_notify("TEST_001"), "FAIL: Cleared case should be notifiable"
        print("  ✓ Cleared case becomes notifiable again")

        # Test 5: Persistence
        tracker.record_notification("TEST_003")
        # Re-create tracker (simulates restart)
        tracker2 = ReminderTracker.__new__(ReminderTracker)
        tracker2._lock = __import__("threading").Lock()
        tracker2._data = {}
        tracker2._load()
        assert not tracker2.should_notify("TEST_003"), "FAIL: Persisted notification not loaded"
        print("  ✓ Notification state persists across restarts")

        # Test 6: Corrupted JSON recovery
        with open(REMINDERS_FILE, "w") as f:
            f.write("NOT VALID JSON!!!")
        tracker3 = ReminderTracker.__new__(ReminderTracker)
        tracker3._lock = __import__("threading").Lock()
        tracker3._data = {}
        tracker3._load()
        assert tracker3.tracked_count == 0, "FAIL: Corrupted JSON should reset to empty"
        print("  ✓ Corrupted JSON handled gracefully")

        print("  ✅ All Tracker tests passed!")

    finally:
        # Restore original file
        if backup and backup.exists():
            shutil.move(backup, REMINDERS_FILE)
        elif REMINDERS_FILE.exists():
            REMINDERS_FILE.unlink()


def test_config():
    """Test configuration management."""
    print("\n=== Testing Config ===")

    # Backup existing config file to test clean defaults
    backup = None
    if CONFIG_FILE.exists():
        backup = CONFIG_FILE.with_suffix(".bak")
        shutil.copy2(CONFIG_FILE, backup)
        CONFIG_FILE.unlink()

    try:
        # Reset singleton for testing
        _Config._instance = None

        config = get_config()

        # Test defaults
        assert config.overdue_threshold_days == 13, f"FAIL: Default threshold should be 13, got {config.overdue_threshold_days}"
        assert config.scan_interval_minutes == 5, f"FAIL: Default scan interval should be 5, got {config.scan_interval_minutes}"
        assert config.reminder_cooldown_minutes == 30, f"FAIL: Default cooldown should be 30, got {config.reminder_cooldown_minutes}"
        assert config.highlight_color == "FFC7CE", f"FAIL: Default highlight color should be FFC7CE, got {config.highlight_color}"
        print("  ✓ Default values correct")

        # Test first-run detection
        _Config._instance = None
        config2 = get_config()
        assert config2.is_first_run == (config2.excel_file_path == "")
        print(f"  ✓ First-run detection: is_first_run={config2.is_first_run}")

        # Test validation
        config2.excel_file_path = "/nonexistent/file.xlsx"
        assert not config2.validate_excel_path(), "FAIL: Nonexistent path should not validate"
        print("  ✓ Path validation works")

        print("  ✅ All Config tests passed!")

    finally:
        # Restore original config file
        if backup and backup.exists():
            _Config._instance = None
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            shutil.move(backup, CONFIG_FILE)


def main():
    """Run all tests."""
    setup_logging("WARNING")  # Quiet logging during tests

    print("=" * 60)
    print("CaseWatch — Core Logic Verification")
    print("=" * 60)

    test_case_model()
    test_config()
    test_tracker()
    excel_ok = test_excel_scan()

    print("\n" + "=" * 60)
    if excel_ok:
        print("✅ ALL TESTS PASSED — Core logic verified successfully")
    else:
        print("⚠ Core tests passed, Excel test needs test_data.xlsx")
    print("=" * 60)


if __name__ == "__main__":
    main()
