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
- Configurable overdue reminder interval
- Optional overnight quiet hours
- One or more selectable Home Assistant notification targets
- Repeating overdue reminders until the next feed is recorded
- 1, 3 or 12-hour snooze control
- Companion App notifications with **Fed now** and **Snooze** actions
- Dynamic notification titles and progressively firmer overdue wording
- Stable per-type notification tags, preventing repeated alerts from stacking
- Optional text-to-speech reminders on one or more media players
- Independent audio lead time and repeat interval
- Optional red-flash reminders on selected colour lights
- Automatic restoration of each reminder light's prior state and colour
- Optional confirmation when a feed is recorded
- Duplicate protection for rapid physical-button presses
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
- Overdue reminder interval
- Quiet hours
- Feed confirmation
- Last reminder sent
- Snooze duration
- Snooze reminders
- Audio reminders
- Audio voice
- Audio targets
- Audio reminder lead time
- Audio reminder interval
- Last audio reminder
- Light reminder targets
- Last light reminder

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
- **Overdue reminder interval:** minutes between reminders after feeding is due
- **Quiet hours:** optional start and end times that suppress scheduled reminders
- **Confirm recorded feeds:** optionally acknowledge successful feed logging
- **Enable audio reminders:** speak reminders through selected media players
- **Text-to-speech provider:** the Home Assistant TTS entity/voice to use
- **Audio targets:** one or more media players
- **Audio reminder lead time:** when spoken reminders begin
- **Audio reminder interval:** independent cadence for repeated announcements
- **Audio announcement volume:** temporary playback level for announcements
- **Light reminder targets:** colour-capable lights to accompany reminders
- **Light reminder colour:** selectable RGB colour, defaulting to red

Changing a frequency immediately recalculates the next deadline.
The integration sends one early reminder, then sends an overdue reminder every
configured interval after the deadline until **Fed now**, **Last fed date** or
**Last fed time** is changed. Reminders resume after quiet hours or a snooze.

Companion App targets receive **Fed now** and **Snooze** actions. Other
notification entities receive the same reminder text without action buttons.
Due-soon, overdue and confirmation notifications use separate stable tags.
Repeated overdue reminders replace the previous overdue alert, and their
wording becomes firmer after 2, 12 and 24 hours overdue.

Audio reminders use Home Assistant's standard `tts.speak` action. They follow
the same quiet hours and snooze state as push notifications, skip unavailable
media players, use the escalating overdue wording and stop as soon as a feed is
recorded. Before each announcement, the player's existing volume is captured
and the configured announcement volume is applied. The previous volume is
restored after playback finishes.

Selected reminder lights flash in the configured colour three times whenever a scheduled push or
audio reminder is actually sent. If both types are sent during the same update,
the lights flash only once. Light reminders respect quiet hours and snooze.
Each light's on/off state, brightness, colour mode, colour and effect are
captured before flashing and restored afterwards. Originally-off lights finish
off after their previous colour settings have been reapplied. Lights that were
already on alternate between the reminder colour and their original colour three times without
being switched off.

The device also provides separate **Test push reminder** and **Test audio
reminder** buttons. Tests use the configured targets, trigger the same light
flash and do not alter the last-fed time or reminder schedule. Test buttons run
even during quiet hours or a snooze so the complete configuration can be
checked immediately. Both tests use the same wording as a one-hour-overdue feed
reminder, clearly prefixed as a test.

## Physical button or NFC tag

Any physical button in Home Assistant can run the starter's **Fed now** button
through an automation. Rapid duplicate presses within 10 seconds are ignored.

An NFC tag attached to the starter jar can do the same:

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
