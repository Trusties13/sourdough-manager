"""Data models and calculations for Sourdough Manager."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import log
from statistics import median
from typing import Any


def parse_datetime(value: str) -> datetime | None:
    """Parse an ISO timestamp."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def feed_ratio(starter: float, water: float, flour: float) -> str:
    """Return a readable starter:water:flour ratio."""
    def part(value: float) -> str:
        result = value / starter
        return str(int(result)) if result.is_integer() else f"{result:.2f}".rstrip("0").rstrip(".")
    return f"1:{part(water)}:{part(flour)}"


def resulting_hydration(
    starter: float, water: float, flour: float, starter_hydration: float
) -> float:
    """Calculate hydration including flour and water in retained starter."""
    factor = starter_hydration / 100
    existing_flour = starter / (1 + factor)
    existing_water = starter - existing_flour
    return round((existing_water + water) / (existing_flour + flour) * 100, 1)


@dataclass(slots=True)
class Prediction:
    """Peak prediction."""

    hours: float
    low_hours: float
    high_hours: float
    confidence: str
    source: str
    matching_feeds: int


def predict_peak(
    starter: float,
    flour: float,
    temperature: float,
    refrigerated: bool,
    history: list[dict[str, Any]],
) -> Prediction:
    """Predict peak duration using similar history, falling back to a baseline."""
    inoculation_ratio = max(flour / starter, 0.1)
    baseline = 6.0 + 4.35 * log(inoculation_ratio)
    baseline *= 2 ** ((22.0 - temperature) / 10.0)
    if refrigerated:
        baseline += 2.0

    matches: list[tuple[float, float]] = []
    for item in history:
        actual = item.get("actual_peak_hours")
        if actual is None:
            continue
        ratio_delta = abs(float(item.get("flour_g", 0)) / float(item.get("starter_g", 1)) - inoculation_ratio)
        temp_delta = abs(float(item.get("temperature_c", 22)) - temperature)
        if ratio_delta <= max(0.5, inoculation_ratio * 0.35) and temp_delta <= 4:
            weight = 1 / (1 + ratio_delta + temp_delta / 4)
            matches.append((float(actual), weight))

    if len(matches) >= 3:
        personalised = sum(value * weight for value, weight in matches) / sum(weight for _, weight in matches)
        predicted = personalised * 0.75 + baseline * 0.25
        spread = median(abs(value - personalised) for value, _ in matches) or 0.5
        confidence = "high" if len(matches) >= 8 and spread <= 1 else "medium"
        tolerance = max(0.75, min(2.5, spread * 1.75))
        return Prediction(predicted, max(1, predicted - tolerance), predicted + tolerance, confidence, "starter_history", len(matches))

    tolerance = max(1.5, baseline * 0.2)
    return Prediction(baseline, max(1, baseline - tolerance), baseline + tolerance, "low", "generic_baseline", len(matches))


def cycle_status(data: dict[str, Any], now: datetime | None = None) -> str:
    """Calculate current cycle state."""
    if data.get("location") == "refrigerator":
        return "refrigerated"
    if data.get("warming"):
        return "warming"
    cycle = data.get("active_cycle")
    if not cycle:
        return "awaiting_feed"
    if cycle.get("cancelled"):
        return "awaiting_feed"
    now = now or datetime.now(UTC)
    fed_at = parse_datetime(cycle["fed_at"])
    if fed_at is None:
        return "unknown"
    elapsed = (now - fed_at).total_seconds() / 3600
    expected = float(cycle["prediction"]["hours"])
    if cycle.get("actual_peak_at"):
        peak = parse_datetime(cycle["actual_peak_at"])
        since_peak = (now - peak).total_seconds() / 3600 if peak else 0
        return "at_peak" if since_peak <= 1 else ("falling" if since_peak <= expected * 0.5 else "hungry")
    low = float(cycle["prediction"]["low_hours"])
    high = float(cycle["prediction"]["high_hours"])
    if elapsed < expected * 0.15:
        return "recently_fed"
    if elapsed < expected * 0.7:
        return "fermenting"
    if elapsed < low:
        return "approaching_peak"
    if elapsed <= high:
        return "at_peak"
    if elapsed <= expected * 1.5:
        return "falling"
    return "hungry"


def cycle_progress(data: dict[str, Any], now: datetime | None = None) -> float | None:
    """Return estimated percentage progress towards peak."""
    cycle = data.get("active_cycle")
    if not cycle:
        return None
    fed_at = parse_datetime(cycle["fed_at"])
    if fed_at is None:
        return None
    elapsed = ((now or datetime.now(UTC)) - fed_at).total_seconds() / 3600
    return round(max(0, min(100, elapsed / float(cycle["prediction"]["hours"]) * 100)), 1)


def peak_times(cycle: dict[str, Any]) -> tuple[datetime, datetime, datetime]:
    """Return predicted peak and window timestamps."""
    fed_at = parse_datetime(cycle["fed_at"])
    prediction = cycle["prediction"]
    return tuple(fed_at + timedelta(hours=float(prediction[key])) for key in ("hours", "low_hours", "high_hours"))
