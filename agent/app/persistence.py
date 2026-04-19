from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.models import ConnectorResult, NormalizedOffer, PersistResult, RunStatus, SourceConfig


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def is_offer_listed_inactive(raw_payload: dict[str, Any] | None) -> bool:
    if not raw_payload:
        return False

    if bool(raw_payload.get("is_filled")):
        return True

    listing_status = str(raw_payload.get("listing_status") or "").strip().lower()
    inactive_statuses = {
        "filled",
        "closed",
        "archived",
        "inactive",
        "pourvue",
        "pourvues",
        "pourvu",
        "closed_filled",
    }
    return listing_status in inactive_statuses


class SupabaseRepository:
    def __init__(self, url: str, key: str) -> None:
        self.client: Client = create_client(url, key)

    def sync_sources(self, sources: list[SourceConfig]) -> dict[str, dict[str, Any]]:
        rows = [
            {
                "slug": source.slug,
                "name": source.name,
                "site_url": str(source.site_url),
                "jobs_url": str(source.jobs_url),
                "is_enabled": source.enabled,
                "connector_type": source.mode,
                "config_json": source.model_dump(mode="json"),
            }
            for source in sources
        ]
        self.client.table("sources").upsert(rows, on_conflict="slug").execute()
        result = self.client.table("sources").select("*").execute()
        return {row["slug"]: row for row in result.data or []}

    def create_pipeline_run(self, trigger_type: str, total_sources: int) -> dict[str, Any]:
        payload = {
            "trigger_type": trigger_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS",
            "total_sources": total_sources,
            "sources_success": 0,
            "sources_failed": 0,
            "new_offers": 0,
            "updated_offers": 0,
            "archived_offers": 0,
            "summary_json": {},
        }
        result = self.client.table("pipeline_runs").insert(payload).execute()
        return result.data[0]

    def finalize_pipeline_run(
        self,
        pipeline_run_id: str,
        status: RunStatus,
        sources_success: int,
        sources_failed: int,
        new_offers: int,
        updated_offers: int,
        archived_offers: int,
        summary_json: dict[str, Any],
    ) -> None:
        self.client.table("pipeline_runs").update(
            {
                "status": status,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "sources_success": sources_success,
                "sources_failed": sources_failed,
                "new_offers": new_offers,
                "updated_offers": updated_offers,
                "archived_offers": archived_offers,
                "summary_json": json_safe(summary_json),
            }
        ).eq("id", pipeline_run_id).execute()

    def create_source_run(self, pipeline_run_id: str, source_id: str) -> dict[str, Any]:
        payload = {
            "pipeline_run_id": pipeline_run_id,
            "source_id": source_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "FAILED",
            "offers_found": 0,
            "offers_new": 0,
            "offers_updated": 0,
            "offers_archived": 0,
            "http_errors": 0,
            "parse_errors": 0,
            "metrics_json": {},
        }
        result = self.client.table("source_runs").insert(payload).execute()
        return result.data[0]

    def finalize_source_run(
        self,
        source_run_id: str,
        connector_result: ConnectorResult,
        persist_result: PersistResult | None,
        raw_output_path: str | None = None,
        normalized_output_path: str | None = None,
    ) -> None:
        payload = {
            "ended_at": connector_result.ended_at.isoformat(),
            "status": connector_result.status,
            "offers_found": len(connector_result.offers),
            "offers_new": persist_result.offers_new if persist_result else 0,
            "offers_updated": persist_result.offers_updated if persist_result else 0,
            "offers_archived": persist_result.offers_archived if persist_result else 0,
            "http_errors": connector_result.http_errors,
            "parse_errors": connector_result.parse_errors,
            "error_message": connector_result.error_message,
            "raw_output_path": raw_output_path,
            "normalized_output_path": normalized_output_path,
            "metrics_json": {
                "discover_count": connector_result.discover_count,
                "parsed_count": connector_result.parsed_count,
                "duration_ms": connector_result.duration_ms,
                "offers_unchanged": persist_result.offers_unchanged if persist_result else 0,
            },
        }
        self.client.table("source_runs").update(json_safe(payload)).eq("id", source_run_id).execute()

    def get_active_offers_for_source(self, source_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("offers")
            .select("id,source_offer_key,consecutive_missed_runs,is_active")
            .eq("source_id", source_id)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []

    def upsert_offers_for_source(
        self,
        source: SourceConfig,
        source_id: str,
        source_run_id: str,
        offers: list[NormalizedOffer],
        archive_missed_threshold: int,
    ) -> PersistResult:
        result = PersistResult(
            source_id=source_id,
            source_run_id=source_run_id,
            offers_found=len(offers),
        )
        active_rows = self.get_active_offers_for_source(source_id)
        current_keys = set()

        for offer in offers:
            current_keys.add(offer.source_offer_key)

            existing = (
                self.client.table("offers")
                .select("id,content_hash,is_active")
                .eq("source_id", source_id)
                .eq("source_offer_key", offer.source_offer_key)
                .limit(1)
                .execute()
            )
            existing_row = existing.data[0] if existing.data else None

            now_iso = datetime.now(timezone.utc).isoformat()
            raw_payload = json_safe(offer.raw_payload or {})
            listed_inactive = is_offer_listed_inactive(raw_payload)

            payload = {
                "source_id": source_id,
                "last_source_run_id": source_run_id,
                "source_offer_key": offer.source_offer_key,
                "source_url": offer.source_url,
                "application_url": offer.application_url,
                "title": offer.title,
                "organization": offer.organization,
                "location_text": offer.location_text,
                "city": offer.city,
                "region": offer.region,
                "country": offer.country,
                "contract_type": offer.contract_type,
                "offer_type": offer.offer_type,
                "remote_mode": offer.remote_mode,
                "posted_at": offer.posted_at.isoformat() if offer.posted_at else None,
                "description_text": offer.description_text,
                "content_hash": offer.content_hash,
                "is_active": not listed_inactive,
                "last_seen_at": now_iso,
                "archived_at": now_iso if listed_inactive else None,
                "consecutive_missed_runs": 0,
                "raw_payload": raw_payload,
            }

            if existing_row is None:
                payload["first_seen_at"] = now_iso
                insert_result = self.client.table("offers").insert(json_safe(payload)).execute()
                offer_id = insert_result.data[0]["id"]
                result.offers_new += 1
            else:
                offer_id = existing_row["id"]
                if (
                    existing_row["content_hash"] != offer.content_hash
                    or bool(existing_row["is_active"]) != (not listed_inactive)
                ):
                    self.client.table("offers").update(json_safe(payload)).eq("id", offer_id).execute()
                    result.offers_updated += 1
                else:
                    self.client.table("offers").update(
                        {
                            "last_seen_at": now_iso,
                            "last_source_run_id": source_run_id,
                            "consecutive_missed_runs": 0,
                            "is_active": not listed_inactive,
                            "archived_at": now_iso if listed_inactive else None,
                        }
                    ).eq("id", offer_id).execute()
                    result.offers_unchanged += 1

            self.client.table("offer_snapshots").insert(
                json_safe(
                    {
                        "offer_id": offer_id,
                        "source_run_id": source_run_id,
                        "seen_at": now_iso,
                        "content_hash": offer.content_hash,
                        "title": offer.title,
                        "location_text": offer.location_text,
                        "contract_type": offer.contract_type,
                        "offer_type": offer.offer_type,
                        "posted_at": offer.posted_at.isoformat() if offer.posted_at else None,
                        "raw_payload": raw_payload,
                    }
                )
            ).execute()

        missing_rows = [row for row in active_rows if row["source_offer_key"] not in current_keys]
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in missing_rows:
            new_missed_count = int(row.get("consecutive_missed_runs") or 0) + 1
            is_archive = new_missed_count >= archive_missed_threshold
            self.client.table("offers").update(
                {
                    "consecutive_missed_runs": new_missed_count,
                    "is_active": not is_archive,
                    "archived_at": now_iso if is_archive else None,
                    "last_source_run_id": source_run_id,
                }
            ).eq("id", row["id"]).execute()
            if is_archive:
                result.offers_archived += 1

        return result