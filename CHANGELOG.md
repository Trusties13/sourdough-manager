# Changelog

## 1.11.2

- Clearly identifies the minimum required setup and optional reminder integrations in the setup form, options form and README.

## 1.11.1

- Adds the repository-level HACS brand icon so the integration icon appears in HACS listings.

## 1.11.0

- Adds configurable Holiday Mode handling: suppress push only, suppress every reminder, or ignore Holiday Mode.
- Adds independent push, audio and light channel switches.
- Adds optional occupancy-aware audio using a configurable household-occupied binary sensor.
- Adds configurable audio/light escalation limits by reminder count and overdue duration.
- Adds a temporary Silent until next feed control.
- Adds expanded reminder status, channel and next-reminder diagnostics.

## 1.10.0

- Pauses all scheduled reminder channels while the configured existing holiday-mode binary sensor is on.
- Supports separate preferred feeding times for bench and refrigerated storage.
- Makes delay and manual deadline controls available only on the due date or while overdue.
- Adds Due today, Schedule status and Missed feed count sensors.
- Adds a Feed and refrigerate action.
- Adds an editable one-off next-feed deadline.
- Expands the example dashboard with conditional rescheduling and recent feed history.

## 1.9.0

- Add optional preferred feeding-time alignment.
- Add one-off deadline delays and a custom-deadline action.
- Retain the most recent 20 feed records.
- Add a feeding calendar and native starter event entity.
- Report deleted reminder targets through Home Assistant Repairs.
- Repair and validate the example dashboard.
- Add tag-driven GitHub release automation.

## 1.8.1

- Add complete push, audio and light reminder controls.
- Add reminder tests, snoozing, quiet hours and manual feed correction.
