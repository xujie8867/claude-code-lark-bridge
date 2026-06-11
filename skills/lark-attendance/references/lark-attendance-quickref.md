# Lark Attendance — Quick Reference

## Check Today's Records
```bash
lark-cli attendance +get-today --as user
```

## Check Records for a Date Range
```bash
lark-cli attendance +get-records --from 2026-06-01 --to 2026-06-10 --as user
```

## Location-Based Check-in
- Attendance uses GPS/network location
- Must be within the configured office geofence
- Check your organization's attendance policy for remote work rules

## Common Issues
- "Out of range": You're not within the office geofence
- "Already checked in": Duplicate check-in prevented
- "Holiday/Special day": Check organization calendar settings
