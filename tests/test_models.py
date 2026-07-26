"""Tests for focused scheduling calculations."""
import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

models_spec = importlib.util.spec_from_file_location(
    "sourdough_models",
    Path(__file__).parents[1] / "custom_components/sourdough_manager/models.py",
)
models = importlib.util.module_from_spec(models_spec)
assert models_spec.loader is not None
sys.modules[models_spec.name] = models
models_spec.loader.exec_module(models)


def test_next_feed_uses_location_frequency():
    fed = datetime(2026, 7, 25, 9, tzinfo=UTC)
    assert models.next_feed_due(fed, "bench", 48, 168) == datetime(
        2026, 7, 27, 9, tzinfo=UTC
    )
    assert models.next_feed_due(fed, "refrigerator", 48, 168) == datetime(
        2026, 8, 1, 9, tzinfo=UTC
    )


def test_due_and_due_soon_boundaries():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 26, 20, tzinfo=UTC)
    ) == (False, False)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 26, 22, tzinfo=UTC)
    ) == (False, True)
    assert models.schedule_state(
        due, 12, datetime(2026, 7, 27, 9, tzinfo=UTC)
    ) == (True, False)


def test_overdue_hours():
    due = datetime(2026, 7, 27, 9, tzinfo=UTC)
    assert models.overdue_hours(due, datetime(2026, 7, 27, 17, tzinfo=UTC)) == 8
    assert models.overdue_hours(due, datetime(2026, 7, 27, 8, tzinfo=UTC)) == 0


def test_migrates_existing_active_cycle_and_location():
    migrated = models.migrate_storage(
        {
            "active_cycle": {"fed_at": "2026-07-25T09:00:00+00:00"},
            "location": "refrigerator",
            "feed_history": [{"unused": True}],
        },
        "bench",
    )
    assert migrated == {
        "schema_version": 3,
        "last_fed": "2026-07-25T09:00:00+00:00",
        "location": "refrigerator",
        "location_changed_at": None,
    }
