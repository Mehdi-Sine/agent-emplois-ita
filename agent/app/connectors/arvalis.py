from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlunsplit, urlsplit

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


class ArvalisConnector(BaseConnector):
    LISTING_URL = "https://www.arvalis.fr/l-institut/nous-rejoindre/offres-d-emploi-de-stages"
    DETAIL_PREFIX = "https://www.arvalis.fr/l-institut/nous-rejoindre/offres-d-emploi-de-stages/"

    ALGOLIA_APP_ID = "5JZPVHMY0V"
    ALGOLIA_API_KEY = "63b868a1de88d91927a5feb55484245c"
    ALGOLIA_INDEX_NAME = "job_offers"
    ALGOLIA_HITS_PER_PAGE = 100

    DATE_NUMERIC_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
    DATE_TEXT_RE = re.compile(
        r"\b(\d{1,2})\s+([A-Za-zÀ-ÿ\.]+)\s+(\d{4})\b",
        re.IGNORECASE,
    )
    DEPT_RE = re.compile(r"\((\d{2,3})\)$")

    CONTRACT_MARKERS = (
        "cdi",
        "cdd",
        "stage",
        "alternance",
        "apprentissage",
        "apprenti",
        "thèse",
        "these",
        "intérim",
        "interim",
        "contrat de mission",
    )

    FOOTER_MARKERS = {
        "postuler",
        "partager :",
        "partager",
        "accès rapides",
        "acces rapides",
        "newsletters",
        "contact",
        "autres sites",
        "suivez nous :",
        "suivez-nous :",
        "© arvalis 2026",
        "© arvalis",
    }

    LABELS = {
        "lieu",
        "lieu de travail",
        "date de début du contrat",
        "date de debut du contrat",
        "date de dépôt de l'offre",
        "date de depot de l'offre",
        "date de dépôt de l’offre",
        "date de depot de l’offre",
        "référence",
        "reference",
        "durée",
        "duree",
        "informations complémentaires",
        "informations complementaires",
    }

    MONTHS_FR = {
        "janvier": 1,
        "janv": 1,
        "janv.": 1,
        "février": 2,
        "fevrier": 2,
        "févr": 2,
        "fevr": 2,
        "févr.": 2,
        "fevr.": 2,
        "mars": 3,
        "avril": 4,
        "avr": 4,
        "avr.": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "juil": 7,
        "juil.": 7,
        "août": 8,
        "aout": 8,
        "septembre": 9,
        "sept": 9,
        "sept.": 9,
        "octobre": 10,
        "oct": 10,
        "oct.": 10,
        "novembre": 11,
        "nov": 11,
        "nov.": 11,
        "décembre": 12,
        "decembre": 12,
        "déc": 12,
        "dec": 12,
        "déc.": 12,
        "dec.": 12,
    }

    def __init__(self, source) -> None:
        super().__init__(source)
        self._hits_by_url: dict[str, dict[str, object]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        self._hits_by_url = {}
        hits = self._fetch_all_algolia_hits(client)

        urls: list[str] = []
        seen: set[str] = set()

        for hit in hits:
            url = self._url_from_hit(hit)
            if not url or url in seen:
                continue
            seen.add(url)
            self._hits_by_url[url] = hit
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        hit = self._hits_by_url.get(url, {})

        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)

        title = self._node_text(tree, ["h1"]) or self._hit_str(hit, "title")
        if not title:
            return None

        lines = self._extract_lines(tree)

        if not self._looks_like_offer_page(lines, title):
            return None

        contract_type = (
            self._normalize_contract_type(hit.get("contracts_types"))
            or self._extract_contract_type_from_context(lines, title)
        )

        location_text = (
            self._extract_label_value(lines, "Lieu")
            or self._extract_label_value(lines, "Lieu de travail")
            or self._hit_str(hit, "place")
        )

        posted_raw = self._extract_label_value(lines, "Date de dépôt de l'offre")
        start_date_raw = self._extract_label_value(lines, "Date de début du contrat")
        reference = self._extract_label_value(lines, "Référence") or self._hit_str(hit, "reference")
        duration = self._extract_label_value(lines, "Durée")

        city = self._extract_city(location_text)
        posted_at = self._parse_date_fr(posted_raw) or self._parse_algolia_timestamp(hit.get("displayed_date"))
        description_text = self._extract_description(lines, title, reference) or self._hit_str(hit, "body_1")

        application_url = self._extract_application_url(tree, str(response.url)) or self._build_application_url(url)

        if not contract_type:
            contract_type = self._infer_contract_type(
                " ".join(filter(None, [title, description_text, duration]))
            )

        is_filled = self._is_filled(lines)
        listing_status = "filled" if is_filled else "open"

        offer_type = self._infer_offer_type(
            title=title,
            contract_type=contract_type,
            description_text=description_text,
        )

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
            "remote_mode": None,
            "posted_at": posted_at,
            "raw_posted_at": posted_raw,
            "raw_start_date": start_date_raw,
            "reference": reference,
            "duration": duration,
            "is_filled": is_filled,
            "listing_status": listing_status,
            "algolia_hit": hit,
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre ARVALIS"
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
            country=str(raw_item.get("country")) if raw_item.get("country") else None,
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
                    str(raw_item.get("reference")) if raw_item.get("reference") else None,
                    str(raw_item.get("duration")) if raw_item.get("duration") else None,
                    str(raw_item.get("is_filled")),
                ]
            ),
            raw_payload=raw_item,
        )

    # -------------------------------------------------------------------------
    # ALGOLIA DISCOVERY
    # -------------------------------------------------------------------------

    def _fetch_all_algolia_hits(self, client: Client) -> list[dict[str, object]]:
        first_page = self._query_algolia(client, page=0)
        hits: list[dict[str, object]] = list(first_page.get("hits", []))
        nb_pages = int(first_page.get("nbPages", 1) or 1)

        for page in range(1, nb_pages):
            data = self._query_algolia(client, page=page)
            hits.extend(data.get("hits", []))

        return hits

    def _query_algolia(self, client: Client, page: int) -> dict[str, object]:
        url = f"https://{self.ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{self.ALGOLIA_INDEX_NAME}/query"
        headers = {
            "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
            "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "query": "",
            "hitsPerPage": self.ALGOLIA_HITS_PER_PAGE,
            "page": page,
            "facets": ["*"],
            "maxValuesPerFacet": 20,
        }

        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _url_from_hit(self, hit: dict[str, object]) -> str | None:
        raw = hit.get("arvalis_entity_url")
        if not raw:
            return None

        url = absolute_url(self.LISTING_URL, str(raw))
        return self._canonicalize_offer_url(url)

    def _canonicalize_offer_url(self, url: str | None) -> str | None:
        if not url:
            return None

        parsed = urlsplit(url)
        clean = urlunsplit((parsed.scheme or "https", parsed.netloc, parsed.path, "", ""))

        if not clean.startswith(self.DETAIL_PREFIX):
            return None

        slug = clean.rstrip("/").rsplit("/", 1)[-1].strip()
        if not slug:
            return None

        if slug.isdigit():
            return None

        if slug in {
            "offres-d-emploi-de-stages",
            "candidature-spontanee",
        }:
            return None

        return clean.rstrip("/")

    def _build_application_url(self, url: str) -> str:
        return url.rstrip("/") + "/postuler"

    # -------------------------------------------------------------------------
    # DETAIL PARSING
    # -------------------------------------------------------------------------

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)

        lines: list[str] = []
        for raw_line in text.splitlines():
            line = self._clean_line(raw_line)
            if not line:
                continue
            lines.append(line)

        return lines

    def _clean_line(self, value: str | None) -> str:
        if value is None:
            return ""

        value = str(value).replace("\xa0", " ")
        value = normalize_spaces(value)
        if not value:
            return ""

        value = re.sub(r"^[\*\-•·]+\s*", "", value)
        value = normalize_spaces(value)

        if re.fullmatch(r"[,;:\-–|/\\\(\)\[\]\{\}\.]+", value or ""):
            return ""

        return value or ""

    def _looks_like_offer_page(self, lines: list[str], title: str) -> bool:
        blob = "\n".join(lines).lower()

        if "référence" in blob or "reference" in blob:
            return True
        if "date de dépôt de l'offre" in blob or "date de depot de l'offre" in blob:
            return True
        if "date de dépôt de l’offre" in blob or "date de depot de l’offre" in blob:
            return True
        if "postuler" in blob and title:
            return True

        return False

    def _extract_label_value(self, lines: list[str], label: str) -> str | None:
        target = self._normalize_label(label)

        for idx, line in enumerate(lines):
            if self._normalize_label(line) != target:
                continue

            for candidate in lines[idx + 1 : idx + 6]:
                if not candidate:
                    continue

                candidate_norm = self._normalize_label(candidate)
                if candidate_norm in self.LABELS:
                    continue

                return candidate

        return None

    def _normalize_label(self, value: str | None) -> str:
        text = normalize_spaces(value or "")
        if not text:
            return ""

        text = text.lower().replace("’", "'")
        replacements = {
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "à": "a",
            "â": "a",
            "ù": "u",
            "û": "u",
            "î": "i",
            "ï": "i",
            "ô": "o",
            "ö": "o",
            "ç": "c",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)

        return text

    def _extract_contract_type_from_context(self, lines: list[str], title: str) -> str | None:
        contract = self._infer_contract_type(title)
        if contract:
            return contract

        title_lower = title.lower()

        for idx, line in enumerate(lines):
            if line.lower() != title_lower:
                continue

            for candidate in lines[idx + 1 : idx + 6]:
                contract = self._infer_contract_type(candidate)
                if contract:
                    return contract

            for candidate in reversed(lines[max(0, idx - 2) : idx]):
                contract = self._infer_contract_type(candidate)
                if contract:
                    return contract

            break

        return None

    def _extract_city(self, location_text: str | None) -> str | None:
        if not location_text:
            return None

        city = location_text.strip()
        city = self.DEPT_RE.sub("", city).strip()
        city = city.strip(" ,;-–")
        city = normalize_spaces(city)

        return city or None

    def _extract_description(
        self,
        lines: list[str],
        title: str,
        reference: str | None,
    ) -> str | None:
        start_index: int | None = None

        if reference:
            for idx, line in enumerate(lines):
                if line == reference:
                    start_index = idx + 1
                    break

        if start_index is None:
            for idx, line in enumerate(lines):
                if line == title:
                    start_index = idx + 1
                    break

        if start_index is None:
            return None

        kept: list[str] = []
        for line in lines[start_index:]:
            lower = line.lower()

            if lower in self.FOOTER_MARKERS:
                break

            if lower in {
                "retour",
                "retour aux offres",
                "offres d'emploi et de stage",
            }:
                continue

            kept.append(line)

        description = "\n\n".join(kept).strip()
        return description or None

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

    # -------------------------------------------------------------------------
    # NORMALIZATION / DATES
    # -------------------------------------------------------------------------

    def _hit_str(self, hit: dict[str, object], key: str) -> str | None:
        value = hit.get(key)
        if value is None:
            return None

        if isinstance(value, list):
            if not value:
                return None
            value = value[0]

        text = normalize_spaces(str(value))
        return text or None

    def _normalize_contract_type(self, value: object) -> str | None:
        if value is None:
            return None

        if isinstance(value, list):
            if not value:
                return None
            value = value[0]

        return self._infer_contract_type(str(value))

    def _parse_algolia_timestamp(self, value: object) -> datetime | None:
        if value is None:
            return None

        try:
            ts = int(value)
            return datetime.utcfromtimestamp(ts)
        except (TypeError, ValueError, OSError):
            return None

    def _parse_date_fr(self, raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None

        raw_value = normalize_spaces(raw_value)
        if not raw_value:
            return None

        m = self.DATE_NUMERIC_RE.search(raw_value)
        if m:
            try:
                return datetime.strptime(m.group(1), "%d/%m/%Y")
            except ValueError:
                pass

        text = raw_value.lower().replace("’", "'")
        text = normalize_spaces(text)
        if not text:
            return None

        m2 = self.DATE_TEXT_RE.search(text)
        if not m2:
            return None

        day = int(m2.group(1))
        month_token = m2.group(2).lower()
        year = int(m2.group(3))
        month = self.MONTHS_FR.get(month_token)

        if not month:
            return None

        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None

        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()

        if "contrat de mission" in low:
            return "contrat de mission"
        if "alternance" in low or "apprentissage" in low or "apprenti" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        if "thèse" in low or "these" in low:
            return "thèse"
        if "intérim" in low or "interim" in low:
            return "intérim"

        return None

    def _infer_offer_type(
        self,
        title: str | None,
        contract_type: str | None,
        description_text: str | None,
    ) -> str | None:
        title_low = (title or "").lower()
        contract_low = (contract_type or "").lower()
        desc_low = (description_text or "").lower()

        if contract_low in {"cdi", "cdd", "intérim", "interim", "contrat de mission"}:
            return "emploi"
        if contract_low == "stage":
            return "stage"
        if contract_low == "alternance":
            return "alternance"
        if contract_low == "thèse":
            return "thèse"

        if any(token in title_low for token in ["stage", "stagiaire"]):
            return "stage"
        if any(token in title_low for token in ["alternance", "apprentissage", "alternant", "apprenti"]):
            return "alternance"
        if any(token in title_low for token in ["thèse", "these", "doctorant", "doctoral", "cifre"]):
            return "thèse"

        if "stage" in desc_low:
            return "stage"
        if "alternance" in desc_low or "apprentissage" in desc_low:
            return "alternance"

        return "emploi"

    def _is_filled(self, lines: list[str]) -> bool:
        blob = "\n".join(lines).lower()
        return (
            "offre pourvue" in blob
            or "poste pourvu" in blob
            or "offre clôturée" in blob
            or "offre cloturee" in blob
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