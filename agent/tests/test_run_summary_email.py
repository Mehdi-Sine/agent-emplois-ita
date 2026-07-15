from app.run_summary_email import _render_text


def test_render_text_uses_supabase_pipeline_field_names():
    body = _render_text(
        {
            "status": "SUCCESS",
            "trigger_type": "cron",
            "started_at": "2026-07-15T01:00:00+02:00",
            "ended_at": "2026-07-15T01:10:00+02:00",
        },
        [],
        {
            "config_total": 1,
            "enabled_total": 1,
            "ok_total": 1,
            "failed_total": 0,
            "offers_found": 0,
            "offers_new": 0,
            "offers_updated": 0,
            "offers_archived": 0,
        },
        None,
    )

    assert "Déclenchement : cron" in body
    assert "Fin : 14/07/2026 23:10 UTC" in body
