from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


RunStatus = Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILED"]
SourceRunStatus = Literal["SUCCESS", "FAILED"]


class SourceConfig(BaseModel):
    slug: str
    name: str
    site_url: HttpUrl
    jobs_url: HttpUrl
    enabled: bool = True
    mode: str = "http"
    timeout_seconds: int = 20


class NormalizedOffer(BaseModel):
    source_slug: str
    source_offer_key: str = Field(min_length=1)
    source_url: str
    application_url: str | None = None
    title: str
    organization: str
    location_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = "France"
    contract_type: str | None = None
    offer_type: str | None = None
    remote_mode: str | None = None
    posted_at: datetime | None = None
    description_text: str | None = None
    content_hash: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ConnectorResult(BaseModel):
    source_slug: str
    status: SourceRunStatus
    started_at: datetime
    ended_at: datetime
    offers: list[NormalizedOffer] = Field(default_factory=list)
    offer_urls: list[str] = Field(default_factory=list)
    discover_count: int = 0
    parsed_count: int = 0
    http_errors: int = 0
    parse_errors: int = 0
    error_message: str | None = None
    raw_items: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        delta = self.ended_at - self.started_at
        return int(delta.total_seconds() * 1000)


class PersistResult(BaseModel):
    source_id: str
    source_run_id: str
    offers_found: int
    offers_new: int = 0
    offers_updated: int = 0
    offers_unchanged: int = 0
    offers_archived: int = 0
