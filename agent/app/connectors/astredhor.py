from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import (
    absolute_url,
    content_hash,
    html_tree,
    normalize_spaces,
    stable_offer_key,
)
from app.models import NormalizedOffer


class AstredhorConnector(BaseConnector):
    OFFER_URL_RE = re.compile(
        r"^https://institut-du-vegetal\.fr/nous-rejoindre/(?!candidature-spontanee/?$|adherer-a-astredhor/?$|$)[^/?#]+/?$",
        re.IGNORECASE,
    )

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        urls: list[str] = []
        seen: set[str] = set()

        for node in tree.css("a[href*='/nous-rejoindre/']"):
            href = node.attributes.get("href")
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)

        title = self._node_text(tree, ["h1", "h2"])
        if not title or title.lower() == "candidature spontanée":
            return None

        lines = self._extract_lines(tree)
        description_text = self._extract_description(lines, title)
        contract_type = self._infer_contract_type(" ".join(filter(None, [title, description_text])))
        offer_type = self._infer_offer_type(title, contract_type, description_text)

        return {
            "source_url": url,
            "application_url": url,
            "title": title,
            "description_text": description_text,
            "location_text": None,
            "city": None,
            "region": None,
            "country": "France",
            "contract_type": contract_type,
            "offer_type": offer_type,
            "remote_mode": None,
            "posted_at": None,
            "raw_posted_at": None,
            "is_filled": False,
            "listing_status": "open",
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ASTREDHOR"
        source_url = str(raw_item["source_url"])
        posted_at = raw_item.get("posted_at")

        return NormalizedOffer(
            source_slug=self.source.slug,
            source_offer_key=stable_offer_key(source_url, None, None),
            source_url=source_url,
            application_url=str(raw_item.get("application_url") or source_url),
            title=str(title),
            organization=self.source.name,
            location_text=None,
            city=None,
            region=None,
            country="France",
            contract_type=str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
            offer_type=str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
            remote_mode=None,
            posted_at=posted_at,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash(
                [
                    source_url,
                    str(title),
                    str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
                    str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
                    str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
                ]
            ),
            raw_payload=raw_item,
        )

    def _canonicalize_offer_url(self, url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlsplit(url)
        clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
        return clean if self.OFFER_URL_RE.match(clean) else None

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        return [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    def _extract_description(self, lines: list[str], title: str) -> str | None:
        start = None
        for idx, line in enumerate(lines):
            if line == title:
                start = idx + 1
                break
        if start is None:
            return None
        kept: list[str] = []
        for line in lines[start:]:
            lower = line.lower()
            if lower in {"contact", "mon compte", "adhérer à astredhor", "adhérer a astredhor"}:
                break
            kept.append(line)
        return "\n\n".join(kept).strip() or None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low or "stagiaire" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str | None, contract_type: str | None, description_text: str | None) -> str | None:
        contract_low = (contract_type or "").lower()
        title_low = (title or "").lower()
        desc_low = (description_text or "").lower()
        if contract_low in {"cdi", "cdd"}:
            return "emploi"
        if contract_low == "alternance":
            return "alternance"
        if contract_low == "stage":
            return "stage"
        if "alternance" in title_low or "apprentissage" in title_low:
            return "alternance"
        if "stage" in title_low:
            return "stage"
        if "alternance" in desc_low:
            return "alternance"
        if "stage" in desc_low:
            return "stage"
        return "emploi"

    def _node_text(self, tree, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if node:
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text:
                    return text
        return None
