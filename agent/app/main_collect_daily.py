from datetime import datetime, timezone

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import RUNS_DIR, Settings, load_sources_config
from app.http import build_http_client
from app.logging_utils import build_logger
from app.models import ConnectorResult, PersistResult, SourceConfig
from app.persistence import SupabaseRepository
from app.reporting import build_pipeline_status, summarize_run
from app.connectors.registry import CONNECTOR_REGISTRY, build_connector


logger = build_logger()


def should_run_now(skip_guard: bool) -> bool:
    if skip_guard:
        return True
    now_paris = datetime.now(ZoneInfo("Europe/Paris"))
    return now_paris.minute == 1 and now_paris.hour in {0, 12}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_offers_csv(path: Path, offers: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not offers:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in offers for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(offers)


def run_collection(selected_sources: list[str] | None = None, skip_paris_guard: bool = False) -> int:
    if not should_run_now(skip_paris_guard):
        logger.info("Exécution ignorée par le garde-fou horaire Europe/Paris.")
        return 0

    settings = Settings.from_env()
    source_rows = [SourceConfig(**row) for row in load_sources_config()]
    if selected_sources:
        selected_set = set(selected_sources)
        source_rows = [source for source in source_rows if source.slug in selected_set]
    else:
        source_rows = [source for source in source_rows if source.enabled]
    source_rows = [source for source in source_rows if source.slug in CONNECTOR_REGISTRY]

    if not source_rows:
        logger.info("Aucune source sélectionnée.")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    repository = SupabaseRepository(settings.supabase_url, settings.supabase_service_key)
    sources_db = repository.sync_sources(source_rows)
    pipeline_run = repository.create_pipeline_run("cron" if not selected_sources else "manual", len(source_rows))

    source_results: list[ConnectorResult] = []
    persist_results: list[PersistResult] = []

    for source in source_rows:
        logger.info(f"Moisson de {source.slug}")
        source_db = sources_db[source.slug]
        source_run = repository.create_source_run(pipeline_run["id"], source_db["id"])
        connector = build_connector(source)
        raw_path = run_dir / f"offers_raw_{source.slug}.json"
        normalized_path = run_dir / f"offers_normalized_{source.slug}.csv"

        with build_http_client(settings.user_agent, source.timeout_seconds) as client:
            result = connector.fetch(client)

        write_json(raw_path, result.raw_items)
        write_offers_csv(normalized_path, [offer.model_dump(mode="json") for offer in result.offers])

        persist_result = None
        if result.status == "SUCCESS":
            persist_result = repository.upsert_offers_for_source(
                source=source,
                source_id=source_db["id"],
                source_run_id=source_run["id"],
                offers=result.offers,
                archive_missed_threshold=settings.archive_missed_threshold,
            )
            persist_results.append(persist_result)

        repository.finalize_source_run(
            source_run_id=source_run["id"],
            connector_result=result,
            persist_result=persist_result,
            raw_output_path=str(raw_path.relative_to(RUNS_DIR.parent)),
            normalized_output_path=str(normalized_path.relative_to(RUNS_DIR.parent)),
        )
        source_results.append(result)

    summary = summarize_run(source_results, persist_results)
    status = build_pipeline_status(source_results)
    repository.finalize_pipeline_run(
        pipeline_run_id=pipeline_run["id"],
        status=status,
        sources_success=summary["success"],
        sources_failed=summary["failed"],
        new_offers=summary["offers_new"],
        updated_offers=summary["offers_updated"],
        archived_offers=summary["offers_archived"],
        summary_json=summary,
    )
    write_json(run_dir / "run_summary.json", summary)
    write_json(
        run_dir / "source_runs.json",
        [result.model_dump(mode="json") for result in source_results],
    )
    logger.info(json.dumps(summary, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", help="slug source à lancer")
    parser.add_argument("--skip-paris-guard", action="store_true")
    args = parser.parse_args()
    return run_collection(selected_sources=args.source, skip_paris_guard=args.skip_paris_guard)


if __name__ == "__main__":
    raise SystemExit(main())
