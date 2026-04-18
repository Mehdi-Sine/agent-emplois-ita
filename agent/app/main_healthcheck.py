from __future__ import annotations

import argparse
import json

from app.config import Settings, load_sources_config
from app.connectors.registry import build_connector, CONNECTOR_REGISTRY
from app.http import build_http_client
from app.models import SourceConfig


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append")
    args = parser.parse_args()

    settings = Settings.from_env()
    source_rows = [SourceConfig(**row) for row in load_sources_config()]
    if args.source:
        selected = set(args.source)
        source_rows = [row for row in source_rows if row.slug in selected]
    else:
        source_rows = [row for row in source_rows if row.enabled and row.slug in CONNECTOR_REGISTRY]

    results = []
    for source in source_rows:
        connector = build_connector(source)
        with build_http_client(settings.user_agent, source.timeout_seconds) as client:
            try:
                payload = connector.healthcheck(client)
            except Exception as exc:
                payload = {
                    "source_slug": source.slug,
                    "status": "FAILED",
                    "error": str(exc),
                }
        results.append(payload)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
