from __future__ import annotations

import json

from app.workflow_event_log import append_jsonl, build_event_payload


def test_build_event_payload_includes_github_context(monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GITHUB_WORKFLOW", "ita-jobs-daily")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("PIPELINE_RUN_ID", "00000000-0000-0000-0000-000000000001")

    payload = build_event_payload("daily_workflow", "started", {"reason": "paris_window"})

    assert payload["event_type"] == "daily_workflow"
    assert payload["status"] == "started"
    assert payload["github_run_id"] == "12345"
    assert payload["github_run_attempt"] == "2"
    assert payload["github_workflow"] == "ita-jobs-daily"
    assert payload["github_event_name"] == "schedule"
    assert payload["pipeline_run_id"] == "00000000-0000-0000-0000-000000000001"
    assert payload["details_json"] == {"reason": "paris_window"}


def test_append_jsonl_writes_one_event_per_line(tmp_path):
    path = tmp_path / "events.jsonl"
    payload = {"event_type": "daily_workflow", "status": "started"}

    append_jsonl(payload, path)

    assert json.loads(path.read_text(encoding="utf-8")) == payload
