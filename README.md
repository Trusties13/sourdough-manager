# Sourdough Manager

A focused, local-first Home Assistant custom integration that answers two
questions:

1. When was my sourdough starter last fed?
2. When is it due to be fed again?

Each starter is represented by one Home Assistant device.

## Features

- **Fed now** button for one-tap logging
- Compact **Last fed date** and **Last fed time** controls for late logging
- Bench or fridge storage selector
- Configurable bench frequency, defaulting to 48 hours
- Configurable fridge frequency, defaulting to 168 hours (7 days)
- Configurable reminder lead time, defaulting to 12 hours
- One or more selectable Home Assistant notification targets
- Repeating overdue reminders every 30 minutes until the next feed is recorded
- Human-friendly configuration summaries on the starter device
- Last-fed and next-feed timestamps
- Feed-due and feed-due-soon binary sensors
- Overdue duration on the next-feed sensor
- Events for optional Home Assistant automations
- Startup-safe minute-by-minute deadline updates
- Multiple starters, with one device per starter
- Automatic migration of last-fed time and location from pre-1.0 versions

## Installation

### HACS custom repository

1. In HACS, open **Integrations**, then **Custom repositories**.
2. Add `https://github.com/Trusties13/sourdough-manager` as an **Integration**.
3. Install **Sourdough Manager** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and add
   **Sourdough Manager**.

### Manual

Copy `custom_components/sourdough_manager` to:

```text
/config/custom_components/sourdough_manager
```

Restart Home Assistant, then add the integration through
**Settings → Devices & services**.

## Everyday use

The integration creates:

- Storage location
- Last fed
- Next feed due
- Feed due soon
- Feed due
- Fed now
- Last fed date
- Last fed time
- Bench feed frequency
- Fridge feed frequency
- Reminder lead time
- Notification targets

After feeding the starter, press **Fed now**. The deadline is calculated from
the selected storage location and its configured frequency.

Changing the storage location immediately recalculates the deadline from the
existing last-fed time.

## Feeding reminders

Open **Settings → Devices & services → Sourdough Manager → Configure**.

- **Bench feed frequency:** hours between feeds; default 48
- **Fridge feed frequency:** hours between feeds; default 168
- **Reminder lead time:** hours before the deadline; default 12, or 0 to
  disable the early reminder
- **Notification targets:** one or more `notify` entities

Changing a frequency immediately recalculates the next deadline.
The integration sends one early reminder, then sends an overdue reminder every
30 minutes after the deadline until **Fed now** is pressed or **Set last fed
date** or **Last fed time** is changed.

## Record an earlier feed

If you forgot to press **Fed now**, edit **Last fed date** and/or **Last fed
time** in the starter's Configuration section. This recalculates the next
deadline and resets the reminder cycle.

Automations can also record an earlier feed with this action:

```yaml
action: sourdough_manager.record_feed
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  fed_at: "2026-07-25T21:30:00+10:00"
```

Leave out `fed_at` to record the current time.

## Automation events

The integration fires:

- `sourdough_manager_feed_recorded`
- `sourdough_manager_feed_due_soon`
- `sourdough_manager_feed_overdue`
- `sourdough_manager_location_changed`

Events include the starter's config-entry ID, last-fed time, next deadline and
location. Example notification automations are in
[`examples/automations.yaml`](examples/automations.yaml).

## Upgrading from an earlier version

Version 1.0 automatically retains the most recent feed time and current
bench/fridge location. Detailed fermentation, quantity and prediction entities
are retired and removed from the entity registry. Their old Recorder history is
not deleted.

## Development

```bash
python -m compileall custom_components
python -m pytest
ruff check .
```

Home Assistant and HACS validation workflows run on pull requests.

## Licence

MIT
