from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import absolute_url, content_hash, html_tree, normalize_spaces, stable_offer_key
from app.models import NormalizedOffer


class CnpfConnector(BaseConnector):
    LINK_LABEL = "La fiche de poste détaillée à télécharger"
    TITLE_RE = re.compile(r"^Réf\.\s*(?P<ref>\d{4}-\d+)\s*:\s*(?P<title>.+)$")
    DEADLINE_RE = re.compile(
        r"Candidature avant le (?P<day>\d{1,2}) (?P<month>[A-Za-zéûôàèù\.]+) (?P<year>\d{4})",
        re.IGNORECASE,
    )
    LOCATION_RE = re.compile(r"basé(?:e)? à (?P<place>.+?)(?:\.|$)", re.IGNORECASE)
    CONTRACT_RE = re.compile(r"Poste(?: en)? (?P<contract>CDD|CDI)", re.IGNORECASE)
    MONTHS_FR = {
        "janvier": 1, "janv": 1, "janv.": 1,
        "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "févr.": 2, "fevr.": 2,
        "mars": 3,
        "avril": 4, "avr": 4, "avr.": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7, "juil": 7, "juil.": 7,
        "août": 8, "aout": 8,
        "septembre": 9, "sept": 9, "sept.": 9,
        "octobre": 10, "oct": 10, "oct.": 10,
        "novembre": 11, "nov": 11, "nov.": 11,
        "décembre": 12, "decembre": 12, "déc": 12, "dec": 12, "déc.": 12, "dec.": 12,
    }

    def __init__(self, source) -> None:
        super().__init__(source)
        self._items_by_url: dict[str, dict[str, object]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)

        download_links: list[str] = []
        for node in tree.css("a[href]"):
            text = normalize_spaces(node.text(separator=" ", strip=True))
            if text != self.LINK_LABEL:
                continue
            href = absolute_url(str(response.url), node.attributes.get("href"))
            if href:
                parsed = urlsplit(href)
                download_links.append(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")))

        items = self._extract_items(lines, download_links)
        self._items_by_url = {item["source_url"]: item for item in items}
        return [item["source_url"] for item in items]

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        if not self._items_by_url:
            self.discover_offer_urls(client)
        return self._items_by_url.get(url)

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre CNPF"
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
            city=str(raw_item.get("city")) if raw_item.get("city") else None,
            region=None,
            country="France",
            contract_type=str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
            offer_type=str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
            remote_mode=None,
            posted_at=raw_item.get("posted_at"),
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash([source_url, str(title), str(location), str(raw_item.get("contract_type")), str(raw_item.get("raw_deadline")), str(raw_item.get("is_filled"))]),
            raw_payload=raw_item,
        )

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        return [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    def _extract_items(self, lines: list[str], download_links: list[str]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        start = None
        for idx, line in enumerate(lines):
            if line.lower() == "fiches de poste":
                start = idx + 1
                break
        if start is None:
            return items

        current_title = None
        current_ref = None
        current_summary_parts: list[str] = []
        link_index = 0

        for line in lines[start:]:
            if line == self.LINK_LABEL:
                if current_title and link_index < len(download_links):
                    summary = " ".join(current_summary_parts).strip() or None
                    location_text = self._extract_location(summary)
                    city = self._extract_city(location_text)
                    contract_type = self._extract_contract_type(summary)
                    deadline = self._extract_deadline(summary)
                    is_filled = bool(deadline and deadline.date() < datetime.utcnow().date())
                    items.append(
                        {
                            "source_url": download_links[link_index],
                            "application_url": download_links[link_index],
                            "title": current_title,
                            "description_text": summary,
                            "location_text": location_text,
                            "city": city,
                            "region": None,
                            "country": "France",
                            "contract_type": contract_type,
                            "offer_type": "emploi",
                            "remote_mode": None,
                            "posted_at": None,
                            "raw_posted_at": None,
                            "reference": current_ref,
                            "raw_deadline": deadline.isoformat() if deadline else None,
                            "is_filled": is_filled,
                            "listing_status": "filled" if is_filled else "open",
                        }
                    )
                    link_index += 1
                current_title = None
                current_ref = None
                current_summary_parts = []
                continue

            match = self.TITLE_RE.match(line)
            if match:
                current_ref = match.group("ref")
                current_title = match.group("title").strip()
                current_summary_parts = []
                continue

            if current_title:
                lower = line.lower()
                if lower in {"suivez-nous", "suivez nous"}:
                    break
                current_summary_parts.append(line)

        return items

    def _extract_location(self, summary: str | None) -> str | None:
        if not summary:
            return None
        match = self.LOCATION_RE.search(summary)
        if not match:
            return None
        return normalize_spaces(match.group("place")) or None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None
        city = location_text.split(" ou ")[0].strip()
        city = city.split("(")[0].strip()
        return normalize_spaces(city) or None

    def _extract_contract_type(self, summary: str | None) -> str | None:
        if not summary:
            return None
        match = self.CONTRACT_RE.search(summary)
        if not match:
            return None
        return match.group("contract").lower()

    def _extract_deadline(self, summary: str | None) -> datetime | None:
        if not summary:
            return None
        match = self.DEADLINE_RE.search(summary)
        if not match:
            return None
        month = self.MONTHS_FR.get(match.group("month").lower())
        if not month:
            return None
        try:
            return datetime(int(match.group("year")), month, int(match.group("day")))
        except ValueError:
            return None
