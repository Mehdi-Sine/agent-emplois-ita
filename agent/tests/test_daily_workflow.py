from pathlib import Path


WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "daily.yml"


def test_daily_workflow_has_one_cron_and_bypasses_duplicate_time_guard() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert content.count('- cron: "0 23 * * *"') == 1
    assert "outside_paris_window" not in content
    assert "python -m app.main_collect_daily --skip-paris-guard" in content


def test_daily_email_uses_current_pipeline_outputs() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "steps.collect.outputs.did_run == 'true'" in content
    assert "PIPELINE_RUN_ID: ${{ steps.collect.outputs.pipeline_run_id }}" in content
