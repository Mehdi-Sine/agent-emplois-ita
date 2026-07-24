from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
EVENTS_LOG_PATH = ROOT_DIR / "data" / "runs" / "workflow_events.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _env_payload() -> dict[str, Any]:
    return {
        "github_run_id": _clean(os.getenv("GITHUB_RUN_ID")),
        "github_run_attempt": _clean(os.getenv("GITHUB_RUN_ATTEMPT")),
        "github_workflow": _clean(os.getenv("GITHUB_WORKFLOW")),
        "github_event_name": _clean(os.getenv("GITHUB_EVENT_NAME")),
        "github_ref": _clean(os.getenv("GITHUB_REF")),
        "github_sha": _clean(os.getenv("GITHUB_SHA")),
        "github_actor": _clean(os.getenv("GITHUB_ACTOR")),
        "pipeline_run_id": _clean(os.getenv("PIPELINE_RUN_ID")),
    }


def build_event_payload(event_type: str, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "event_type": event_type,
        "status": status,
        "occurred_at": _utc_now(),
        "details_json": details or {},
    }
    payload.update(_env_payload())
    return payload


def append_jsonl(payload: dict[str, Any], path: Path = EVENTS_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def post_to_supabase(payload: dict[str, Any]) -> tuple[bool, str | None]:
    supabase_url = _clean(os.getenv("SUPABASE_URL"))
    service_key = _clean(os.getenv("SUPABASE_SERVICE_KEY"))
    if not supabase_url or not service_key:
        return False, "SUPABASE_URL/SUPABASE_SERVICE_KEY absents"

    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/workflow_run_events"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return 200 <= response.status < 300, None
    except HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = ""
        return False, f"HTTP {exc.code}: {error_body[:500]}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:
        return False, str(exc)


def record_event(event_type: str, status: str, details: dict[str, Any] | None = None) -> int:
    payload = build_event_payload(event_type, status, details)
    append_jsonl(payload)
    ok, error = post_to_supabase(payload)
    if ok:
        print(f"workflow_event_log: événement {event_type}/{status} écrit dans Supabase")
    else:
        print(f"workflow_event_log: événement {event_type}/{status} écrit en JSONL seulement ({error})", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--details-json", default="{}")
    args = parser.parse_args()

    try:
        details = json.loads(args.details_json)
    except json.JSONDecodeError as exc:
        details = {"details_parse_error": str(exc), "raw_details": args.details_json}

    return record_event(args.event_type, args.status, details)


if __name__ == "__main__":
    raise SystemExit(main())
