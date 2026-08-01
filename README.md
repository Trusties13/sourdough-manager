# Sourdough Manager

Sourdough Manager is a local-first Home Assistant custom integration for
tracking when a sourdough starter was last fed and calculating when it should
be fed again. It provides a simple **Fed now** workflow, separate bench and
fridge schedules, and optional reminders through push notifications, spoken
announcements and colour-capable lights.

Each starter is represented as its own Home Assistant device, with native
entities for dashboards, automations and manual corrections. All information
is stored locally in Home Assistant; no cloud account or external service is
required.

## Highlights

- **Simple feed tracking:** record a feed with one press, correct a late entry,
  or use the combined **Feed and refrigerate** action.
- **Flexible scheduling:** configure separate bench and fridge intervals,
  preferred feeding times, one-off delays and custom deadlines.
- **Clear status:** see the last feed, next deadline, due-today, due-soon,
  overdue and missed-feed information at a glance.
- **Optional reminders:** send push, audio and light alerts independently, with
  quiet hours, snoozing, Holiday Mode policies and escalation limits.
- **Actionable notifications:** Companion App alerts can record **Fed now** or
  snooze reminders without opening Home Assistant.
- **Safe household alerts:** audio can depend on occupancy; media-player volume
  and light state are restored after each reminder.
- **Home Assistant native:** supports multiple starters, visual automation
  events, a feeding calendar, recent feed history, Repairs and NFC or physical
  button workflows.

## Installation

### HACS custom repository

1. In HACS, open **Integrations**, then **Custom repositories**.
2. Add `https://github.com/Trusties13/sourdough-manager` as an **Integration**.
3. Install **Sourdough Manager** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and select
   **Sourdough Manager**.

### Manual installation

Copy `custom_components/sourdough_manager` into:

```text
/config/custom_components/sourdough_manager
```

Restart Home Assistant, then add **Sourdough Manager** through
**Settings → Devices & services**.

## Quick start

Only four values are needed to create a working feeding schedule:

- **Starter name**
- **Storage location** — bench or fridge
- **Bench feed frequency** — defaults to 48 hours
- **Fridge feed frequency** — defaults to 168 hours (7 days)

**Last fed** is optional during setup. Leave it empty and press **Fed now**
after installation, or set the date and time later. The next-feed deadline
becomes available after the first feed is recorded.

After feeding:

1. Press **Fed now** on the starter device or dashboard.
2. Sourdough Manager records the time.
3. The next deadline is calculated from the selected storage location and its
   configured frequency.

Changing the storage location immediately recalculates the deadline from the
existing last-fed time.

## Optional configuration

Open **Settings → Devices & services → Sourdough Manager → Configure** to add
any of the following features:

| Capability | Optional configuration |
| --- | --- |
| Consistent clock times | Preferred bench and fridge feeding times |
| Push reminders | One or more `notify` entities and an optional feed confirmation |
| Reminder timing | Lead time, overdue interval, quiet hours and snooze duration |
| Holiday Mode | An existing binary sensor and push/all/ignore policy |
| Spoken reminders | A TTS provider, media players, volume and repeat interval |
| Presence-aware audio | An existing household-occupied binary sensor |
| Light reminders | Colour-capable lights, reminder colour and pulse timing |
| Escalation controls | Maximum disruptive reminders and overdue duration |

Leave target selectors empty and keep the corresponding feature disabled when
it is not required. The core **Fed now → next feed due** schedule works without
notification, media-player, light, Holiday Mode or occupancy entities.

## Scheduling and corrections

Enable **Use a preferred feeding time** to align interval-based deadlines to a
consistent local clock time. Bench and fridge storage can use different times.

When a feed is due today or overdue, the device exposes controls to delay the
deadline by one hour, three hours or until tomorrow morning. The next-feed
deadline can also be edited directly without changing the last-fed time.

If a feed was logged late, edit **Last fed date** and **Last fed time** on the
starter device. This recalculates the deadline and resets the reminder cycle.

## Reminders

Scheduled reminders are optional and controlled by a master **Reminders**
switch. Push, audio and light channels can also be enabled independently.

