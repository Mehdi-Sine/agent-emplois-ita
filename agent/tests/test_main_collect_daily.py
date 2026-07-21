from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.main_collect_daily import run_collection
from app.models import ConnectorResult


class FakeRepository:
    synced_slugs: list[str] = []

    def __init__(self, url: str, key: str) -> None:
        self.url = url
        self.key = key

    def sync_sources(self, sources):
        FakeRepository.synced_slugs = [source.slug for source in sources]
        return {source.slug: {"id": f"source-{source.slug}"} for source in sources}

    def create_pipeline_run(self, trigger_type: str, total_sources: int):
        return {"id": "pipeline-1"}

    def create_source_run(self, pipeline_run_id: str, source_id: str):
        return {"id": f"run-{source_id}"}

    def upsert_offers_for_source(self, **kwargs):
        raise AssertionError("No offers are returned by this test connector")

    def finalize_source_run(self, **kwargs):
        pass

    def finalize_pipeline_run(self, **kwargs):
        pass


class FakeConnector:
    def __init__(self, source):
        self.source = source

    def fetch(self, client):
        now = datetime.now(timezone.utc)
        return ConnectorResult(
            source_slug=self.source.slug,
            status="SUCCESS",
            started_at=now,
            ended_at=now,
            offers=[],
            raw_items=[],
        )


class FakeHttpClient:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_skipped_cron_sets_github_output_without_requiring_supabase(tmp_path, monkeypatch):
    output_path = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))

    assert run_collection(skip_paris_guard=False) == 0

    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "did_run=false",
        "pipeline_run_id=",
    ]


def test_daily_collection_filters_disabled_sources_and_exports_pipeline_id(tmp_path, monkeypatch):
    output_path = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    FakeRepository.synced_slugs = []

    monkeypatch.setattr(
        "app.main_collect_daily.Settings.from_env",
        lambda: SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_service_key="service-key",
            user_agent="test-agent",
            archive_missed_threshold=2,
        ),
    )
    monkeypatch.setattr(
        "app.main_collect_daily.load_sources_config",
        lambda: [
            {
                "slug": "enabled_source",
                "name": "Enabled",
                "site_url": "https://example.com",
                "jobs_url": "https://example.com/jobs",
                "enabled": True,
                "mode": "http",
                "timeout_seconds": 20,
            },
            {
                "slug": "disabled_source",
                "name": "Disabled",
                "site_url": "https://disabled.example.com",
                "jobs_url": "https://disabled.example.com/jobs",
                "enabled": False,
                "mode": "http",
                "timeout_seconds": 20,
            },
        ],
    )
    monkeypatch.setattr("app.main_collect_daily.CONNECTOR_REGISTRY", {"enabled_source": FakeConnector, "disabled_source": FakeConnector})
    monkeypatch.setattr("app.main_collect_daily.SupabaseRepository", FakeRepository)
    monkeypatch.setattr("app.main_collect_daily.build_connector", lambda source: FakeConnector(source))
    monkeypatch.setattr("app.main_collect_daily.build_http_client", lambda *args, **kwargs: FakeHttpClient())
    monkeypatch.setattr("app.main_collect_daily.RUNS_DIR", tmp_path / "runs")

    assert run_collection(skip_paris_guard=True) == 0

    assert FakeRepository.synced_slugs == ["enabled_source"]
    assert output_path.read_text(encoding="utf-8").splitlines() == [
        "did_run=true",
        "pipeline_run_id=pipeline-1",
    ]
