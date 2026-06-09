from __future__ import annotations

import re
from typing import Any

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import (
    absolute_url,
    content_hash,
    description_from_selectors,
    html_tree,
    node_text,
    normalize_spaces,
    parse_date_guess,
    stable_offer_key,
)
from app.models import NormalizedOffer


class TerresInoviaConnector(BaseConnector):
    READER_URL_PREFIX = "https://r.jina.ai/http://r.jina.ai/http://"

    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    }
    JOB_PATH_RE = re.compile(r"/fr/institut/carrieres/[^/?#]+/?$")
    PUBLISHED_RE = re.compile(r"Publié le\s+([0-9]{1,2}\s+[^\|\n]+?\s+[0-9]{4})", re.IGNORECASE)

    FRENCH_REGIONS = (
        "Auvergne-Rhône-Alpes",
        "Bourgogne-Franche-Comté",
        "Bretagne",
        "Centre-Val de Loire",
        "Corse",
        "Grand Est",
        "Hauts-de-France",
        "Île-de-France",
        "Ile-de-France",
        "Normandie",
        "Nouvelle-Aquitaine",
        "Occitanie",
        "Pays de la Loire",
        "Provence-Alpes-Côte d’Azur",
        "Provence-Alpes-Côte d'Azur",
    )

    def __init__(self, source) -> None:
        super().__init__(source)
        self._listing_index: dict[str, dict[str, Any]] = {}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = self._get_with_fallback(client, str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)

        offer_urls: list[str] = []
        seen: set[str] = set()
        listing_index: dict[str, dict[str, Any]] = {}

        for card in tree.css(".bk-remontees-offres__card"):
            link = card.css_first("h3.like-h4 a[href]")
            if not link:
                continue

            href = link.attributes.get("href")
            url = absolute_url(str(response.url), href)
            if not url:
                continue
            if not self.JOB_PATH_RE.search(url):
                continue
            if url.rstrip("/") == str(self.source.jobs_url).rstrip("/"):
                continue
            if url in seen:
                continue

            title = normalize_spaces(link.text(separator=" ", strip=True))
            if not title:
                continue

            date_node = card.css_first(".bk-remontees-offres__date")
            posted_at_raw = (
                normalize_spaces(date_node.text(separator=" ", strip=True)) if date_node else None
            )

            teaser_node = card.css_first(".bk-remontees-offres__teaser")
            teaser = (
                normalize_spaces(teaser_node.text(separator=" ", strip=True)) if teaser_node else None
            )

            tags: list[str] = []
            for node in card.css(".tag-item"):
                text = normalize_spaces(node.text(separator=" ", strip=True))
                if text:
                    tags.append(text)

            badge_texts: list[str] = []
            location_text: str | None = None

            for badge in card.css(".bk-remontees-offres__btn"):
                text = normalize_spaces(badge.text(separator=" ", strip=True))
                if not text:
                    continue
                if badge.css_first(".icon-pin"):
                    location_text = text
                else:
                    badge_texts.append(text)

            if not location_text:
                location_text = self._extract_location_from_title(title)

            listing_index[url] = {
                "source_url": url,
                "application_url": url,
                "title": title,
                "description_text": teaser,
                "location_text": location_text,
                "posted_at": parse_date_guess(posted_at_raw),
                "posted_at_raw": posted_at_raw,
                "tag_values": tags,
                "extra_meta": badge_texts,
            }

            seen.add(url)
            offer_urls.append(url)

        if not offer_urls:
            offer_urls, listing_index = self._discover_offer_urls_from_text(str(response.url), response.text)

        self._listing_index = listing_index
        return offer_urls

    def parse_offer(self, client: Client, url: str) -> dict[str, Any] | None:
        seed = dict(self._listing_index.get(url, {}))
        if not seed:
            return None

        title = seed.get("title")
        description_text = seed.get("description_text")
        posted_at = seed.get("posted_at")
        location_text = seed.get("location_text")
        region = None

        detail_text = ""
        try:
            response = self._get_with_fallback(client, url)
            response.raise_for_status()
            tree = html_tree(response.text)

            title = node_text(tree, ["h1"]) or title

            detail_description = self._extract_detail_description(tree)
            if detail_description:
                description_text = detail_description

            body_node = tree.body
            if body_node:
                detail_text = body_node.text(separator="\n", strip=True)
            else:
                detail_text = tree.text(separator="\n", strip=True)

            if not posted_at:
                posted_at = self._extract_published_date(detail_text)

            region = self._extract_region(detail_text)

            if not location_text:
                location_text = self._extract_location_from_detail(detail_text)

            if not location_text:
                location_text = self._extract_location_from_title(title)

        except Exception:
            # On garde les métadonnées de la page liste, déjà fiables.
            pass

        contract_type = self._infer_contract_type(
            title=title,
            tags=seed.get("tag_values", []),
            extra_meta=seed.get("extra_meta", []),
            detail_text=detail_text,
        )
        offer_type = self._infer_offer_type(
            title=title,
            tags=seed.get("tag_values", []),
            extra_meta=seed.get("extra_meta", []),
            detail_text=detail_text,
        )

        if not title:
            return None

        return {
            "source_url": url,
            "application_url": seed.get("application_url") or url,
            "title": title,
            "description_text": description_text,
            "location_text": location_text,
            "city": location_text,
            "region": region,
            "contract_type": contract_type,
            "offer_type": offer_type,
            "posted_at": posted_at,
            "raw_listing_tags": seed.get("tag_values", []),
            "raw_listing_extra_meta": seed.get("extra_meta", []),
            "raw_posted_at": seed.get("posted_at_raw"),
        }

    def normalize_offer(self, raw_item: dict[str, Any]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre Terres Inovia"
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
            contract_type=raw_item.get("contract_type"),
            offer_type=raw_item.get("offer_type"),
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
                ]
            ),
            raw_payload=raw_item,
        )

    def _extract_detail_description(self, tree) -> str | None:
        text = description_from_selectors(
            tree,
            [
                "article .field--name-body",
                "article .node__content",
                "article .layout-content",
                "main article",
                "article",
            ],
        )
        if not text:
            return None

        lowered = text.lower()
        stop_markers = [
            "vous souhaitez postuler à cette offre",
            "mon panier",
            "mot de passe oublié",
            "créer un compte",
        ]
        for marker in stop_markers:
            idx = lowered.find(marker)
            if idx != -1:
                text = text[:idx].strip()
                break

        return normalize_spaces(text)

    def _extract_published_date(self, detail_text: str | None):
        if not detail_text:
            return None
        match = self.PUBLISHED_RE.search(detail_text)
        if not match:
            return None
        return parse_date_guess(match.group(1))

    def _extract_region(self, detail_text: str | None) -> str | None:
        if not detail_text:
            return None
        compact = normalize_spaces(detail_text) or ""
        for region in self.FRENCH_REGIONS:
            if region.lower() in compact.lower():
                return region
        return None

    def _extract_location_from_detail(self, detail_text: str | None) -> str | None:
        if not detail_text:
            return None

        patterns = [
            r"## Le site\s+###\s+(.+?)\s+Adresse",
            r"Le site\s+(.+?)\s+Adresse",
        ]
        for pattern in patterns:
            match = re.search(pattern, detail_text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return normalize_spaces(match.group(1))
        return None

    def _extract_location_from_title(self, title: str | None) -> str | None:
        if not title:
            return None

        patterns = [
            r"\((?P<loc>[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]+?)\s*-\s*\d{2}\)\s*$",
            r"[-–]\s*(?P<loc>[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]+?)\s*\(\d{2}\)\s*$",
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return normalize_spaces(match.group("loc"))
        return None

    def _infer_contract_type(
        self,
        title: str | None,
        tags: list[str],
        extra_meta: list[str],
        detail_text: str | None,
    ) -> str | None:
        blob = " ".join(
            [
                title or "",
                *(tags or []),
                *(extra_meta or []),
                detail_text or "",
            ]
        ).lower()

        if "apprentissage" in blob:
            return "apprentissage"
        if "alternance" in blob:
            return "alternance"
        if "cdi" in blob:
            return "cdi"
        if "cdd" in blob:
            return "cdd"
        if "stage" in blob:
            return "stage"
        return None

    def _infer_offer_type(
        self,
        title: str | None,
        tags: list[str],
        extra_meta: list[str],
        detail_text: str | None,
    ) -> str | None:
        blob = " ".join(
            [
                title or "",
                *(tags or []),
                *(extra_meta or []),
                detail_text or "",
            ]
        ).lower()

        if "apprentissage" in blob or "alternance" in blob:
            return "alternance"
        if "stage" in blob:
            return "stage"
        return "emploi"

    def _discover_offer_urls_from_text(self, base_url: str, text: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
        lines = [normalize_spaces(line) for line in text.splitlines()]
        lines = [line for line in lines if line]

        offer_urls: list[str] = []
        listing_index: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()

        for idx, line in enumerate(lines):
            parsed = self._extract_markdown_offer_link(line, base_url)
            if not parsed:
                continue

            title, url = parsed
            if not self.JOB_PATH_RE.search(url) or url in seen:
                continue

            window = lines[max(0, idx - 3) : min(len(lines), idx + 8)]
            posted_at_raw = self._extract_text_posted_at(window)
            location_text = self._extract_text_location(title, window)
            teaser = self._extract_text_teaser(lines[idx + 1 : idx + 6])
            tags = self._extract_text_tags(title, window)

            listing_index[url] = {
                "source_url": url,
                "application_url": url,
                "title": title,
                "description_text": teaser,
                "location_text": location_text,
                "posted_at": parse_date_guess(posted_at_raw),
                "posted_at_raw": posted_at_raw,
                "tag_values": tags,
                "extra_meta": [],
            }
            seen.add(url)
            offer_urls.append(url)

        return offer_urls, listing_index

    def _extract_markdown_offer_link(self, line: str, base_url: str) -> tuple[str, str] | None:
        match = re.match(r"^#+\s*\[(?P<title>[^\]]+)\]\((?P<href>[^)]+)\)", line)
        if not match:
            match = re.match(r"^\*?\s*\[(?P<title>[^\]]+)\]\((?P<href>[^)]+)\)", line)
        if not match:
            return None

        title = normalize_spaces(match.group("title"))
        href = match.group("href")
        url = absolute_url(str(self.source.site_url), href) if href.startswith("/") else absolute_url(base_url, href)
        if not title or not url:
            return None
        return title, url

    def _extract_text_posted_at(self, lines: list[str]) -> str | None:
        for line in lines:
            match = re.search(r"\b\d{1,2}\s+[A-Za-zÀ-ÖØ-öø-ÿ]+\s+\d{4}\b", line)
            if match:
                return match.group(0)
        return None

    def _extract_text_location(self, title: str, lines: list[str]) -> str | None:
        title_location = self._extract_location_from_title(title)
        if title_location:
            return title_location

        for line in reversed(lines):
            if re.search(r"\b(CDI|CDD|Stage|apprentissage|mois)\b", line, re.IGNORECASE):
                continue
            if re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", line) and len(line) <= 80:
                return line
        return None

    def _extract_text_teaser(self, lines: list[str]) -> str | None:
        kept: list[str] = []
        for line in lines:
            if line.startswith("###") or re.search(r"\b\d{1,2}\s+[A-Za-zÀ-ÖØ-öø-ÿ]+\s+\d{4}\b", line):
                break
            if re.fullmatch(r"(CDI|CDD|Stage|apprentissage|\d+\s+mois)", line, flags=re.IGNORECASE):
                continue
            kept.append(line)
        return normalize_spaces(" ".join(kept))

    def _extract_text_tags(self, title: str, lines: list[str]) -> list[str]:
        tags: list[str] = []
        blob = " ".join([title, *lines])
        for tag in ["CDI", "CDD", "Stage", "apprentissage"]:
            if tag.lower() in blob.lower():
                tags.append(tag)
        return tags

    def _reader_url(self, url: str) -> str:
        return f"{self.READER_URL_PREFIX}{url}"

    def _get_with_fallback(self, client: Client, url: str):
        retry_headers = dict(self.BROWSER_HEADERS)
        retry_headers["Referer"] = str(self.source.site_url)

        urls = [url]
        slash_url = url if url.endswith("/") else f"{url}/"
        no_slash_url = url.rstrip("/")
        for candidate in [no_slash_url, slash_url]:
            if candidate not in urls:
                urls.append(candidate)

        last_response = None
        last_exc: Exception | None = None
        for candidate_url in urls:
            for kwargs in [{}, {"headers": retry_headers}]:
                try:
                    response = client.get(candidate_url, **kwargs)
                    last_response = response
                    if response.status_code != 403:
                        response.raise_for_status()
                        return response
                except Exception as exc:
                    last_exc = exc

        # Last-resort read-through fallback: keeps Terres Inovia from failing the
        # whole source run when the origin WAF blocks GitHub Actions IPs.
        try:
            reader_response = client.get(self._reader_url(no_slash_url), headers=retry_headers, timeout=45)
            reader_response.raise_for_status()
            return reader_response
        except Exception as exc:
            last_exc = exc

        if last_response is not None:
            last_response.raise_for_status()
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Impossible de récupérer {url}")
