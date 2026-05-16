# 1. Agent Operating Rules

## General Rules

* The system must prioritize reliability and data integrity over visual complexity.
* The system must never modify FIR/FSL records other than:

  * row highlighting,
  * calculated columns,
  * reminder metadata.
* Original case information must remain untouched.
* The application must function offline on Windows systems.
* The application must continue operating even if the Excel file contains partially invalid rows.
* All date comparisons must use the local system date.
* The system must not delete rows automatically.
* The system must not overwrite manually entered reporting dates.

## Coding Rules

* Use modular Python architecture.
* Use clear separation between:

  * UI,
  * Excel processing,
  * notification logic,
  * configuration.
* Avoid hardcoded paths.
* All configurable values must exist in a config file.
* Logging must be implemented for debugging and auditability.

---

# 2. Project Overview

## Project Name

FSL FIR Monitoring & Reminder System

## Overview

The project is a Windows-based desktop monitoring application for district FSL labs to track allotted FIR/case files and automatically identify overdue reports.

The system monitors an Excel sheet containing FIR case details. If more than 13 days pass after the date of allotment and no reporting date has been entered, the system:

* marks the case as pending,
* highlights the corresponding row in Excel,
* continuously issues reminder notifications,
* opens the Excel sheet when reminders are clicked.

## Problem Statement

Currently, overdue FIR/case reports are manually tracked, making it easy for delayed cases to go unnoticed. This leads to:

* delayed forensic reporting,
* administrative inefficiency,
* lack of automated tracking,
* poor visibility of pending cases.

The system automates overdue detection and reminder issuance.

---

# 3. Product Philosophy

## Core Principles

### 1. Minimal Operational Friction

The system should require minimal technical expertise.

### 2. Non-Disruptive Automation

The workflow should integrate with existing Excel-based processes without requiring migration to a new database system.

### 3. Persistent Visibility

Pending cases must remain continuously visible until resolved.

### 4. Data Integrity First

The application must preserve original records and avoid destructive modifications.

### 5. Offline-First Design

The system must work without internet connectivity.

---

# 4. User Personas

## Primary Users

### FSL Administrative Staff

* Maintain Excel records
* Monitor pending cases
* Update reporting dates

### FSL Officers

* Receive reminders for overdue cases
* Access case sheet quickly

### Supervisory Officers

* Review pending workload
* Identify delayed reporting patterns

## Technical Skill Level

Low to moderate computer literacy.

## Usage Environment

* Windows desktop systems
* Government office environments
* Shared workstation scenarios

---

# 5. Core Features

## Excel Monitoring

* Read Excel workbook periodically
* Parse FIR/case records

## Overdue Detection

Trigger overdue state when:

* current date − allotment date > 13 days
* reporting date field is empty

## Reminder Notifications

* Desktop popup notifications
* Repeat reminders until reporting date is entered
* Notification click opens Excel sheet

## Row Highlighting

* Highlight overdue rows in soft red
* Restore normal formatting once reporting date exists

## Automatic Refresh

* Re-check Excel at fixed intervals

## Startup Automation

* Launch automatically on Windows startup

## Logging

* Maintain logs of:

  * reminders issued,
  * errors,
  * processing activity.

---

# 6. User Flows

## Flow 1 — Normal Case

### Step 1

User enters:

* FIR details,
* allotment date.

### Step 2

Reporting date entered within 13 days.

### Step 3

No reminder generated.

---

## Flow 2 — Overdue Case

### Step 1

User enters allotment date.

### Step 2

13+ days pass.

### Step 3

Reporting date remains empty.

### Step 4

System:

* highlights row,
* generates reminder,
* logs overdue state.

---

## Flow 3 — Reminder Click

### Step 1

User clicks notification.

### Step 2

Excel sheet opens automatically.

---

## Flow 4 — Case Resolution

### Step 1

User enters reporting date.

### Step 2

Next scan detects completion.

### Step 3

System:

* removes highlight,
* stops reminders.

---

# 7. Technical Stack

## Language

Python 3.11+

## GUI Framework

PyQt5

## Excel Processing

* pandas
* openpyxl

## Notifications

PyQt5 System Tray Notifications

## Packaging

PyInstaller

## Scheduling

Internal timer loop

## Operating System

Windows 10/11

## Storage

Excel workbook (.xlsx)

## Constraints

* Offline operation mandatory
* No internet dependency
* Must run on low-resource government systems

---

# 8. Database Schema

## No Dedicated Database (Phase 1)

