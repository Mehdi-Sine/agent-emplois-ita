from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

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
    ALGOLIA_URL = (
        "https://csekhvms53-dsn.algolia.net/1/indexes/*/queries"
        "?x-algolia-agent=Algolia%20for%20JavaScript%20(4.20.0)%3B%20Browser"
        "&search_origin=companies_search_client"
    )
    ALGOLIA_APP_ID = "CSEKHVMS53"
    ALGOLIA_API_KEY = "4bd8f6215d0cc52b26430765769e65a0"
    ALGOLIA_JOB_INDEX = "wk_cms_jobs_production"

    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    JOB_URL_RE = re.compile(
        r"^https://www\.welcometothejungle\.com/fr/companies(?:-v1)?/acta/jobs/[^/?#]+/?$",
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
    INVALID_TITLES = {
        "javascript is disabled",
        "access denied",
        "forbidden",
        "just a moment...",
    }

    def __init__(self, source) -> None:
        super().__init__(source)
        self._listing_by_url: dict[str, dict[str, object]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = self._get_with_fallback(client, str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        self._listing_by_url = {}
        urls: list[str] = []
        seen: set[str] = set()

        for card in tree.css("[data-role='jobs:thumb']"):
            link = card.css_first("a[href*='/fr/companies/acta/jobs/'], a[href*='/fr/companies-v1/acta/jobs/']")
            if not link:
                continue

            href = link.attributes.get("href")
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            title = normalize_spaces(link.text(separator=" ", strip=True))
            if not url or not title or self._is_invalid_title(title):
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

        try:
            algolia_urls = self._discover_algolia_offer_urls(client)
        except Exception:
            algolia_urls = []
        if algolia_urls:
            return algolia_urls

        # fallback minimal si WTTJ ne rend pas les cartes avec le même markup
        for node in tree.css("a[href*='/fr/companies/acta/jobs/'], a[href*='/fr/companies-v1/acta/jobs/']"):
            href = node.attributes.get("href")
            text = normalize_spaces(node.text(separator=" ", strip=True))
            url = self._canonicalize_offer_url(absolute_url(str(response.url), href))
            if not url or self._is_invalid_title(text):
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

        detail_text = ""
        detail_url = url
        tree = None
        try:
            response = self._get_with_fallback(client, url)
            response.raise_for_status()
            detail_text = response.text
            detail_url = str(response.url)
            tree = html_tree(detail_text)
        except Exception:
            tree = None

        listing_title = self._as_clean_str(listing.get("title"))
        detail_title = self._node_text(tree, ["h1", "h2"]) if tree else None
        if self._is_invalid_title(detail_title):
            detail_title = None
        title = listing_title or detail_title
        if not title or self._is_invalid_title(title):
            return None

        lines = self._extract_lines(tree) if tree else []
        header_lines = self._extract_header_lines(lines, title) if lines else []

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
        posted_at = self._extract_posted_at(detail_text) if detail_text else None
        posted_at = posted_at or listing.get("posted_at")
        description_text = self._extract_description(lines, title) if lines else None
        description_text = description_text or self._as_clean_str(listing.get("description_text"))
        application_url = self._extract_application_url(tree, detail_url) if tree else None
        application_url = application_url or url
        deadline = self._extract_deadline(lines) if lines else None

        is_filled = self._is_filled(lines) if lines else False
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

    def _discover_algolia_offer_urls(self, client: Client) -> list[str]:
        hits = self._search_algolia_jobs(client)
        urls: list[str] = []
        seen: set[str] = set()

        for hit in hits:
            if not self._is_acta_algolia_hit(hit):
                continue

            title = self._as_clean_str(hit.get("name") or hit.get("title"))
            url = self._canonicalize_offer_url(
                self._as_clean_str(hit.get("url")) or self._build_algolia_job_url(hit)
            )
            if not title or self._is_invalid_title(title) or not url or url in seen:
                continue

            blob = f"{url} {title}".lower()
            if "spontan" in blob:
                continue

            meta = {
                "title": title,
                "contract_type": self._extract_algolia_contract_type(hit),
                "location_text": self._extract_algolia_location(hit) or self._fallback_location_from_url(url),
                "city": self._extract_city(self._extract_algolia_location(hit) or self._fallback_location_from_url(url)),
                "remote_mode": self._extract_algolia_remote(hit),
                "posted_at": self._parse_algolia_date(hit.get("published_at") or hit.get("date")),
                "description_text": self._as_clean_str(hit.get("description")),
            }
            self._listing_by_url[url] = meta
            seen.add(url)
            urls.append(url)

        return urls

    def _search_algolia_jobs(self, client: Client) -> list[dict[str, object]]:
        params = urlencode({"hitsPerPage": 50, "page": 0, "query": "acta"})
        payload = {"requests": [{"indexName": self.ALGOLIA_JOB_INDEX, "params": params}]}
        headers = {
            "x-algolia-application-id": self.ALGOLIA_APP_ID,
            "x-algolia-api-key": self.ALGOLIA_API_KEY,
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://www.welcometothejungle.com",
            "referer": "https://www.welcometothejungle.com/",
        }
        response = client.post(self.ALGOLIA_URL, content=json.dumps(payload), headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not results or not isinstance(results, list):
            return []
        hits = results[0].get("hits") if isinstance(results[0], dict) else None
        return hits if isinstance(hits, list) else []

    def _is_acta_algolia_hit(self, hit: dict[str, object]) -> bool:
        organization = hit.get("organization")
        organization = organization if isinstance(organization, dict) else {}
        slug_candidates = [
            hit.get("organization_slug"),
            hit.get("companySlug"),
            hit.get("company_slug"),
            organization.get("slug"),
        ]
        if any(str(value or "").strip().lower() == "acta" for value in slug_candidates):
            return True

        name_candidates = [
            organization.get("name"),
            hit.get("organization_name"),
            hit.get("companyName"),
            hit.get("company_name"),
        ]
        return any(self._is_acta_company_name(value) for value in name_candidates)

    def _is_acta_company_name(self, value: object) -> bool:
        name = str(value or "").strip().lower()
        return bool(re.match(r"^acta(?:\b|\s|\s*[-–—|])", name))

    def _is_invalid_title(self, value: object) -> bool:
        title = self._as_clean_str(value)
        return not title or title.lower() in self.INVALID_TITLES

    def _build_algolia_job_url(self, hit: dict[str, object]) -> str | None:
        slug = self._as_clean_str(hit.get("slug"))
        if not slug:
            return None
        return f"https://www.welcometothejungle.com/fr/companies-v1/acta/jobs/{slug}"

    def _extract_algolia_contract_type(self, hit: dict[str, object]) -> str | None:
        names = hit.get("contract_type_names")
        if isinstance(names, dict):
            raw = names.get("fr") or names.get("en")
            inferred = self._infer_contract_type(str(raw))
            if inferred:
                return inferred
        return self._infer_contract_type(self._as_clean_str(hit.get("contract_type")))

    def _extract_algolia_location(self, hit: dict[str, object]) -> str | None:
        office = hit.get("office")
        office = office if isinstance(office, dict) else {}
        offices = hit.get("offices")
        if isinstance(offices, list) and offices and isinstance(offices[0], dict):
            office = offices[0]
        city = self._as_clean_str(office.get("city"))
        return city or self._as_clean_str(hit.get("location"))

    def _extract_algolia_remote(self, hit: dict[str, object]) -> str | None:
        remote = self._as_clean_str(hit.get("remote"))
        if not remote or remote.lower() == "unknown":
            return None
        return remote

    def _parse_algolia_date(self, value: object) -> datetime | None:
        raw = self._as_clean_str(value)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

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


    def _get_with_fallback(self, client: Client, url: str):
        response = client.get(url)
        if response.status_code != 403:
            response.raise_for_status()
            return response

        retry_headers = dict(self.BROWSER_HEADERS)
        retry_headers["Referer"] = str(self.source.site_url)
        response = client.get(url, headers=retry_headers)
        response.raise_for_status()
        return response
