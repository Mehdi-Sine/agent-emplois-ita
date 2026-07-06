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
    TITLE_RE = re.compile(r"^poste\s+(?:de|d['’])", re.IGNORECASE)
    DATE_RANGE_RE = re.compile(
        r"^(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)"
        r"(?:\s*[-–]\s*"
        r"(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre))?"
        r"\s+\d{4}$",
        re.IGNORECASE,
    )
    FOOTER_RE = re.compile(r"^institut technique agricole qualifi", re.IGNORECASE)
    FILLED_RE = re.compile(r"(offre pourvue|recrutement termin[ée])", re.IGNORECASE)

    def __init__(self, source) -> None:
        super().__init__(source)
        self._items_by_url: dict[str, dict[str, object]] = {}
        self._normalized_html: str = ""

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()

        self._normalized_html = self._normalize_for_search(html.unescape(response.text))

        tree = html_tree(response.text)
        stream = self._extract_stream(tree)
        items = self._extract_items(stream)

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
            content_hash=content_hash(
                [
                    source_url,
                    str(title),
                    str(raw_item.get("contract_type")),
                    str(raw_item.get("offer_type")),
                    str(raw_item.get("is_filled")),
                ]
            ),
            raw_payload=raw_item,
        )

    # -------------------------------------------------------------------------
    # STREAM EXTRACTION
    # -------------------------------------------------------------------------

    def _extract_stream(self, tree) -> list[dict[str, str]]:
        stream: list[dict[str, str]] = []

        for node in tree.css("[data-testid='richTextElement'], img[alt]"):
            alt = normalize_spaces(node.attributes.get("alt") or "")
            if alt:
                stream.append({"kind": "badge", "text": alt})
                continue

            text = normalize_spaces(node.text(separator=" ", strip=True))
            if not text:
                continue

            text = self._clean_text(text)
            if not text:
                continue

            stream.append({"kind": "text", "text": text})

        return stream

    def _clean_text(self, value: str) -> str:
        value = normalize_spaces(value)
        if not value:
            return ""

        low = value.lower()

        if low in {"recrutements", "recrutement"}:
            return ""
        if low.startswith("poster"):
            return ""
        if value.startswith("#comp-"):
            return ""
        if "lire la vidéo" in low or "lire la video" in low:
            return ""

        return value

    # -------------------------------------------------------------------------
    # ITEM EXTRACTION
    # -------------------------------------------------------------------------

    def _extract_items(self, stream: list[dict[str, str]]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        i = 0
        n = len(stream)

        while i < n:
            token = stream[i]

            if token["kind"] != "text":
                i += 1
                continue

            text = token["text"]
            low = text.lower()

            if self.FOOTER_RE.match(low):
                break

            # On ignore la section historique en bas du site
            if low == "stages":
                break

            if self._is_offer_start(text):
                stage_mode = low == "offre de stage"
                title = text
                extras: list[str] = []
                badge_filled = False

                j = i + 1

                if stage_mode and j < n and stream[j]["kind"] == "text" and self._is_date_range(stream[j]["text"]):
                    title = f"Offre de stage - {stream[j]['text']}"
                    j += 1

                while j < n:
                    nxt = stream[j]

                    if nxt["kind"] == "badge":
                        if self._is_filled_badge(nxt["text"]):
                            badge_filled = True
                        j += 1
                        continue

                    nxt_text = nxt["text"]
                    nxt_low = nxt_text.lower()

                    if self.FOOTER_RE.match(nxt_low):
                        break
                    if nxt_low == "stages":
                        break
                    if self._is_offer_start(nxt_text):
                        break

                    if stage_mode and self._is_date_range(nxt_text) and title.lower() == "offre de stage":
                        title = f"Offre de stage - {nxt_text}"
                    else:
                        if self._keep_as_description(nxt_text):
                            extras.append(nxt_text)

                    j += 1

                is_filled = badge_filled or self._detect_filled_status(title)
                contract_type = self._infer_contract_type(title, extras)
                offer_type = self._infer_offer_type(title, contract_type)
                description_text = "\n\n".join(extras).strip() or None

                items.append(
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

                i = j
                continue

            i += 1

        return items

    def _is_offer_start(self, text: str) -> bool:
        low = text.lower()
        return self._is_position_title(text) or low == "offre de stage"

    def _is_position_title(self, text: str) -> bool:
        return bool(self.TITLE_RE.match(text.strip()))

    def _is_date_range(self, text: str) -> bool:
        return bool(self.DATE_RANGE_RE.match(text.strip()))

    def _is_filled_badge(self, text: str) -> bool:
        return bool(self.FILLED_RE.search(text))

    def _keep_as_description(self, text: str) -> bool:
        low = text.lower()

        if not text:
            return False
        if self._is_offer_start(text):
            return False
        if low == "stages":
            return False
        if self.FOOTER_RE.match(low):
            return False
        if low.startswith("poster"):
            return False
        if "lire la vidéo" in low or "lire la video" in low:
            return False

        return True

    # -------------------------------------------------------------------------
    # FILLED STATUS
    # -------------------------------------------------------------------------

    def _detect_filled_status(self, title: str) -> bool:
        if not self._normalized_html:
            return False

        key = self._normalize_for_search(title)
        if not key:
            return False

        positions = [m.start() for m in re.finditer(re.escape(key), self._normalized_html)]
        if not positions:
            return False

        for pos in positions[:3]:
            nearby = self._normalized_html[pos : pos + 2500]
            next_offer = self._find_next_offer_marker(nearby)
            if next_offer is not None:
                nearby = nearby[:next_offer]
            if self._contains_filled_marker(nearby):
                return True

        return False

    def _find_next_offer_marker(self, text: str) -> int | None:
        markers = [
            match.start()
            for match in re.finditer(r"\b(poste\s+(?:de|d['’])|offre\s+de\s+stage)\b", text, flags=re.IGNORECASE)
            if match.start() > 20
        ]
        return min(markers) if markers else None

    def _contains_filled_marker(self, text: str) -> bool:
        normalized = self._normalize_for_search(text)
        return any(
            marker in normalized
            for marker in [
                "logo offre pourvue",
                "offre pourvue",
                "offre-pourvue",
                "offre pourvue.png",
                "recrutement termine",
            ]
        )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _normalize_for_search(self, value: str) -> str:
        value = html.unescape(value)
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower().replace("’", "'")
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _slugify_fragment(self, value: str) -> str:
        value = self._normalize_for_search(value)
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "offre"

    def _infer_contract_type(self, title: str, extras: list[str]) -> str | None:
        low = " ".join([title] + extras).lower()
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
        if "stage" in title.lower():
            return "stage"
        return "emploi"