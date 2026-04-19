from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

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


class IteipmaiConnector(BaseConnector):
    FRENCH_MONTHS = {
        "janvier": 1,
        "février": 2,
        "fevrier": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "aout": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,
        "decembre": 12,
    }

    TEMPORAL_WORDS = (
        "janvier",
        "février",
        "fevrier",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "aout",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
        "decembre",
        "mois",
        "semestre",
        "période",
        "periode",
        "dates flexibles",
        "à partir de",
        "a partir de",
        "idéalement",
        "idealement",
        "pourvoir",
        "recrutement",
    )

    def __init__(self, source) -> None:
        super().__init__(source)
        self._listing_index: dict[str, dict[str, Any]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        root = tree.css_first("main") or tree.css_first("body") or tree
        listing_index: dict[str, dict[str, Any]] = {}
        offer_urls: list[str] = []
        seen: set[str] = set()

        for link in root.css('a[target="_blank"]'):
            href = link.attributes.get("href")
            url = absolute_url(str(response.url), href)
            if not self._is_internal_offer_url(url):
                continue
            if url in seen:
                continue

            title = self._extract_listing_title(link)
            if not title:
                continue

            paragraphs = self._extract_listing_paragraphs(link)
            posted_raw = self._extract_posted_raw(paragraphs)
            contract_raw = self._extract_contract_raw(paragraphs)
            is_filled = self._extract_is_filled(paragraphs, title)
            location_text = self._extract_listing_location(paragraphs)

            offer_type = self._infer_offer_type(
                url=url,
                title=title,
                contract_raw=contract_raw,
                paragraphs=paragraphs,
            )
            contract_type = self._infer_contract_type(
                url=url,
                title=title,
                contract_raw=contract_raw,
                paragraphs=paragraphs,
            )

            listing_index[url] = {
                "source_url": url,
                "application_url": url,
                "title": title,
                "posted_at": self._parse_french_date(posted_raw),
                "posted_raw": posted_raw,
                "contract_type": contract_type,
                "contract_raw": contract_raw,
                "offer_type": offer_type,
                "location_text": location_text,
                "is_filled": is_filled,
                "listing_status": "filled" if is_filled else "open",
            }

            seen.add(url)
            offer_urls.append(url)

        self._listing_index = listing_index
        return offer_urls

    def parse_offer(self, client: Client, url: str) -> dict[str, Any] | None:
        seed = dict(self._listing_index.get(url, {}))
        if not seed:
            return None

        # On garde prioritairement le titre de la carte liste
        title = seed.get("title")
        posted_at = seed.get("posted_at")
        contract_type = seed.get("contract_type")
        offer_type = seed.get("offer_type")
        location_text = seed.get("location_text")
        description_text = None

        try:
            response = client.get(url)
            response.raise_for_status()
            tree = html_tree(response.text)

            detail_text = tree.text(separator="\n", strip=True) or ""
            description_text = self._extract_detail_description(tree, listing_title=title)

            if not posted_at:
                posted_at = self._extract_date_from_detail(detail_text)

            if not contract_type:
                contract_type = self._infer_contract_type(
                    url=url,
                    title=title,
                    contract_raw=detail_text,
                    paragraphs=[],
                )

            if not offer_type:
                offer_type = self._infer_offer_type(
                    url=url,
                    title=title,
                    contract_raw=detail_text,
                    paragraphs=[],
                )

            if not location_text:
                location_text = self._extract_location_from_detail(detail_text)

        except Exception:
            pass

        if not title:
            return None

        title = self._clean_title(title)
        location_text = self._normalize_location(location_text)
        city = self._extract_city(location_text)

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
            "remote_mode": None,
            "posted_at": posted_at,
            "raw_posted_at": seed.get("posted_raw"),
            "raw_contract": seed.get("contract_raw"),
            "is_filled": bool(seed.get("is_filled")),
            "listing_status": seed.get("listing_status") or "open",
        }

    def normalize_offer(self, raw_item: dict[str, Any]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ITEIPMAI"
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
                    posted_at.isoformat() if posted_at else None,
                    raw_item.get("description_text"),
                    str(raw_item.get("is_filled")),
                ]
            ),
            raw_payload=raw_item,
        )

    def _is_internal_offer_url(self, url: str | None) -> bool:
        if not url:
            return False

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc not in {"www.iteipmai.fr", "iteipmai.fr"}:
            return False

        path = parsed.path or ""
        if not path or path == "/":
            return False
        if path.rstrip("/") == urlparse(str(self.source.jobs_url)).path.rstrip("/"):
            return False
        if re.search(r"\.(pdf|jpg|jpeg|png|svg|webp|doc|docx|xls|xlsx)$", path, flags=re.IGNORECASE):
            return False

        return True

    def _extract_listing_title(self, link) -> str | None:
        heading = (
            link.css_first("h2")
            or link.css_first("h3")
            or link.css_first(".elementor-heading-title")
        )
        if not heading:
            return None

        title = normalize_spaces(heading.text(separator=" ", strip=True))
        return self._clean_title(title)

    def _clean_title(self, value: str | None) -> str | None:
        if not value:
            return None
        text = normalize_spaces(value)
        if not text:
            return None
        text = re.sub(r"\s+", " ", text).strip()
        text = text.rstrip()
        return text or None

    def _extract_listing_paragraphs(self, link) -> list[str]:
        paragraphs: list[str] = []
        for p in link.css("p"):
            text = normalize_spaces(p.text(separator=" ", strip=True))
            if text:
                paragraphs.append(text)
        return paragraphs

    def _extract_posted_raw(self, paragraphs: list[str]) -> str | None:
        for p in paragraphs:
            if p.lower().startswith("publiée le"):
                return p
        return None

    def _extract_contract_raw(self, paragraphs: list[str]) -> str | None:
        for p in paragraphs:
            if self._is_contract_line(p):
                return p
        return None

    def _extract_is_filled(self, paragraphs: list[str], title: str | None) -> bool:
        blob = " ".join([title or "", *paragraphs]).lower()
        return "annonce pourvue" in blob or "annonces pourvues" in blob

    def _extract_listing_location(self, paragraphs: list[str]) -> str | None:
        fragments: list[str] = []

        for p in paragraphs:
            if self._is_posted_line(p) or self._is_status_line(p):
                continue

            if self._is_contract_line(p):
                maybe_location = self._extract_location_fragment(p)
                if maybe_location:
                    fragments.append(maybe_location)
                continue

            if self._looks_like_location_line(p):
                fragments.append(p)
                continue

            maybe_location = self._extract_location_fragment(p)
            if maybe_location:
                fragments.append(maybe_location)

        if not fragments:
            return None

        cleaned_parts: list[str] = []
        i = 0
        while i < len(fragments):
            current = self._normalize_location_fragment(fragments[i])
            if not current:
                i += 1
                continue

            if current.lower().endswith(" ou") and i + 1 < len(fragments):
                nxt = self._normalize_location_fragment(fragments[i + 1])
                if nxt:
                    current = f"{current} {nxt}"
                    i += 1

            cleaned_parts.append(current)
            i += 1

        deduped: list[str] = []
        seen: set[str] = set()
        for part in cleaned_parts:
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(part)

        if not deduped:
            return None

        if len(deduped) == 1:
            return self._normalize_location(deduped[0])

        return self._normalize_location(" ou ".join(deduped))

    def _is_posted_line(self, value: str) -> bool:
        return value.lower().startswith("publiée le")

    def _is_status_line(self, value: str) -> bool:
        lower = value.lower()
        return "annonce pourvue" in lower or "annonces pourvues" in lower

    def _is_contract_line(self, value: str) -> bool:
        lower = normalize_spaces(value).lower()

        if "poste en cdd" in lower or "postes en cdd" in lower or "poste en cdi" in lower:
            return True
        if "cdi à pourvoir" in lower or "à pourvoir en" in lower:
            return True
        if lower.startswith("stage "):
            return True
        if lower.startswith("m2 :") or lower.startswith("m2:"):
            return True
        if lower.startswith("l3-m1 :") or lower.startswith("l3-m1:"):
            return True
        if "stage master" in lower or "stage ingénieur" in lower or "stage ingenieur" in lower:
            return True
        if re.match(r"^\d+\s*à\s*\d+\s*mois\b", lower):
            return True
        if re.match(r"^\d+\s*mois\b", lower):
            return True
        if "dates flexibles" in lower:
            return True
        if "idéalement à partir de" in lower or "idealement a partir de" in lower:
            return True
        if "recrutement en" in lower:
            return True
        if "permis b" in lower:
            return True

        return False

    def _extract_location_fragment(self, value: str) -> str | None:
        text = normalize_spaces(value)
        if not text:
            return None

        # Cas "2 à 6 mois, à Chemillé-en-Anjou"
        match = re.search(r",\s*[àa]\s+(.+)$", text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if self._is_probable_location_text(candidate):
                return candidate

        # Cas "A Montboucher..." / "à Chemillé..."
        match = re.match(r"^[àa]\s+(.+)$", text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if self._is_probable_location_text(candidate):
                return candidate

        # Cas "Basé sur ... 26740 Montboucher-sur-Jabron"
        zip_match = re.search(r"\b\d{5}\s+([A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\- ]+)$", text)
        if zip_match:
            return zip_match.group(1).strip()

        # Cas "Basé sur la station ... de Chemillé-en-Anjou (49)"
        if text.lower().startswith(("basé sur", "base sur")):
            de_match = re.search(r"\bde\s+([A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\- ]+\([^)]+\))$", text)
            if de_match:
                return de_match.group(1).strip()

            a_match = re.search(r"\bà\s+([A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\- ]+\([^)]+\))$", text)
            if a_match:
                return a_match.group(1).strip()

            plain_match = re.search(r"\bà\s+([A-ZÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\- ]+)$", text)
            if plain_match:
                candidate = plain_match.group(1).strip()
                if self._is_probable_location_text(candidate):
                    return candidate

        return None

    def _looks_like_location_line(self, value: str) -> bool:
        text = normalize_spaces(value)
        if not text:
            return False

        lower = text.lower()
        if self._is_posted_line(text) or self._is_status_line(text):
            return False
        if self._is_contract_line(text):
            return False

        if lower.startswith("basé sur") or lower.startswith("base sur") or lower.startswith("lieu de"):
            return True
        if re.search(r"\(\d{2}\)$", text):
            return True
        if re.search(r"\b\d{5}\s+[A-ZÀ-ÖØ-öø-ÿ]", text):
            return True
        if "chemillé" in lower or "montboucher" in lower or "obernai" in lower:
            return True
        if lower.endswith(" ou"):
            return True

        return self._is_probable_location_text(text)

    def _is_probable_location_text(self, value: str) -> bool:
        text = normalize_spaces(value)
        if not text:
            return False

        lower = text.lower()
        if self._is_posted_line(text) or self._is_status_line(text):
            return False

        for marker in self.TEMPORAL_WORDS:
            if marker in lower and not (
                "chemillé" in lower or "montboucher" in lower or "obernai" in lower or re.search(r"\(\d{2}\)", text)
            ):
                return False

        if re.match(r"^\d+\s+[A-Za-z]", text) and not re.search(r"\b\d{5}\b", text):
            return False
        if len(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+", text)) > 12:
            return False

        return True

    def _normalize_location_fragment(self, value: str | None) -> str | None:
        if not value:
            return None

        text = normalize_spaces(value)
        text = text.replace(" ,", ",")
        text = re.sub(r"^\s*[àa]\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*basé sur\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*base sur\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*lieu de stage\s*:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^\s*lieu\s*:\s*", "", text, flags=re.IGNORECASE)
        text = text.strip(" -–|:.;,")

        if not text:
            return None

        return text

    def _parse_french_date(self, posted_raw: str | None):
        if not posted_raw:
            return None

        clean = normalize_spaces(posted_raw)
        clean = re.sub(r"^Publiée le\s*", "", clean, flags=re.IGNORECASE).strip()

        match = re.match(
            r"^(\d{1,2})\s+([A-Za-zÀ-ÖØ-öø-ÿ]+)\s+(\d{4})$",
            clean,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        day = int(match.group(1))
        month_label = match.group(2).lower()
        year = int(match.group(3))

        month = self.FRENCH_MONTHS.get(month_label)
        if not month:
            return None

        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    def _extract_date_from_detail(self, text: str | None):
        if not text:
            return None

        match = re.search(
            r"Publiée le\s+(\d{1,2}\s+[A-Za-zÀ-ÖØ-öø-ÿ]+\s+\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return self._parse_french_date(f"Publiée le {match.group(1)}")

        match = re.search(
            r"\b(\d{1,2}\s+[A-Za-zÀ-ÖØ-öø-ÿ]+\s+\d{4})\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return self._parse_french_date(f"Publiée le {match.group(1)}")

        return None

    def _extract_location_from_detail(self, text: str | None) -> str | None:
        if not text:
            return None

        patterns = [
            r"Lieu de stage\s*:\s*([^\n\r]+)",
            r"Poste basé à\s*([^\n\r]+)",
            r"Basé sur\s*([^\n\r]+)",
            r"Base sur\s*([^\n\r]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                fragment = self._extract_location_fragment(match.group(1)) or match.group(1)
                return self._normalize_location(fragment)

        # fallback si on repère une ville claire dans le texte
        city_patterns = [
            r"\b(Chemillé-en-Anjou\s*\([^)]+\))",
            r"\b(Montboucher[-\s]sur[-\s]Jabron\s*\([^)]+\))",
            r"\b(Obernai\s*\([^)]+\))",
            r"\b\d{5}\s+(Montboucher[-\s]sur[-\s]Jabron)\b",
        ]
        for pattern in city_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._normalize_location(match.group(1))

        return None

    def _normalize_location(self, value: str | None) -> str | None:
        if not value:
            return None

        text = normalize_spaces(value)
        if not text:
            return None

        text = text.replace(" ,", ",")
        text = re.sub(r"\s+ou\s+", " ou ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b\d{5}\s+([A-ZÀ-ÖØ-öø-ÿ])", r"\1", text)
        text = text.strip(" -–|:.;,")

        return text or None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None

        first = location_text.split(" ou ")[0].strip()

        match = re.match(r"^(.+?)\s*\([^)]+\)$", first)
        if match:
            first = match.group(1).strip()

        match = re.search(r"\b\d{5}\s+(.+)$", first)
        if match:
            first = match.group(1).strip()

        if " à " in first:
            candidate = first.split(" à ")[-1].strip()
            if candidate:
                first = candidate

        first = normalize_spaces(first)
        return first or None

    def _extract_detail_description(self, tree, listing_title: str | None = None) -> str | None:
        raw = description_from_selectors(tree, ["main", "article", "body"])
        if not raw:
            return None

        lines: list[str] = []
        started = False

        stop_markers = (
            "Restez informé",
            "Actualités & veille",
            "Voir toutes les actualités",
            "L'iteipmai",
            "Publications",
            "Prestations",
            "Autres liens",
        )

        for raw_line in raw.split("\n"):
            line = normalize_spaces(raw_line)
            if not line:
                continue

            lower = line.lower()

            if any(marker.lower() in lower for marker in stop_markers):
                break

            if listing_title and line == listing_title:
                started = True
                continue

            if not started:
                if (
                    line.startswith("Poste")
                    or line.startswith("Etude")
                    or line.startswith("Étude")
                    or line.startswith("Evaluation")
                    or line.startswith("Évaluation")
                    or line.startswith("Captation")
                    or line.startswith("La régulation")
                    or line.startswith("Chargé")
                    or line.startswith("Assistant")
                    or line.startswith("Technicien")
                ):
                    started = True
                else:
                    continue

            lines.append(line)

        if not lines:
            return None

        return "\n".join(lines)

    def _infer_offer_type(
        self,
        url: str | None,
        title: str | None,
        contract_raw: str | None,
        paragraphs: list[str] | None = None,
    ) -> str | None:
        blob = " ".join([url or "", title or "", contract_raw or "", " ".join(paragraphs or [])]).lower()
        if "stage" in blob or "m2 :" in blob or "l3-m1 :" in blob:
            return "stage"
        return "emploi"

    def _infer_contract_type(
        self,
        url: str | None,
        title: str | None,
        contract_raw: str | None,
        paragraphs: list[str] | None = None,
    ) -> str | None:
        blob = " ".join([url or "", title or "", contract_raw or "", " ".join(paragraphs or [])]).lower()

        if "cdd" in blob:
            return "cdd"
        if "cdi" in blob:
            return "cdi"
        if "stage" in blob or "m2 :" in blob or "l3-m1 :" in blob:
            return "stage"
        return None