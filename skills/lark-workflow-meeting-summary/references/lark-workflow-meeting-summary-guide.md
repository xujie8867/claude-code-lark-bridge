# Meeting Summary Workflow — Usage Guide

## Overview
Generates structured meeting summary reports from Lark meeting minutes within a specified time range.

## Quick Start
```bash
lark-cli workflow-meeting-summary +generate --from 2026-06-01 --to 2026-06-07
```

## Output Format
The report includes:
- **Period**: Time range covered
- **Meetings**: List of meetings with date, title, participants
- **Key Decisions**: Decisions made in each meeting
- **Action Items**: Tasks and follow-ups
- **Summary**: Overall period summary

## Tips
- Run weekly for regular reporting (Monday morning recommended)
- Filter by specific calendars or participants when needed
- Combine with lark-task to auto-create action items from meeting notes
