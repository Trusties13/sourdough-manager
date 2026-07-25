"""Tests for pure calculations."""
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "sourdough_models",
    Path(__file__).parents[1] / "custom_components/sourdough_manager/models.py",
)
models = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = models
SPEC.loader.exec_module(models)

cycle_progress = models.cycle_progress
cycle_status = models.cycle_status
feed_ratio = models.feed_ratio
predict_peak = models.predict_peak
resulting_hydration = models.resulting_hydration
feeding_instruction = models.feeding_instruction
next_feed_time = models.next_feed_time
programme_day = models.programme_day
programme_phase = models.programme_phase


def test_feed_calculations():
    assert feed_ratio(30.0, 30.0, 30.0) == "1:1:1"
    assert resulting_hydration(30, 30, 30, 100) == 100
    assert resulting_hydration(20, 40, 50, 100) == 83.3


def test_baseline_prediction_changes_with_temperature_and_ratio():
    warm = predict_peak(30, 30, 26, False, [])
    cool = predict_peak(30, 30, 18, False, [])
    larger = predict_peak(30, 90, 22, False, [])
    assert warm.hours < cool.hours
    assert larger.hours > 6
    assert warm.confidence == "low"


def test_cycle_state():
    data = {"location": "bench", "active_cycle": {"fed_at": "2026-01-01T00:00:00+00:00", "prediction": {"hours": 8, "low_hours": 7, "high_hours": 9}}}
    assert cycle_status(data, datetime(2026, 1, 1, 1, tzinfo=UTC)) == "recently_fed"
    assert cycle_status(data, datetime(2026, 1, 1, 6, tzinfo=UTC)) == "approaching_peak"
    assert cycle_status(data, datetime(2026, 1, 1, 8, tzinfo=UTC)) == "at_peak"
    assert cycle_progress(data, datetime(2026, 1, 1, 4, tzinfo=UTC)) == 50


def test_programmes_and_instructions():
    data = {
        "feed_count": 10,
        "current_weight_g": 90,
        "location": "bench",
        "active_cycle": {"fed_at": "2026-01-01T00:00:00+00:00"},
    }
    assert programme_day(data) == 6
    assert programme_phase(data, "new_starter") == "activation"
    assert next_feed_time(data, "new_starter", 14) == datetime(2026, 1, 1, 12, tzinfo=UTC)
    assert feeding_instruction(data, "mature", 30, 30, 30) == (
        "Retain 30 g starter, discard 60 g, then add 30 g water and 30 g flour."
    )
