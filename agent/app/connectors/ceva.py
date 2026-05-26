from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO

from httpx import Client

from app.connectors.base import BaseConnector
from app.connectors.common import absolute_url, content_hash, html_tree, normalize_spaces, stable_offer_key
from app.models import NormalizedOffer


class CevaConnector(BaseConnector):
    MARKERS = {"OFFRE D’EMPLOI :", "OFFRE D'EMPLOI :", "OFFRE D’EMPLOI", "OFFRE D'EMPLOI"}

    def discover_offer_urls(self, client: Client) -> list[str]:
        response = client.get(str(self.source.jobs_url))
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)
        title = self._extract_title(lines)
        return [str(response.url)] if title else []

    def parse_offer(self, client: Client, url: str) -> dict[str, object] | None:
        response = client.get(url)
        response.raise_for_status()
        tree = html_tree(response.text)
        lines = self._extract_lines(tree)

        title = self._extract_title(lines)
        if not title:
            return None

        application_url = self._extract_application_url(tree, str(response.url), title)
        page_description = self._extract_description(lines, title)
        doc_description = self._fetch_offer_document_text(client, application_url)
        description_text = doc_description or page_description
        contract_type = self._infer_contract_type(" ".join(filter(None, [title, description_text])))
        offer_type = self._infer_offer_type(title, contract_type, description_text)
        location_text, city, region = self._infer_location(title, description_text)
        is_filled = self._is_filled(title, description_text)

        return {
            "source_url": url,
            "application_url": application_url or "mailto:algue@ceva.fr",
            "title": title,
            "description_text": description_text,
            "location_text": location_text,
            "city": city,
            "region": region,
            "country": "France",
            "contract_type": contract_type,
            "offer_type": offer_type,
            "remote_mode": None,
            "posted_at": None,
            "raw_posted_at": None,
            "is_filled": is_filled,
            "listing_status": "filled" if is_filled else "open",
        }

    def normalize_offer(self, raw_item: dict[str, object]) -> NormalizedOffer:
        title = raw_item.get("title") or "Offre CEVA"
        location = raw_item.get("location_text")
        source_url = str(raw_item["source_url"])

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
            posted_at=None,
            description_text=str(raw_item.get("description_text")) if raw_item.get("description_text") else None,
            content_hash=content_hash([
                source_url,
                str(title),
                str(location),
                str(raw_item.get("contract_type")),
                str(raw_item.get("offer_type")),
                str(raw_item.get("listing_status")),
            ]),
            raw_payload=raw_item,
        )

    def _extract_lines(self, tree) -> list[str]:
        body = tree.body
        text = body.text(separator="\n", strip=True) if body else tree.text(separator="\n", strip=True)
        return [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    def _extract_title(self, lines: list[str]) -> str | None:
        for idx, line in enumerate(lines):
            if line in self.MARKERS and idx + 1 < len(lines):
                candidate = normalize_spaces(lines[idx + 1])
                if candidate:
                    return candidate
        return None

    def _extract_description(self, lines: list[str], title: str) -> str | None:
        kept: list[str] = []
        started = False
        for line in lines:
            if line == title:
                started = True
                continue
            if not started:
                continue
            if line.startswith("Partagez cette page") or line.startswith("Centre d'Étude") or line.startswith("Centre d'Etude"):
                break
            if line in self.MARKERS:
                continue
            kept.append(line)
        text = "\n\n".join(kept).strip()
        return text or None


    def _extract_application_url(self, tree, page_url: str, title: str) -> str | None:
        title_low = title.lower()
        for node in tree.css("a[href]"):
            href = node.attributes.get("href")
            text = normalize_spaces(node.text(separator=" ", strip=True)) or ""
            text_low = text.lower()
            if not href:
                continue
            is_doc = any(marker in href.lower() for marker in [".pdf", ".doc", ".docx"])
            if is_doc and (text_low in title_low or title_low in text_low or "offre" in text_low):
                return absolute_url(page_url, href)
        for node in tree.css("a[href]"):
            href = node.attributes.get("href")
            if href and any(marker in href.lower() for marker in [".pdf", ".doc", ".docx"]):
                return absolute_url(page_url, href)
        return None

    def _fetch_offer_document_text(self, client: Client, application_url: str | None) -> str | None:
        if not application_url:
            return None
        try:
            response = client.get(application_url)
            response.raise_for_status()
        except Exception:
            return None

        content_type = (response.headers.get("content-type") or "").lower()
        if "html" in content_type:
            tree = html_tree(response.text)
            lines = self._extract_lines(tree)
            return "\n\n".join(lines).strip() or None

        if "pdf" in content_type or application_url.lower().endswith(".pdf"):
            return self._extract_pdf_text(response.content)

        text = response.text.strip()
        return text or None


    def _extract_pdf_text(self, content: bytes) -> str | None:
        if not content:
            return None
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            pages: list[str] = []
            for page in reader.pages:
                text = normalize_spaces(page.extract_text() or "")
                if text:
                    pages.append(text)
            joined = "\n\n".join(pages).strip()
            return joined or None
        except Exception:
            return None

    def _infer_contract_type(self, text: str | None) -> str | None:
        if not text:
            return None
        low = normalize_spaces(text).lower()
        if "alternance" in low or "apprentissage" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        if "cdi" in low:
            return "cdi"
        if "cdd" in low:
            return "cdd"
        return None

    def _infer_offer_type(self, title: str | None, contract_type: str | None, description_text: str | None) -> str | None:
        contract_low = (contract_type or "").lower()
        if contract_low in {"cdi", "cdd"}:
            return "emploi"
        if contract_low == "alternance":
            return "alternance"
        if contract_low == "stage":
            return "stage"
        low = " ".join(filter(None, [title, description_text])).lower()
        if "alternance" in low:
            return "alternance"
        if "stage" in low:
            return "stage"
        return "emploi"

    def _infer_location(self, title: str | None, description_text: str | None) -> tuple[str | None, str | None, str | None]:
        text = "\n".join(filter(None, [title, description_text]))
        match = re.search(r"(?:bas[ée] à|poste est bas[ée] à)\s+([A-Za-zÀ-ÿ\- ]+)\s*\((\d{2})\)", text, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"\b(\d{5})\s+([A-Za-zÀ-ÿ\- ]{2,})\b", text)
            if match:
                postal, city = match.group(1), normalize_spaces(match.group(2))
                dept = postal[:2]
                return f"{city} ({postal})", city, self._region_from_dept(dept)
            return "Pleubian (22610)", "Pleubian", "Bretagne"
        city = normalize_spaces(match.group(1))
        dept = match.group(2)
        return f"{city} ({dept})", city, self._region_from_dept(dept)

    def _region_from_dept(self, dept: str | None) -> str | None:
        mapping = {"22": "Bretagne", "29": "Bretagne", "35": "Bretagne", "56": "Bretagne", "75": "Île-de-France", "77": "Île-de-France", "78": "Île-de-France", "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France", "94": "Île-de-France", "95": "Île-de-France"}
        return mapping.get(dept or "")

    def _is_filled(self, title: str | None, description_text: str | None) -> bool:
        text = " ".join(filter(None, [title, description_text])).lower()
        return any(marker in text for marker in ["poste pourvu", "offre close", "recrutement clos", "candidatures closes"])