The normal reminder sequence is:

1. A due-soon reminder is sent at the configured lead time.
2. A due reminder is sent at the deadline.
3. Overdue reminders repeat at the configured interval until a feed is
   recorded, the cycle is snoozed, or reminders are disabled.

Quiet hours pause scheduled reminders without discarding them. Holiday Mode can
suppress push only, suppress every reminder channel, or be ignored. **Silent
until next feed** pauses the current reminder cycle and resets automatically
when the next feed is recorded.

Companion App notifications include **Fed now** and **Snooze** actions. Stable
notification tags ensure repeated overdue reminders replace the previous alert
instead of stacking. Overdue titles and wording become progressively firmer as
the delay increases, and the overdue notification is cleared after feeding.

### Audio reminders

Audio reminders use Home Assistant's `tts.speak` action. Before an
announcement, Sourdough Manager captures the media player's current volume,
uses the configured announcement volume, then restores the previous level.
Unavailable players are skipped. Audio can optionally be limited to periods
when an existing household-occupied sensor is on.

### Light reminders

Selected colour-capable lights pulse in the configured reminder colour whenever
an enabled push or audio reminder is delivered. Lights that were already on
alternate between the reminder colour and their original colour; lights that
were off return to off. Brightness, colour, colour mode and effect are restored
afterwards.

### Testing reminders

The starter device includes **Test push reminder** and **Test audio reminder**
buttons. Tests use the configured targets, include the light alert and do not
change the feed schedule. They remain available while scheduled reminders are
disabled, snoozed or within quiet hours.

## Dashboard

A dependency-free Lovelace example is provided in
[`examples/dashboard.yaml`](examples/dashboard.yaml). It includes:

- schedule status, last feed and next deadline
- storage and reminder controls
- **Fed now**, **Snooze** and reminder-test actions
- late-entry and one-off deadline controls
- feeding calendar and recent history
- conditional rescheduling and **Feed and refrigerate** actions

Copy the YAML into a Manual card and replace `main_starter` if your generated
entity IDs use a different prefix.

## Physical buttons and NFC tags

Any physical button available in Home Assistant can press the starter's
**Fed now** button through an automation. Rapid duplicate feed actions within
10 seconds are ignored.

An NFC tag attached to the starter jar can use the same action:

```yaml
alias: Sourdough - NFC feed log
triggers:
  - trigger: tag
    tag_id: REPLACE_WITH_YOUR_TAG_ID
actions:
  - action: button.press
    target:
      entity_id: button.main_starter_fed_now
```

Create the tag in **Settings → Tags**, replace the example entity ID with your
starter's **Fed now** entity, then scan the tag after feeding.

## Actions and automation events

Record the current time or an earlier feed from an automation:

```yaml
action: sourdough_manager.record_feed
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  fed_at: "2026-07-25T21:30:00+10:00"
```

Omit `fed_at` to record the current time.

Set a one-off custom deadline without changing the last-fed time:

```yaml
action: sourdough_manager.set_next_feed_due
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  due_at: "2026-08-02T09:00:00+10:00"
```

Sourdough Manager fires these Home Assistant events:

- `sourdough_manager_feed_recorded`
- `sourdough_manager_feed_due_soon`
- `sourdough_manager_feed_overdue`
- `sourdough_manager_location_changed`

Events include the starter's config-entry ID, last-fed time, next deadline and
storage location. The same lifecycle is exposed through the starter's native
event entity, including `deadline_delayed`, so events are selectable in the
visual automation editor. Examples are available in
[`examples/automations.yaml`](examples/automations.yaml).

## Configuration health

If a configured notification, TTS, media-player or light entity is deleted,
Sourdough Manager creates a Home Assistant repair warning and turns on the
starter's **Configuration problem** binary sensor. Select valid targets in the
integration options and the warning clears automatically.

## Development

```bash
python -m compileall custom_components
python -m pytest
ruff check .
```

Home Assistant, HACS and test validation workflows run on every pull request.

## Licence

Sourdough Manager is licensed under the [MIT Licence](LICENSE).
