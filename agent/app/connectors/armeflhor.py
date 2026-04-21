from __future__ import annotations

import re
from datetime import datetime, timedelta
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


class ArmeflhorConnector(BaseConnector):
    ARTICLE_URL_RE = re.compile(r"^https://www\.armeflhor\.fr/(?!category/|tag/|wp-)([^/?#]+)/?$", re.IGNORECASE)
    PUBLISHED_RE = re.compile(
        r'(?:article:published_time|datePublished)"?\s*[:=]\s*"(?P<value>\d{4}-\d{2}-\d{2})',
        re.IGNORECASE,
    )
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

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        urls: list[str] = []
        seen: set[str] = set()

        selectors = [
            "h2 a[href]",
            "article a[href]",
        ]
        candidates = []
        for selector in selectors:
            candidates.extend(tree.css(selector))

        for node in candidates:
            href = node.attributes.get("href")
            text = normalize_spaces(node.text(separator=" ", strip=True))
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            if not url:
                continue
            if not text:
                continue
            lower = text.lower()
            if lower in {"recrutement", "adhésion", "adhesion"}:
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

        lines = self._extract_lines(tree)
        title = self._extract_title(tree, lines)
        if not title:
            return None

        description_text = self._extract_description(lines, title)
        contract_type = self._extract_contract_type(lines, title, description_text)
        location_text = self._extract_location(lines) or "Saint-Pierre (97410) - La Réunion"
        city = self._extract_city(location_text)
        posted_at = self._extract_posted_at(response.text)
        application_url = self._extract_application_url(lines, url)
        is_filled = self._is_filled(lines, posted_at)
        listing_status = "filled" if is_filled else "open"
        offer_type = self._infer_offer_type(title, contract_type, description_text)

        return {
            "source_url": url,
            "application_url": application_url,
            "title": title,
            "description_text": description_text,
            "location_text": location_text,
            "city": city,
            "region": "La Réunion",
            "country": "France",
            "contract_type": contract_type,
            "offer_type": offer_type,
            "remote_mode": None,
            "posted_at": posted_at,
            "raw_posted_at": posted_at.isoformat() if posted_at else None,
            "is_filled": is_filled,
            "listing_status": listing_status,
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ARMEFLHOR"
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
            region=str(raw_item.get("region")) if raw_item.get("region") else None,
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
        return clean if self.ARTICLE_URL_RE.match(clean) else None

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        lines: list[str] = []
        for raw_line in text.splitlines():
            line = normalize_spaces(raw_line)
            if not line:
                continue
            if line.lower().startswith("image"):
                continue
            lines.append(line)
        return lines

    def _extract_title(self, tree, lines: list[str]) -> str | None:
        for selector in ("h1", "h2", "h3"):
            node = tree.css_first(selector)
            if node:
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text and text.lower() != "l'armeflhor recrute !":
                    return text

        for idx, line in enumerate(lines):
            if line.lower() == "l'armeflhor recrute !" and idx + 1 < len(lines):
                return lines[idx + 1]
        return None

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
            if lower in {"coordonnées", "coordonnees", "a propos", "publications", "contact"}:
                break
            if lower in {"l'armeflhor recrute !"}:
                continue
            kept.append(line)
        return "\n\n".join(kept).strip() or None

    def _extract_contract_type(self, lines: list[str], title: str, description_text: str | None) -> str | None:
        for line in lines:
            if "contrat :" in line.lower():
                return self._infer_contract_type(line)
        return self._infer_contract_type(" ".join(filter(None, [title, description_text])))

    def _extract_location(self, lines: list[str]) -> str | None:
        joined = "\n".join(lines)
        if "97410" in joined and "Saint-Pierre" in joined:
            return "Saint-Pierre (97410) - La Réunion"
        return None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None
        city = location_text.split("(")[0].split("-")[0].strip()
        return normalize_spaces(city) or None

    def _extract_posted_at(self, html: str) -> datetime | None:
        match = self.PUBLISHED_RE.search(html)
        if match:
            raw = match.group("value")
            try:
                return datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                pass
        return None

    def _extract_application_url(self, lines: list[str], source_url: str) -> str:
        blob = "\n".join(lines)
        email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", blob)
        if email_match:
            return f"mailto:{email_match.group(0)}"
        return source_url

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "service civique" in low:
            return "service civique"
        if "vsc" in low:
            return "vsc"
        if "stage" in low:
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

        if contract_low in {"cdi", "cdd", "vsc", "service civique"}:
            return "emploi"
        if contract_low == "stage":
            return "stage"
        if contract_low == "alternance":
            return "alternance"
        if "stage" in title_low or "stagiaire" in title_low:
            return "stage"
        if "alternance" in title_low or "apprentissage" in title_low:
            return "alternance"
        if "service civique" in title_low or "vsc" in title_low:
            return "emploi"
        if "stage" in desc_low:
            return "stage"
        if "alternance" in desc_low:
            return "alternance"
        return "emploi"

    def _is_filled(self, lines: list[str], posted_at: datetime | None) -> bool:
        blob = "\n".join(lines).lower()
        if "offre pourvue" in blob or "recrutement terminé" in blob or "recrutement termine" in blob:
            return True
        if posted_at and posted_at.date() < (datetime.utcnow().date() - timedelta(days=180)):
            return True
        return False
