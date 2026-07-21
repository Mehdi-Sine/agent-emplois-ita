from datetime import datetime, timezone

from app.schedule import should_run_now


def test_guard_runs_at_midnight_paris_in_winter() -> None:
    assert should_run_now(False, datetime(2026, 1, 5, 23, 0, tzinfo=timezone.utc))


def test_guard_runs_at_one_am_paris_in_winter() -> None:
    assert should_run_now(False, datetime(2026, 1, 6, 0, 0, tzinfo=timezone.utc))


def test_guard_runs_at_one_am_paris_in_summer() -> None:
    assert should_run_now(False, datetime(2026, 7, 6, 23, 0, tzinfo=timezone.utc))


def test_guard_rejects_other_paris_hours() -> None:
    assert not should_run_now(False, datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc))


def test_guard_can_be_bypassed_for_manual_workflow() -> None:
    assert should_run_now(True, datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc))
