from __future__ import annotations

import html
import re
import unicodedata
from urllib.parse import quote

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import content_hash, html_tree, normalize_spaces, stable_offer_key
from app.models import NormalizedOffer


class Inov3ptConnector(BaseConnector):
    TITLE_PREFIX_RE = re.compile(r"^poste\s+d[eu]'|^poste\s+de\s+|^poste\s+d’", re.IGNORECASE)
    DATE_RANGE_RE = re.compile(r"^[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)?\s+[0-9]{4}$")
    FOOTER_RE = re.compile(r"^institut technique agricole qualifi", re.IGNORECASE)

    def __init__(self, source) -> None:
        super().__init__(source)
        self._items_by_url: dict[str, dict[str, object]] = {}
        self._normalized_html: str = ""

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)
        self._normalized_html = self._normalize_for_search(html.unescape(response.text))

        items = self._extract_items(lines)
        self._items_by_url = {}

        urls: list[str] = []
        for item in items:
            title = item.get("title")
            if not title:
                continue
            anchor = quote(self._slugify_fragment(str(title)))
            url = f"{self.source.jobs_url}#{anchor}"
            item["source_url"] = url
            item["application_url"] = url
            self._items_by_url[url] = item
            urls.append(url)

        return urls

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        if not self._items_by_url:
            self.discover_offer_urls(client)
        return self._items_by_url.get(url)

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre inov3PT"
        source_url = str(raw_item["source_url"])

        return NormalizedOffer(
            source_slug=self.source.slug,
            source_offer_key=stable_offer_key(source_url, None, None),
            source_url=source_url,
            application_url=str(raw_item.get("application_url") or source_url),
            title=str(title),
            organization=self.source.name,
            location_text=str(raw_item.get("location_text")) if raw_item.get("location_text") else None,
            city=str(raw_item.get("city")) if raw_item.get("city") else None,
            region=None,
            country="France",
            contract_type=str(raw_item.get("contract_type")) if raw_item.get("contract_type") else None,
            offer_type=str(raw_item.get("offer_type")) if raw_item.get("offer_type") else None,
            remote_mode=None,
            posted_at=None,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash([
                source_url,
                str(title),
                str(raw_item.get("contract_type")),
                str(raw_item.get("offer_type")),
                str(raw_item.get("is_filled")),
            ]),
            raw_payload=raw_item,
        )

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

    def _extract_items(self, lines: list[str]) -> list[dict[str, object]]:
        items: list[tuple[str, list[str]]] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            low = line.lower()

            if self.FOOTER_RE.match(low):
                break

            if low == "stages":
                # section historique 2023 à ignorer
                break

            if self._is_position_title(line):
                title = line
                if i + 1 < n and self._is_title_continuation(lines[i + 1]):
                    title = normalize_spaces(f"{title} {lines[i + 1]}")
                    i += 1
                extras: list[str] = []
                j = i + 1
                while j < n and not self._starts_new_item(lines[j]):
                    if self.FOOTER_RE.match(lines[j].lower()) or lines[j].lower() == "stages":
                        break
                    extras.append(lines[j])
                    j += 1
                items.append((title, extras))
                i = j
                continue

            if low == "offre de stage":
                extras: list[str] = []
                title = "Offre de stage"
                if i + 1 < n and self.DATE_RANGE_RE.match(lines[i + 1]):
                    title = f"Offre de stage - {lines[i + 1]}"
                    extras.append(lines[i + 1])
                    i += 1
                j = i + 1
                while j < n and not self._starts_new_item(lines[j]):
                    if self.FOOTER_RE.match(lines[j].lower()) or lines[j].lower() == "stages":
                        break
                    extras.append(lines[j])
                    j += 1
                items.append((title, extras))
                i = j
                continue

            i += 1

        normalized: list[dict[str, object]] = []
        for title, extras in items:
            title = normalize_spaces(title)
            if not title or title.lower() == "stages":
                continue

            extras = [normalize_spaces(x) for x in extras if normalize_spaces(x)]
            description_text = "\n\n".join(extras).strip() or None
            contract_type = self._infer_contract_type(title, description_text or "")
            offer_type = self._infer_offer_type(title, contract_type)
            is_filled = self._detect_filled_status(title, extras)

            normalized.append(
                {
                    "title": title,
                    "description_text": description_text,
                    "location_text": None,
                    "city": None,
                    "region": None,
                    "country": "France",
                    "contract_type": contract_type,
                    "offer_type": offer_type,
                    "remote_mode": None,
                    "posted_at": None,
                    "raw_posted_at": None,
                    "is_filled": is_filled,
                    "listing_status": "filled" if is_filled else "open",
                }
            )

        return normalized

    def _is_position_title(self, line: str) -> bool:
        return bool(self.TITLE_PREFIX_RE.match(line.strip()))

    def _is_title_continuation(self, line: str) -> bool:
        low = line.lower()
        if self._starts_new_item(line):
            return False
        if self.DATE_RANGE_RE.match(line):
            return False
        return low[:1].islower()

    def _starts_new_item(self, line: str) -> bool:
        low = line.lower()
        return (
            self._is_position_title(line)
            or low == "offre de stage"
            or low == "stages"
            or self.FOOTER_RE.match(low) is not None
        )

    def _detect_filled_status(self, title: str, extras: list[str]) -> bool:
        if not self._normalized_html:
            return False
        key = self._normalize_for_search(title)
        positions = []
        if key:
            pos = self._normalized_html.find(key)
            if pos >= 0:
                positions.append(pos)
        for extra in extras[:2]:
            extra_key = self._normalize_for_search(extra)
            if extra_key:
                pos = self._normalized_html.find(extra_key)
                if pos >= 0:
                    positions.append(pos)
        if not positions:
            return False
        pos = min(positions)
        nearby = self._normalized_html[pos : pos + 2500]
        return (
            "logo offre pourvue" in nearby
            or "offre pourvue" in nearby
            or "recrutement termine" in nearby
        )

    def _normalize_for_search(self, value: str) -> str:
        value = html.unescape(value)
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower().replace("’", "'")
        value = re.sub(r"\s+", " ", value)
        return value

    def _slugify_fragment(self, value: str) -> str:
        value = self._normalize_for_search(value)
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "offre"

    def _infer_contract_type(self, title: str, description: str) -> str | None:
        low = f"{title} {description}".lower()
        if "service civique" in low:
            return "service civique"
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str, contract_type: str | None) -> str | None:
        if contract_type in {"cdi", "cdd", "service civique"}:
            return "emploi"
        if contract_type == "alternance":
            return "alternance"
        if contract_type == "stage":
            return "stage"
        if title.lower().startswith("offre de stage"):
            return "stage"
        return "emploi"
