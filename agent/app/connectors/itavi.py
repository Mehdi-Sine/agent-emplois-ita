from __future__ import annotations

from typing import Any

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import (
    absolute_url,
    classify_contract_type,
    classify_offer_type,
    content_hash,
    description_from_selectors,
    html_tree,
    node_text,
    parse_date_guess,
    stable_offer_key,
)
from app.models import NormalizedOffer


class ItaviConnector(BaseConnector):
    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)
        urls = []
        seen = set()
        for selector in [
            "a[href*='/offres/emplois']",
            "a[href*='/offres/stages']",
            "main a[href]",
        ]:
            for node in tree.css(selector):
                href = node.attributes.get("href")
                url = absolute_url(str(response.url), href)
                if not url or url in seen:
                    continue
                seen.add(url)
                urls.append(url)
        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, Any] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)
        title = node_text(tree, ["h1", ".page-title", ".entry-title"])
        description = description_from_selectors(
            tree, [".content", ".entry-content", "main article", ".post-content"]
        )
        meta_blob = " ".join(filter(None, [title, description]))
        return {
            "source_url": url,
            "title": title,
            "description_text": description,
            "location_text": node_text(tree, [".location", ".lieu", ".entry-meta"]),
            "contract_type": classify_contract_type(meta_blob),
            "offer_type": classify_offer_type(meta_blob),
            "posted_at": parse_date_guess(node_text(tree, ["time", ".date", ".entry-date"])),
        }

    def normalize_offer(self, raw_item: dict[str, Any]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ITAVI"
        location = raw_item.get("location_text")
        source_url = raw_item["source_url"]
        return NormalizedOffer(
            source_slug=self.source.slug,
            source_offer_key=stable_offer_key(source_url, title, location),
            source_url=source_url,
            application_url=source_url,
            title=title,
            organization=self.source.name,
            location_text=location,
            contract_type=raw_item.get("contract_type"),
            offer_type=raw_item.get("offer_type"),
            posted_at=raw_item.get("posted_at"),
            description_text=raw_item.get("description_text"),
            content_hash=content_hash(
                [title, location, raw_item.get("contract_type"), raw_item.get("description_text")]
            ),
            raw_payload=raw_item,
        )
