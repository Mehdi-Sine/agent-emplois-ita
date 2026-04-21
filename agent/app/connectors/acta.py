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


class ActaConnector(BaseConnector):
    JOB_URL_RE = re.compile(
        r"^https://www\.welcometothejungle\.com/fr/companies/acta/jobs/[^/?#]+/?$",
        re.IGNORECASE,
    )
    ISO_DATE_RE = re.compile(r'"date(?:Posted|Published)"\s*:\s*"(?P<value>[^"]+)"')
    DEADLINE_RE = re.compile(
        r"avant le (?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})",
        re.IGNORECASE,
    )

    NOISE_LINES = {
        "postuler",
        "sauvegarder",
        "partager",
        "copier le lien",
        "cette offre vous tente ?",
        "retour",
        "questions et réponses sur l'offre",
        "le poste",
    }

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        urls: list[str] = []
        seen: set[str] = set()

        for node in tree.css("a[href*='/fr/companies/acta/jobs/']"):
            href = node.attributes.get("href")
            text = normalize_spaces(node.text(separator=" ", strip=True) if node else "")
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            if not url:
                continue
            blob = f"{url} {text or ''}".lower()
            if "spontan" in blob:
                continue
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)

        title = self._node_text(tree, ["h1", "h2"])
        if not title:
            return None

        lines = self._extract_lines(tree)
        header_lines = self._extract_header_lines(lines, title)

        contract_type = self._extract_contract_type(header_lines) or self._infer_contract_type(title)
        location_text = self._extract_location(header_lines)
        city = self._extract_city(location_text)
        remote_mode = self._extract_remote_mode(header_lines)
        posted_at = self._extract_posted_at(response.text)
        description_text = self._extract_description(lines, title)
        application_url = self._extract_application_url(tree, str(response.url)) or url
        deadline = self._extract_deadline(lines)

        is_filled = self._is_filled(lines)
        listing_status = "filled" if is_filled else "open"
        offer_type = self._infer_offer_type(title, contract_type, description_text)

        return {
            "source_url": url,
            "application_url": application_url,
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
            "raw_posted_at": posted_at.isoformat() if posted_at else None,
            "raw_deadline": deadline.isoformat() if deadline else None,
            "is_filled": is_filled,
            "listing_status": listing_status,
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ACTA"
        location = raw_item.get("location_text")
        source_url = str(raw_item["source_url"])
        posted_at = raw_item.get("posted_at")

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
            remote_mode=str(raw_item.get("remote_mode")) if raw_item.get("remote_mode") else None,
            posted_at=posted_at,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash(
                [
                    source_url,
                    str(title),
                    str(location) if location else None,
                    str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
                    str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
                    posted_at.isoformat() if posted_at else None,
                    str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
                    str(raw_item.get("is_filled")),
                ]
            ),
            raw_payload=raw_item,
        )

    def _canonicalize_offer_url(self, url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlsplit(url)
        clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
        return clean if self.JOB_URL_RE.match(clean) else None

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

    def _extract_header_lines(self, lines: list[str], title: str) -> list[str]:
        title_lower = title.lower()
        start_index = 0
        for idx, line in enumerate(lines):
            if line.lower() == title_lower:
                start_index = idx + 1
                break

        header: list[str] = []
        for line in lines[start_index : start_index + 12]:
            lower = line.lower()
            if lower in self.NOISE_LINES:
                continue
            if lower in {"descriptif du poste", "le poste"}:
                break
            header.append(line)
        return header

    def _extract_contract_type(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            contract = self._infer_contract_type(line)
            if contract:
                return contract
        return None

    def _extract_location(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            lower = line.lower()
            if self._infer_contract_type(line):
                continue
            if "télétravail" in lower or "salaire" in lower or "expérience" in lower or "éducation" in lower or "education" in lower:
                continue
            if lower.startswith("il y a "):
                continue
            return line
        return None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None
        city = normalize_spaces(location_text.split(",")[0].strip())
        return city or None

    def _extract_remote_mode(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            lower = line.lower()
            if "télétravail" in lower or "teletravail" in lower:
                return line
        return None

    def _extract_posted_at(self, html: str) -> datetime | None:
        match = self.ISO_DATE_RE.search(html)
        if not match:
            return None
        raw = match.group("value")
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _extract_description(self, lines: list[str], title: str) -> str | None:
        start_index = None
        for idx, line in enumerate(lines):
            if line.lower() == "descriptif du poste":
                start_index = idx + 1
                break
        if start_index is None:
            return None

        kept: list[str] = []
        for line in lines[start_index:]:
            lower = line.lower()
            if lower in {
                "envie d’en savoir plus ?",
                "envie d'en savoir plus ?",
                "le lieu de travail",
                "l'entreprise",
            }:
                break
            if lower in self.NOISE_LINES:
                continue
            kept.append(line)
        return "\n\n".join(kept).strip() or None

    def _extract_application_url(self, tree, base_url: str) -> str | None:
        for node in tree.css("a[href]"):
            text = normalize_spaces(node.text(separator=" ", strip=True))
            href = node.attributes.get("href")
            if not text or not href:
                continue
            if text.lower() != "postuler":
                continue
            url = absolute_url(base_url, href)
            if url:
                return url
        return None

    def _extract_deadline(self, lines: list[str]) -> datetime | None:
        blob = "\n".join(lines)
        match = self.DEADLINE_RE.search(blob)
        if not match:
            return None
        try:
            return datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            return None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low or "temporaire" in low:
            return "cdd"
        return None

    def _infer_offer_type(
        self,
        title: str | None,
        contract_type: str | None,
        description_text: str | None,
    ) -> str | None:
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
        if "stage" in title_low or "stagiaire" in title_low:
            return "stage"
        if "alternance" in desc_low or "apprentissage" in desc_low:
            return "alternance"
        if "stage" in desc_low:
            return "stage"
        return "emploi"

    def _is_filled(self, lines: list[str]) -> bool:
        blob = "\n".join(lines).lower()
        return (
            "n'est plus disponible" in blob
            or "n’est plus disponible" in blob
            or "vous ne pouvez plus postuler" in blob
            or "offre pourvue" in blob
        )

    def _node_text(self, tree, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if node:
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text:
                    return text
        return None
