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
    WTTJ_RELATIVE_RE = re.compile(r"^(il y a\s+\d+\s+jours|le mois dernier|il y a\s+\d+\s+heures?)$", re.IGNORECASE)
    ADDRESS_CITY_RE = re.compile(r"\b\d{5}\s+([A-Za-zÀ-ÿ'\- ]+)")

    NOISE_LINES = {
        "postuler",
        "sauvegarder",
        "partager",
        "copier le lien",
        "cette offre vous tente ?",
        "retour",
        "questions et réponses sur l'offre",
        "le poste",
        "descriptif du poste",
        "envie d’en savoir plus ?",
        "envie d'en savoir plus ?",
    }

    def __init__(self, source) -> None:
        super().__init__(source)
        self._listing_by_url: dict[str, dict[str, object]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        self._listing_by_url = {}
        urls: list[str] = []
        seen: set[str] = set()

        for card in tree.css("[data-role='jobs:thumb']"):
            link = card.css_first("a[href*='/fr/companies/acta/jobs/']")
            if not link:
                continue

            href = link.attributes.get("href")
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            title = normalize_spaces(link.text(separator=" ", strip=True))
            if not url or not title:
                continue

            blob = f"{url} {title}".lower()
            if "spontan" in blob:
                continue
            if url in seen:
                continue

            meta = self._extract_card_meta(card, title, url)
            self._listing_by_url[url] = meta
            seen.add(url)
            urls.append(url)

        if urls:
            return urls

        # fallback minimal si WTTJ ne rend pas les cartes avec le même markup
        for node in tree.css("a[href*='/fr/companies/acta/jobs/']"):
            href = node.attributes.get("href")
            text = normalize_spaces(node.text(separator=" ", strip=True))
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            if not url:
                continue
            blob = f"{url} {text or ''}".lower()
            if "spontan" in blob:
                continue
            if url in seen:
                continue
            seen.add(url)
            self._listing_by_url[url] = {
                "title": text or None,
                "contract_type": None,
                "location_text": self._fallback_location_from_url(url),
                "city": self._fallback_location_from_url(url),
                "remote_mode": None,
            }
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        if not self._listing_by_url:
            self.discover_offer_urls(client)
        listing = self._listing_by_url.get(url, {})

        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)

        title = self._node_text(tree, ["h1", "h2"]) or self._as_clean_str(listing.get("title"))
        if not title:
            return None

        lines = self._extract_lines(tree)
        header_lines = self._extract_header_lines(lines, title)

        contract_type = (
            self._as_clean_str(listing.get("contract_type"))
            or self._extract_contract_type(header_lines)
            or self._infer_contract_type(title)
        )

        location_text = (
            self._as_clean_str(listing.get("location_text"))
            or self._extract_detail_location(lines)
            or self._fallback_location_from_url(url)
        )
        city = self._extract_city(location_text)

        remote_mode = self._as_clean_str(listing.get("remote_mode")) or self._extract_remote_mode(header_lines)
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
            "listing_meta": listing,
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

    def _extract_card_meta(self, card, title: str, url: str) -> dict[str, object]:
        text = card.text(separator="\n", strip=True)
        lines: list[str] = []
        seen: set[str] = set()
        for raw_line in text.splitlines():
            line = normalize_spaces(raw_line)
            if not line or line == title:
                continue
            low = line.lower()
            if low in self.NOISE_LINES:
                continue
            if low in seen:
                continue
            seen.add(low)
            lines.append(line)

        contract_type = None
        location_text = None
        remote_mode = None

        for idx, line in enumerate(lines):
            contract = self._infer_contract_type(line)
            if contract and not contract_type:
                contract_type = contract
                for candidate in lines[idx + 1 : idx + 5]:
                    low = candidate.lower()
                    if self._is_location_candidate(candidate):
                        location_text = candidate
                        break
                    if "télétravail" in low or "teletravail" in low:
                        break

            low = line.lower()
            if ("télétravail" in low or "teletravail" in low) and remote_mode is None:
                remote_mode = line
            if location_text is None and self._is_location_candidate(line):
                location_text = line

        if location_text is None:
            location_text = self._fallback_location_from_url(url)

        return {
            "title": title,
            "contract_type": contract_type,
            "location_text": location_text,
            "city": self._extract_city(location_text),
            "remote_mode": remote_mode,
        }

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
        for line in lines[start_index : start_index + 14]:
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

    def _extract_detail_location(self, lines: list[str]) -> str | None:
        for idx, line in enumerate(lines):
            if line.lower() == "le lieu de travail":
                for candidate in lines[idx + 1 : idx + 5]:
                    low = candidate.lower()
                    if low in self.NOISE_LINES:
                        continue
                    if self._infer_contract_type(candidate):
                        continue
                    return candidate
        for line in lines:
            low = line.lower()
            if low.startswith("localisation"):
                return line.split(":", 1)[-1].strip() or None
        return None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None
        match = self.ADDRESS_CITY_RE.search(location_text)
        if match:
            city = normalize_spaces(match.group(1).strip(" ,"))
            return city or None
        city = normalize_spaces(location_text.split(",")[0].strip())
        return city or None

    def _fallback_location_from_url(self, url: str) -> str | None:
        parsed = urlsplit(url)
        slug = parsed.path.rstrip("/").rsplit("_", 1)[-1].strip().lower()
        if slug == "paris":
            return "Paris"
        if slug == "lyon":
            return "Lyon"
        return None

    def _is_location_candidate(self, line: str) -> bool:
        low = line.lower()
        if not line:
            return False
        if self._infer_contract_type(line):
            return False
        if self.WTTJ_RELATIVE_RE.match(low):
            return False
        if "télétravail" in low or "teletravail" in low:
            return False
        if low.startswith("salaire") or low.startswith("expérience") or low.startswith("experience"):
            return False
        if low.startswith("éducation") or low.startswith("education"):
            return False
        if re.search(r"\d+\s+mois", low):
            return False
        if low.startswith("début") or low.startswith("debut"):
            return False
        return bool(re.match(r"^[A-Za-zÀ-ÿ0-9,'\- ]+$", line))

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
                "profil recherché",
                "l’entreprise",
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

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()
        if "alternance" in low or "apprentissage" in low or "apprenti" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low or "temporaire" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str | None, contract_type: str | None, description_text: str | None) -> str | None:
        contract_low = (contract_type or "").lower()
        low = " ".join(filter(None, [title, description_text])).lower()
        if contract_low in {"cdi", "cdd"}:
            return "emploi"
        if contract_low == "alternance":
            return "alternance"
        if contract_low == "stage":
            return "stage"
        if "alternance" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        return "emploi"

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

    def _is_filled(self, lines: list[str]) -> bool:
        blob = "\n".join(lines).lower()
        return (
            "offre pourvue" in blob
            or "cette offre n'est plus disponible" in blob
            or "cette offre n’est plus disponible" in blob
        )

    def _node_text(self, tree, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if node:
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text:
                    return text
        return None

    def _as_clean_str(self, value: object) -> str | None:
        if value is None:
            return None
        text = normalize_spaces(str(value))
        return text or None
