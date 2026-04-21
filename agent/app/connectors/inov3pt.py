from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import content_hash, html_tree, normalize_spaces, stable_offer_key
from app.models import NormalizedOffer


class Inov3ptConnector(BaseConnector):
    def __init__(self, source) -> None:
        super().__init__(source)
        self._items_by_url: dict[str, dict[str, object]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)

        items = self._extract_items(lines)
        self._items_by_url = {}

        urls: list[str] = []
        for item in items:
            title = item.get("title")
            if not title:
                continue
            url = f"{self.source.jobs_url}#{quote(str(title).lower().replace(' ', '-'))}"
            item["source_url"] = url
            item["application_url"] = url
            self._items_by_url[url] = item
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        if not self._items_by_url:
            self.discover_offer_urls(client)
        item = self._items_by_url.get(url)
        if not item:
            return None
        return item

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre inov3PT"
        source_url = str(raw_item["source_url"])

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
            posted_at=None,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash([source_url, str(title), str(raw_item.get("contract_type")), str(raw_item.get("offer_type")), str(raw_item.get("is_filled"))]),
            raw_payload=raw_item,
        )

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        lines: list[str] = []
        for raw_line in text.splitlines():
            line = normalize_spaces(raw_line)
            if not line:
                continue
            lines.append(line)
        return lines

    def _is_title_line(self, line: str) -> bool:
        low = line.lower()
        return low.startswith("poste ") or low == "offre de stage" or low == "stages"

    def _extract_items(self, lines: list[str]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        current: dict[str, object] | None = None

        for line in lines:
            low = line.lower()

            if low.startswith("top of page") or low.startswith("institut technique agricole qualifié") or low.startswith("© "):
                continue

            if self._is_title_line(line):
                if current:
                    items.append(current)
                current = {"title": line, "extras": []}
                continue

            if not current:
                continue

            if self._is_title_line(line):
                items.append(current)
                current = {"title": line, "extras": []}
                continue

            # continuation title lines
            if (
                current["title"] != "Offre de stage"
                and current["title"] != "Stages"
                and re.match(r"^[a-zà-ÿ]", line)
                and "logo offre pourvue" not in low
                and "recrutement terminé" not in low
                and "recrutement termine" not in low
                and not re.search(r"\b20\d{2}\b", line)
            ):
                current["title"] = f"{current['title']} {line}".strip()
                continue

            current["extras"].append(line)

        if current:
            items.append(current)

        normalized: list[dict[str, object]] = []
        for item in items:
            title = str(item.get("title") or "").strip()
            extras = [normalize_spaces(x) for x in item.get("extras", []) if normalize_spaces(x)]
            if not title:
                continue

            blob = " ".join(extras).lower()
            description_text = "\n\n".join(extras).strip() or None
            contract_type = self._infer_contract_type(title, blob)
            offer_type = self._infer_offer_type(title, contract_type)
            is_filled = (
                "logo offre pourvue" in blob
                or "recrutement terminé" in blob
                or "recrutement termine" in blob
                or "offre pourvue" in blob
            )

            normalized.append(
                {
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
                    "is_filled": is_filled,
                    "listing_status": "filled" if is_filled else "open",
                }
            )

        return normalized

    def _infer_contract_type(self, title: str, blob: str) -> str | None:
        low = f"{title} {blob}".lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low or "stag" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str, contract_type: str | None) -> str | None:
        if contract_type in {"cdi", "cdd"}:
            return "emploi"
        if contract_type == "alternance":
            return "alternance"
        if contract_type == "stage":
            return "stage"
        return "emploi"
