from __future__ import annotations

import argparse

from app.main_collect_daily import run_collection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True)
    args = parser.parse_args()
    return run_collection(selected_sources=args.source, skip_paris_guard=True)


if __name__ == "__main__":
    raise SystemExit(main())