Excel sheet acts as the primary datastore.

## Excel Columns

| Column           | Type         |
| ---------------- | ------------ |
| Sno              | Integer      |
| FSL Number       | String       |
| FIR Number       | String       |
| Police Station   | String       |
| Under Section    | String       |
| Allotted Officer | String       |
| Date Receiving   | Date         |
| Date Allotment   | Date         |
| Date Reporting   | Date / Empty |

## Optional Internal Tracking File

### reminders.json

Tracks:

* last reminder timestamp,
* notification cooldown.

Example:

```json id="ckrzud"
{
  "124/25": {
    "last_notified": "2026-05-15T10:00:00"
  }
}
```

---

# 9. API Contracts

## Phase 1

No external APIs required.

## Internal Functional Interfaces

### Excel Scanner

```python id="49v0uh"
scan_excel(file_path) -> List[Case]
```

### Overdue Checker

```python id="4e2byd"
is_overdue(case) -> bool
```

### Notification Dispatcher

```python id="z9nmg0"
send_notification(case)
```

### Excel Formatter

```python id="ogwcnr"
highlight_row(case_row)
```

---

# 10. UI/UX Guidelines

## Design Philosophy

* Minimalist
* Administrative utility focused
* Low learning curve

## Color Rules

### Overdue Rows

Soft red:

```text id="v88fsy"
#FFC7CE
```

### Text

Black text only for readability.

## Notifications

Must contain:

* FIR number,
* officer name,
* overdue duration.

## Tray Application

Application should:

* minimize to system tray,
* run silently in background.

## Responsiveness

UI interactions should complete within 1 second.

---

# 11. AI/System Behavior Rules

## System Rules

* Never generate duplicate notifications continuously.
* Use cooldown intervals between reminders.
* Ignore rows with invalid or missing allotment dates.
* Skip empty rows safely.
* Continue processing remaining rows if one row fails.

## Reminder Logic

Reminder continues until:

```text id="4d7g9k"
Date Reporting != empty
```

---

# 12. Edge Cases

## Invalid Dates

* malformed dates,
* text instead of dates,
* future allotment dates.

## Excel File Locked

If Excel is already open:

* retry safely,
* avoid corruption.

## Missing Columns

System should:

* log error,
* notify admin.

## Duplicate FIR Numbers

Handle independently using row index.

## Empty Rows

Ignore safely.

## System Restart

Resume monitoring automatically.

---

# 13. Security Requirements

## File Safety

* Never delete original records.
* Avoid destructive overwrites.

## Path Validation

Prevent invalid file paths.

## Access

Local-system-only operation.

## Logging

Do not log sensitive case content beyond operational necessity.

## Backup

Maintain automatic backup copies before edits.

---

# 14. Performance Requirements

## Excel Scan Time

< 5 seconds for:

* up to 5000 rows.

## Notification Delay

< 2 seconds after detection.

## Memory Usage

< 250 MB RAM.

## CPU Usage

Minimal background utilization.

---

# 15. File Structure Rules

```text id="lkg6hj"
FSL_Reminder_System/
│
├── main.py
├── config.py
├── excel_handler.py
├── notifier.py
├── tracker.py
├── scheduler.py
├── logger.py
│
├── assets/
│   ├── icons/
│   └── styles/
│
├── logs/
│
├── backups/
│
├── data/
│   └── reminders.json
│
└── requirements.txt
```

## Rules

* One responsibility per module.
* No business logic inside UI files.
* All configuration centralized.

---

# 16. Development Priorities

## Phase 1 — Core Logic

* Excel reading
* Date validation
* Overdue detection

## Phase 2 — Excel Formatting

* Row highlighting
* Save handling
* Backup system

## Phase 3 — Notifications

* Desktop reminders
* Click-to-open Excel

## Phase 4 — Tray Application

* Background execution
* Auto startup

## Phase 5 — Stability

* Logging
* Edge case handling
* Performance optimization

## Phase 6 — Optional Enhancements

* Dashboard
* Officer analytics
* PDF exports
* Search/filter system

---

# 17. Out of Scope

The following are NOT part of Phase 1:

* Cloud synchronization
* Multi-user real-time collaboration
* Online database systems
* Web application deployment
* AI/ML prediction systems
* OCR/document scanning
* Facial recognition
* FIR content analysis
* Role-based authentication systems
* Mobile application support
* Internet-dependent functionality
* Full forensic case management system
* Automatic report generation from FIR documents
