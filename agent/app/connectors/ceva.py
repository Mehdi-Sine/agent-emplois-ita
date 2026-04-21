from __future__ import annotations

import re
from datetime import datetime

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import content_hash, html_tree, normalize_spaces, stable_offer_key
from app.models import NormalizedOffer


class CevaConnector(BaseConnector):
    TITLE_RE = re.compile(r"OFFRE D[’']EMPLOI\s*:?\s*(?P<title>[A-Z0-9() \-]{8,})", re.IGNORECASE)

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        text = normalize_spaces(response.text.replace("\n", " "))
        if self.TITLE_RE.search(text) or "OFFRE D’EMPLOI" in response.text or "OFFRE D'EMPLOI" in response.text:
            return [str(response.url)]
        return []

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)

        title = self._extract_title(lines)
        if not title:
            return None

        contract_type = self._infer_contract_type(title)
        location_text = "Pleubian (22610)"
        city = "Pleubian"
        description_text = self._extract_description(lines)
        offer_type = self._infer_offer_type(title, contract_type, description_text)

        return {
            "source_url": url,
            "application_url": url,
            "title": title,
            "description_text": description_text,
            "location_text": location_text,
            "city": city,
            "region": "Bretagne",
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
        title = raw_item.get("title") or "Offre CEVA"
        location = raw_item.get("location_text")
        source_url = str(raw_item["source_url"])

        return NormalizedOffer(
            source_slug=self.source.slug,
            source_offer_key=stable_offer_key(source_url, None, None),
            source_url=source_url,
            application_url=str(raw_item.get("application_url") or source_url),
            title=str(title),
            organization=self.source.name,
            location_text=str(location) if location else None,
            city="Pleubian",
            region="Bretagne",
            country="France",
            contract_type=str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
            offer_type=str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
            remote_mode=None,
            posted_at=None,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash([source_url, str(title), str(location), str(raw_item.get("contract_type")), str(raw_item.get("offer_type"))]),
            raw_payload=raw_item,
        )

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        return [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    def _extract_title(self, lines: list[str]) -> str | None:
        for idx, line in enumerate(lines):
            if line in {"OFFRE D’EMPLOI :", "OFFRE D'EMPLOI :", "OFFRE D’EMPLOI", "OFFRE D'EMPLOI"} and idx + 1 < len(lines):
                return lines[idx + 1]
        for line in lines:
            if "TECHNICIEN" in line.upper() or "INGENIEUR" in line.upper() or "CHARGÉ" in line.upper() or "CHARGE" in line.upper():
                return line
        return None

    def _extract_description(self, lines: list[str]) -> str | None:
        kept = []
        started = False
        for line in lines:
            if line.upper().startswith("OFFRE D"):
                started = True
                continue
            if not started:
                continue
            if line.startswith("Centre d'Étude") or line.startswith("Centre d'Etude"):
                break
            kept.append(line)
        text = "\n\n".join(kept).strip()
        return text or None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text).lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str | None, contract_type: str | None, description_text: str | None) -> str | None:
        contract_low = (contract_type or "").lower()
        if contract_low in {"cdi", "cdd"}:
            return "emploi"
        if contract_low == "alternance":
            return "alternance"
        if contract_low == "stage":
            return "stage"
        low = " ".join(filter(None, [title, description_text])).lower()
        if "alternance" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        return "emploi"
