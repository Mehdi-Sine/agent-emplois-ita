from __future__ import annotations

import re
from datetime import datetime
from hashlib import sha256
from typing import Iterable
from urllib.parse import urljoin

from dateutil import parser as dateparser
from selectolax.parser import HTMLParser


def html_tree(content: str) -> HTMLParser:
    return HTMLParser(content)


def absolute_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href.strip())


def normalize_spaces(value: str | None) -> str | None:
    if value is None:
        return None
    clean = re.sub(r"\s+", " ", value).strip()
    return clean or None


def node_text(tree: HTMLParser, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = tree.css_first(selector)
        if node:
            text = normalize_spaces(node.text(separator=" ", strip=True))
            if text:
                return text
    return None


def node_texts(tree: HTMLParser, selectors: list[str]) -> list[str]:
    results: list[str] = []
    for selector in selectors:
        for node in tree.css(selector):
            text = normalize_spaces(node.text(separator=" ", strip=True))
            if text:
                results.append(text)
    return results


def find_offer_links(tree: HTMLParser, base_url: str, selectors: list[str]) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for selector in selectors:
        for node in tree.css(selector):
            href = node.attributes.get("href")
            url = absolute_url(base_url, href)
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            links.append(url)
    return links


def extract_first_matching_text(items: Iterable[str], patterns: list[str]) -> str | None:
    lowered = [(item or "").strip() for item in items]
    for item in lowered:
        item_low = item.lower()
        if any(pattern in item_low for pattern in patterns):
            return item
    return None


def parse_date_guess(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        return dateparser.parse(raw_value, dayfirst=True, fuzzy=True)
    except Exception:
        return None


def classify_offer_type(text_blob: str | None) -> str | None:
    if not text_blob:
        return None
    text = text_blob.lower()
    if "stage" in text:
        return "stage"
    if "alternance" in text or "apprentissage" in text:
        return "alternance"
    if "thèse" in text or "doctorat" in text:
        return "thèse"
    if "cdd" in text or "cdi" in text or "emploi" in text or "poste" in text:
        return "emploi"
    return None


def classify_contract_type(text_blob: str | None) -> str | None:
    if not text_blob:
        return None
    text = text_blob.lower()
    for marker in ["cdi", "cdd", "alternance", "stage", "thèse", "intérim"]:
        if marker in text:
            return marker
    return None


def stable_offer_key(url: str, title: str | None, location: str | None) -> str:
    base = " | ".join([(url or "").strip(), (title or "").strip(), (location or "").strip()])
    return sha256(base.encode("utf-8")).hexdigest()[:24]


def content_hash(parts: list[str | None]) -> str:
    normalized = " | ".join([(part or "").strip() for part in parts])
    return sha256(normalized.encode("utf-8")).hexdigest()


def description_from_selectors(tree: HTMLParser, selectors: list[str]) -> str | None:
    blocks: list[str] = []
    for selector in selectors:
        for node in tree.css(selector):
            text = normalize_spaces(node.text(separator=" ", strip=True))
            if text:
                blocks.append(text)
        if blocks:
            break
    if not blocks:
        return None
    return normalize_spaces("\n\n".join(blocks))
