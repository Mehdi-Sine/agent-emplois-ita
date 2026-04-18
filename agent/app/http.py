from __future__ import annotations

import httpx


def build_http_client(user_agent: str, timeout_seconds: int) -> httpx.Client:
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    return httpx.Client(
        headers=headers,
        timeout=timeout_seconds,
        follow_redirects=True,
    )
