from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from httpx import Client

from app.models import ConnectorResult, NormalizedOffer, SourceConfig


class BaseConnector(ABC):
    def __init__(self, source: SourceConfig) -> None:
        self.source = source

    @abstractmethod
    def discover_offer_urls(self, client: Client) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def parse_offer(self, client: Client, url: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def normalize_offer(self, raw_item: dict[str, Any]) -> NormalizedOffer:
        raise NotImplementedError

    def fetch(self, client: Client) -> ConnectorResult:
        started_at = datetime.now(timezone.utc)
        raw_items: list[dict[str, Any]] = []
        offers: list[NormalizedOffer] = []
        offer_urls: list[str] = []
        http_errors = 0
        parse_errors = 0
        status = "SUCCESS"
        error_message: str | None = None

        try:
            offer_urls = self.discover_offer_urls(client)
            for url in offer_urls:
                try:
                    raw_item = self.parse_offer(client, url)
                    if not raw_item:
                        continue
                    raw_items.append(raw_item)
                    offer = self.normalize_offer(raw_item)
                    offers.append(offer)
                except Exception as exc:
                    parse_errors += 1
                    error_message = str(exc)
        except Exception as exc:
            status = "FAILED"
            http_errors += 1
            error_message = str(exc)

        ended_at = datetime.now(timezone.utc)
        return ConnectorResult(
            source_slug=self.source.slug,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            offers=offers,
            offer_urls=offer_urls,
            discover_count=len(offer_urls),
            parsed_count=len(offers),
            http_errors=http_errors,
            parse_errors=parse_errors,
            error_message=error_message,
            raw_items=raw_items,
        )

    def healthcheck(self, client: Client) -> dict[str, Any]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        return {
            "source_slug": self.source.slug,
            "status": "SUCCESS",
            "status_code": response.status_code,
            "final_url": str(response.url),
        }
