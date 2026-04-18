from __future__ import annotations

from collections import Counter
from typing import Any

from app.models import ConnectorResult, PersistResult, RunStatus


def build_pipeline_status(source_results: list[ConnectorResult]) -> RunStatus:
    if not source_results:
        return "FAILED"
    statuses = [result.status for result in source_results]
    if all(status == "SUCCESS" for status in statuses):
        return "SUCCESS"
    if any(status == "SUCCESS" for status in statuses):
        return "PARTIAL_SUCCESS"
    return "FAILED"


def summarize_run(
    source_results: list[ConnectorResult],
    persist_results: list[PersistResult],
) -> dict[str, Any]:
    counter = Counter(result.status for result in source_results)
    return {
        "sources": len(source_results),
        "success": counter.get("SUCCESS", 0),
        "failed": counter.get("FAILED", 0),
        "offers_found": sum(len(result.offers) for result in source_results),
        "offers_new": sum(result.offers_new for result in persist_results),
        "offers_updated": sum(result.offers_updated for result in persist_results),
        "offers_archived": sum(result.offers_archived for result in persist_results),
    }
