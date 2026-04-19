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


class CtiflConnector(BaseConnector):
    FLATCHR_COMPANY_FALLBACK_URL = "https://careers.flatchr.io/fr/company/ctifl/"

    COMPANY_SLUG_RE = re.compile(
        r"https://(?:careers\.flatchr\.io|[a-z0-9-]+\.flatchr\.io)(?:/fr|/en)?/company/(?P<slug>[^/?#]+)/?",
        re.IGNORECASE,
    )
    VACANCY_URL_RE = re.compile(
        r"^https://careers\.flatchr\.io/fr/company/[^/]+/vacancy/[^/?#]+/?$",
        re.IGNORECASE,
    )
    DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
    ZIP_RE = re.compile(r"\b\d{5}\b")

    CONTRACT_MARKERS = (
        "cdi",
        "cdd",
        "stage",
        "alternance",
        "apprentissage",
        "thèse",
        "these",
        "intérim",
        "interim",
        "contrat de mission",
    )

    HEADER_STOP_MARKERS = {
        "description",
        "avantages",
        "missions",
        "profil",
        "formation",
        "compétences techniques",
        "competences techniques",
        "atouts appréciés",
        "atouts apprecies",
        "qualités attendues",
        "qualites attendues",
        "postuler",
    }

    FOOTER_MARKERS = {
        "postuler",
        "annonces gérées par",
        "annonces gerees par",
        "obtenir ses données",
        "obtenir ses donnees",
        "politique de confidentialité candidats",
        "politique de confidentialite candidats",
    }

    NOISE_LINES = {
        "ctifl",
        "retour aux offres",
        "partager sur :",
        "partager sur",
        "rejoignez-nous",
        "rejoignez-nous !",
        "*",
        "###",
        "##",
    }

    def __init__(self, source) -> None:
        super().__init__(source)
        self._company_listing_url: str = self.FLATCHR_COMPANY_FALLBACK_URL

    def discover_offer_urls(self, client: Client) -> list[str]:
        # 1) Page officielle CTIFL
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        # 2) Tentative d'extraction d'un lien Flatchr depuis la page,
        # puis fallback sur la page société connue
        company_listing_url = self._discover_company_listing_url(tree, str(response.url))
        self._company_listing_url = company_listing_url

        # 3) Vraie liste exploitable côté Flatchr
        listing_response = client.get(company_listing_url)
        listing_response.raise_for_status()
        listing_tree = html_tree(listing_response.text)

        offer_urls: list[str] = []
        seen: set[str] = set()

        for node in listing_tree.css("a[href*='/vacancy/']"):
            href = node.attributes.get("href")
            url = absolute_url(str(listing_response.url), href)
            url = self._canonicalize_vacancy_url(url)
            if not url or not self.VACANCY_URL_RE.match(url):
                continue
            if "candidature-spontanee" in url.lower():
                continue
            if url in seen:
                continue

            seen.add(url)
            offer_urls.append(url)

        return offer_urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)

        title = normalize_spaces(self._node_text(tree, ["h1"]))
        if not title:
            return None

        lines = self._extract_lines(tree)
        header_lines = self._extract_header_lines(lines, title)

        location_text = self._extract_location(header_lines)
        city = self._extract_city_from_header(header_lines, location_text)

        contract_type = self._extract_contract_type(header_lines)
        posted_raw = self._extract_posted_raw(header_lines)
        posted_at = self._parse_first_date(posted_raw)

        description_text = self._extract_description(lines, title)
        if not contract_type:
            contract_type = self._infer_contract_type(
                " ".join(filter(None, [title, description_text]))
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
            "application_url": self._build_application_url(url),
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
            "is_filled": is_filled,
            "listing_status": listing_status,
            "company_listing_url": self._company_listing_url,
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre CTIFL"
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
                    str(raw_item.get("is_filled")),
                ]
            ),
            raw_payload=raw_item,
        )

    def _discover_company_listing_url(self, tree, base_url: str) -> str:
        selectors = [
            "iframe[src*='flatchr.io']",
            "a[href*='flatchr.io/company/']",
            "a[href*='careers.flatchr.io']",
        ]

        for selector in selectors:
            for node in tree.css(selector):
                attr = "src" if "iframe" in selector else "href"
                candidate = absolute_url(base_url, node.attributes.get(attr))
                slug = self._extract_company_slug(candidate)
                if slug:
                    return f"https://careers.flatchr.io/fr/company/{slug}/"

        return self.FLATCHR_COMPANY_FALLBACK_URL

    def _extract_company_slug(self, url: str | None) -> str | None:
        if not url:
            return None

        match = self.COMPANY_SLUG_RE.search(url)
        if not match:
            return None

        slug = normalize_spaces(match.group("slug"))
        return slug or None

    def _canonicalize_vacancy_url(self, url: str | None) -> str | None:
        if not url:
            return None

        parsed = urlsplit(url)
        path = parsed.path.rstrip("/")

        if path.endswith("/apply"):
            path = path[: -len("/apply")]

        if not path:
            return None

        if path.startswith("/vacancy/"):
            path = "/fr/company/ctifl" + path
        elif path.startswith("/company/"):
            path = "/fr" + path
        elif path.startswith("/en/company/"):
            path = "/fr/company/" + path.split("/company/", 1)[1]
        elif not path.startswith("/fr/company/"):
            return None

        return urlunsplit(("https", "careers.flatchr.io", f"{path}/", "", ""))

    def _build_application_url(self, url: str) -> str:
        canonical = self._canonicalize_vacancy_url(url) or url
        return canonical.rstrip("/") + "/apply/"

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

    def _extract_header_lines(self, lines: list[str], title: str) -> list[str]:
        start_index = 0
        title_lower = title.lower()

        for idx, line in enumerate(lines):
            if line.lower() == title_lower:
                start_index = idx + 1
                break

        header_lines: list[str] = []
        for line in lines[start_index : start_index + 12]:
            clean = self._clean_line(line)
            lower = clean.lower()
            if not clean:
                continue
            if lower in self.NOISE_LINES:
                continue
            if lower in self.HEADER_STOP_MARKERS:
                break
            header_lines.append(clean)

        return header_lines

    def _extract_location(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            clean = self._clean_line(line)
            if not clean:
                continue

            if self.DATE_RE.search(clean):
                continue
            if self._infer_contract_type(clean):
                continue

            zip_match = self.ZIP_RE.search(clean)
            if zip_match:
                return zip_match.group(0)

        return None

    def _is_city_candidate(self, value: str | None) -> bool:
        if not value:
            return False

        value = self._clean_line(value).strip(" ,;:-–|")
        if not value:
            return False

        low = value.lower()
        if low in {"france"}:
            return False

        if self.DATE_RE.search(value):
            return False

        if self.ZIP_RE.search(value):
            return False

        if self._infer_contract_type(value):
            return False

        if re.fullmatch(r"[,;:\-–|/\\\(\)\[\]\{\}\.]+", value):
            return False

        if not re.search(r"[A-Za-zÀ-ÿŒœ\-']", value):
            return False

        return True

    def _extract_city_from_header(
        self,
        header_lines: list[str],
        location_text: str | None,
    ) -> str | None:
        for idx, line in enumerate(header_lines):
            clean = self._clean_line(line)
            if not clean:
                continue

            zip_match = self.ZIP_RE.search(clean)
            if not zip_match:
                continue

            before_zip = clean[: zip_match.start()].strip(" ,;:-–|")
            if self._is_city_candidate(before_zip):
                city = normalize_spaces(before_zip)
                return city or None

            for j in range(idx - 1, -1, -1):
                candidate = self._clean_line(header_lines[j]).strip(" ,;:-–|")
                if self._is_city_candidate(candidate):
                    city = normalize_spaces(candidate)
                    return city or None

            return None

        return None

    def _extract_contract_type(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            contract = self._infer_contract_type(line)
            if contract:
                return contract
        return None

    def _extract_posted_raw(self, header_lines: list[str]) -> str | None:
        for line in header_lines:
            if self.DATE_RE.search(line):
                return line
        return None

    def _parse_first_date(self, raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None

        match = self.DATE_RE.search(raw_value)
        if not match:
            return None

        try:
            return datetime.strptime(match.group(1), "%d/%m/%Y")
        except ValueError:
            return None

    def _extract_description(self, lines: list[str], title: str) -> str | None:
        start_index: int | None = None

        for idx, line in enumerate(lines):
            if line.lower() == "description":
                start_index = idx
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
            if lower in {"retour aux offres", "partager sur :", "partager sur"}:
                continue
            kept.append(line)

        description = "\n\n".join(kept).strip()
        return description or None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None

        low = normalize_spaces(text)
        if not low:
            return None
        low = low.lower()

        if "contrat de mission" in low:
            return "contrat de mission"
        if "alternance" in low or "apprentissage" in low:
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
        if any(token in title_low for token in ["alternance", "apprentissage", "alternant"]):
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
            "offre terminée" in blob
            or "offre terminee" in blob
            or "cette offre n'est plus disponible" in blob
        )

    def _node_text(self, tree, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if node:
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text:
                    return text
        return None