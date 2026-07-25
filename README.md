# Sourdough Manager

A local-first Home Assistant custom integration for tracking sourdough starter feeds, fermentation cycles, peak predictions, refrigeration and starter quantity.

Each configured starter becomes its own Home Assistant device. The integration creates its sensors and action buttons automatically; no YAML helpers are required.

## Features

- UI config flow and options flow
- Multiple starters, with one device per starter
- Atomic `sourdough_manager.record_feed` action
- Dashboard-friendly feed inputs and a one-tap **Record feed** button
- Remembered starter, water, flour and flour-type values
- Optional empty-jar tare and total weight with jar
- Suggested discard, water and flour quantities
- Next-feed time, feeding count and plain-English instructions
- Mature, new-starter and refrigerated maintenance programmes
- Feed ratio, resulting hydration and current-weight calculations
- Recently fed, fermenting, approaching peak, at peak, falling, hungry, refrigerated and warming states
- Conservative peak estimate and window
- Optional Home Assistant temperature sensor, with a configurable fallback
- Personalised predictions after three comparable marked peaks
- Mark peak, refrigerate, remove from fridge and cancel-cycle buttons
- Discard and use actions that adjust current quantity
- Versioned local storage for active state, feed history and events

Predictions are estimates, not direct measurements of rise or food safety.

## Installation

### HACS custom repository

1. In HACS, open **Integrations**, then the three-dot menu and **Custom repositories**.
2. Add `https://github.com/Trusties13/sourdough-manager` as an **Integration**.
3. Install **Sourdough Manager** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, search for **Sourdough Manager**, and add your starter.

### Manual

Copy `custom_components/sourdough_manager` to:

```text
/config/custom_components/sourdough_manager
```

Restart Home Assistant, then add the integration through **Settings → Devices & services**.

## Record a feed

For everyday use, add the generated feed controls to a dashboard:

- Starter retained
- Water added
- Flour added
- Feed flour type
- Record feed

Adjust only the values that changed and press **Record feed**. The integration
captures all displayed values together, recalculates the cycle and remembers the
values for next time. Developer Tools are not required.

The configuration options set the initial feed amounts, empty-jar weight and
programme:

- **Mature starter** uses the predicted peak window to suggest the next feed.
- **New starter programme** provides Day 1–7+ guidance, using 24-hour feeds
  initially and 12-hour feeds from Day 6.
- **Refrigerated maintenance** uses the configured refrigerated reminder.

The action remains available for automations and retrospective entries:

Use **Developer tools → Actions** or call the action from a script or dashboard:

```yaml
action: sourdough_manager.record_feed
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  starter_retained_g: 30
  water_added_g: 30
  flour_added_g: 30
  flour_type: bread_flour
  notes: "Routine maintenance feed"
```

`fed_at` is optional and accepts a timestamp for retrospective entries. If omitted, the current time is used.

For a 30 g starter, 30 g water and 30 g flour feed, the integration records:

- ratio: 1:1:1
- total weight: 90 g
- resulting hydration: 100% when the retained starter is 100% hydration

## Entities

Typical generated entities include:

- Status
- Last fed
- Expected peak
- Current weight
- Feed ratio
- Hydration
- Cycle progress
- Prediction confidence
- Temperature at feed
- Last peak duration
- Starter retained, water added, flour added and flour type controls
- Record feed
- Suggested discard, water and flour
- Total weight including the empty jar
- Next feed due, total feedings and next feeding instructions
- Optional programme day and phase
- Mark peak
- Refrigerate
- Remove from fridge
- Cancel cycle

Peak-window start and end sensors are available but disabled by default.

## Prediction model

The initial model uses feed inoculation, temperature and refrigeration state. It follows a Q10-style temperature adjustment and returns a broad low-confidence window.

After at least three comparable cycles have an observed peak, the model blends similar personal history with the baseline. Recent storage retains up to 250 completed cycles and 500 events per starter. Mark the visible maximum rise using **Mark peak** to provide useful learning data.

## Quantity actions

```yaml
action: sourdough_manager.record_discard
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  amount_g: 60
```

```yaml
action: sourdough_manager.record_use
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
  amount_g: 80
```

Both actions clamp the resulting current weight at zero.

## Events

The integration fires:

- `sourdough_manager_feed_recorded`
- `sourdough_manager_peak_marked`
- `sourdough_manager_refrigerated`
- `sourdough_manager_removed_from_fridge`
- `sourdough_manager_cycle_cancelled`
- `sourdough_manager_record_discard`
- `sourdough_manager_record_use`

Every event includes the starter's `config_entry_id`.

## Development

Run the fast validation suite with:

```bash
python -m compileall custom_components
python -m pytest
ruff check .
```

Home Assistant and HACS validation workflows run on pull requests.

## Licence

MIT
