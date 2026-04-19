from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import (
    absolute_url,
    content_hash,
    description_from_selectors,
    html_tree,
    normalize_spaces,
    stable_offer_key,
)
from app.models import NormalizedOffer


class IfipConnector(BaseConnector):
    DETAIL_URL_RE = re.compile(
        r"^https://careers\.flatchr\.io/fr/company/ifip/vacancy/[^/?#]+/?$",
        re.IGNORECASE,
    )
    PUBLISHED_RE = re.compile(r"Publié le\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)

    def __init__(self, source) -> None:
        super().__init__(source)
        self._listing_index: dict[str, dict[str, Any]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        offer_urls: list[str] = []
        seen: set[str] = set()
        listing_index: dict[str, dict[str, Any]] = {}

        for card in tree.css("div.card.card-actualite"):
            link = card.css_first("a.content[href]")
            if not link:
                continue

            href = link.attributes.get("href")
            url = absolute_url(str(response.url), href)
            if not url or not self.DETAIL_URL_RE.match(url):
                continue
            if url in seen:
                continue

            title_node = card.css_first("strong.title")
            title = (
                normalize_spaces(title_node.text(separator=" ", strip=True))
                if title_node
                else None
            )
            if not title:
                continue
            if "candidature spontanée" in title.lower():
                continue

            contract_node = card.css_first("span.contract-type")
            contract_type = (
                normalize_spaces(contract_node.text(separator=" ", strip=True))
                if contract_node
                else None
            ) or normalize_spaces(card.attributes.get("data-type"))

            posted_node = card.css_first("span.date")
            posted_raw = (
                normalize_spaces(posted_node.text(separator=" ", strip=True))
                if posted_node
                else None
            )
            posted_at = self._parse_published_date(posted_raw)

            # IMPORTANT : la localisation fiable est ici, sur la page liste
            location_node = card.css_first("div.localisation")
            location_text = (
                normalize_spaces(location_node.text(separator=" ", strip=True))
                if location_node
                else None
            )
            location_text = self._clean_location_text(location_text)

            education_node = card.css_first("span.education-level")
            education_level = (
                normalize_spaces(education_node.text(separator=" ", strip=True))
                if education_node
                else None
            )

            listing_index[url] = {
                "source_url": url,
                "application_url": url,
                "title": title,
                "contract_type": contract_type,
                "posted_at": posted_at,
                "posted_raw": posted_raw,
                "location_text": location_text,
                "education_level": education_level,
            }

            seen.add(url)
            offer_urls.append(url)

        self._listing_index = listing_index
        return offer_urls

    def parse_offer(self, client: Client, url: str) -> dict[str, Any] | None:
        seed = dict(self._listing_index.get(url, {}))
        if not seed:
            return None

        title = seed.get("title")
        contract_type = seed.get("contract_type")
        posted_at = seed.get("posted_at")
        location_text = seed.get("location_text")
        education_level = seed.get("education_level")
        description_text = None
        remote_mode = None
        detail_text = ""

        try:
            response = client.get(url)
            response.raise_for_status()
            tree = html_tree(response.text)

            h1 = tree.css_first("h1")
            if h1:
                title = normalize_spaces(h1.text(separator=" ", strip=True)) or title

            description_text = self._extract_detail_description(tree)

            body = tree.body
            if body:
                detail_text = body.text(separator="\n", strip=True)
            else:
                detail_text = tree.text(separator="\n", strip=True)

            detail_text = normalize_spaces(detail_text) or ""

            if not contract_type:
                contract_type = self._infer_contract_type(title, detail_text)

            if not posted_at:
                posted_at = self._extract_detail_date(detail_text)

            remote_mode = self._infer_remote_mode(detail_text)

        except Exception:
            pass

        if not title:
            return None

        location_text = self._clean_location_text(location_text)
        city = location_text
        offer_type = self._infer_offer_type(title, contract_type)

        return {
            "source_url": url,
            "application_url": seed.get("application_url") or url,
            "title": title,
            "description_text": description_text,
            "location_text": location_text,
            "city": city,
            "region": None,
            "country": "France",
            "contract_type": contract_type,
            "offer_type": offer_type,
            "remote_mode": remote_mode,
            "posted_at": posted_at,
            "education_level": education_level,
            "raw_posted_at": seed.get("posted_raw"),
        }

    def normalize_offer(self, raw_item: dict[str, Any]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre IFIP"
        location = raw_item.get("location_text")
        source_url = raw_item["source_url"]
        posted_at = raw_item.get("posted_at")

        return NormalizedOffer(
            source_slug=self.source.slug,
            source_offer_key=stable_offer_key(source_url, None, None),
            source_url=source_url,
            application_url=raw_item.get("application_url") or source_url,
            title=title,
            organization=self.source.name,
            location_text=location,
            city=raw_item.get("city"),
            region=raw_item.get("region"),
            country=raw_item.get("country"),
            contract_type=raw_item.get("contract_type"),
            offer_type=raw_item.get("offer_type"),
            remote_mode=raw_item.get("remote_mode"),
            posted_at=posted_at,
            description_text=raw_item.get("description_text"),
            content_hash=content_hash(
                [
                    source_url,
                    title,
                    location,
                    raw_item.get("contract_type"),
                    raw_item.get("offer_type"),
                    raw_item.get("remote_mode"),
                    posted_at.isoformat() if posted_at else None,
                    raw_item.get("description_text"),
                ]
            ),
            raw_payload=raw_item,
        )

    def _parse_published_date(self, text: str | None):
        if not text:
            return None
        match = self.PUBLISHED_RE.search(text)
        if not match:
            return None
        return self._parse_fr_slash_date(match.group(1))

    def _extract_detail_date(self, text: str | None):
        if not text:
            return None
        match = self.PUBLISHED_RE.search(text)
        if match:
            return self._parse_fr_slash_date(match.group(1))

        range_match = re.search(
            r"\b(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\b", text
        )
        if range_match:
            return self._parse_fr_slash_date(range_match.group(1))

        one_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", text)
        if one_date:
            return self._parse_fr_slash_date(one_date.group(1))

        return None

    def _parse_fr_slash_date(self, value: str | None):
        if not value:
            return None
        value = value.strip()
        try:
            return datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            return None

    def _clean_location_text(self, value: str | None) -> str | None:
        if not value:
            return None
        value = normalize_spaces(value)
        if not value:
            return None
        value = value.replace(" ,", ",").strip(" -–|:")
        return value or None

    def _extract_detail_description(self, tree) -> str | None:
        raw = description_from_selectors(tree, ["main", "body"])
        if not raw:
            return None

        lines: list[str] = []
        started = False
        stop_markers = (
            "annonces gérées par",
            "politique de confidentialité",
            "obtenir ses données",
        )

        for raw_line in raw.split("\n"):
            line = normalize_spaces(raw_line)
            if not line:
                continue

            lower = line.lower()

            if line in {"Description", "Missions", "Profil", "Avantages"}:
                started = True

            if any(marker in lower for marker in stop_markers):
                break

            if not started:
                continue

            if line in {"Partager sur :", "Postuler", "Retour aux offres"}:
                continue

            lines.append(line)

        if not lines:
            return None

        return "\n".join(lines)

    def _infer_contract_type(self, title: str | None, detail_text: str | None) -> str | None:
        blob = " ".join([title or "", detail_text or ""]).lower()

        if "alternance" in blob:
            return "alternance"
        if "apprentissage" in blob:
            return "apprentissage"
        if "stage" in blob:
            return "stage"
        if "cdi" in blob:
            return "cdi"
        if "cdd" in blob:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str | None, contract_type: str | None) -> str | None:
        blob = " ".join([title or "", contract_type or ""]).lower()

        if "stage" in blob:
            return "stage"
        if "alternance" in blob or "apprentissage" in blob:
            return "alternance"
        return "emploi"

    def _infer_remote_mode(self, detail_text: str | None) -> str | None:
        if not detail_text:
            return None

        blob = detail_text.lower()

        if "présentiel" in blob and "télétravail non prévu" in blob:
            return "présentiel"
        if "hybride" in blob:
            return "hybride"
        if "télétravail" in blob:
            return "télétravail"
        return None