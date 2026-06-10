#!/usr/bin/env python3
"""Generate a square LinkedIn PDF carousel for Terres Inovia job offers.

The PDF is intentionally generated with the Python standard library only so the
asset can be rebuilt in restricted CI environments without external packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

OUT = Path(__file__).with_name("terres-inovia-3-offres-linkedin-2026-06-10.pdf")
PAGE = 1080
MARGIN = 70

# Palette inspired by Terres Inovia's visual identity: agriculture greens,
# sunflower / oilseed yellow-orange accents, and warm off-white backgrounds.
COLORS = {
    "deep_green": (24, 83, 55),
    "green": (82, 154, 60),
    "light_green": (164, 205, 85),
    "yellow": (248, 181, 37),
    "orange": (232, 126, 39),
    "cream": (250, 247, 235),
    "ink": (38, 48, 44),
    "white": (255, 255, 255),
    "muted": (93, 112, 103),
}

CAREERS_URL = "terresinovia.fr/fr/institut/carrieres"


@dataclass(frozen=True)
class Offer:
    number: str
    title: str
    contract: str
    region: str
    location: str
    duration: str
    start: str
    published: str
    bullets: tuple[str, str, str]
    tag: str
    image: str
    url: str


OFFERS: tuple[Offer, ...] = (
    Offer(
        number="01",
        title="Ingénieur·e développement\n‘lutte ravageurs’",
        contract="CDD • 16 mois",
        region="Grand Est",
        location="Châlons-en-Champagne (51)",
        duration="Septembre 2026",
        start="40–46 k€ • statut cadre",
        published="Publié le 26 mai 2026",
        bullets=(
            "Réseaux expérimentaux en grandes parcelles",
            "Suivi ravageurs : colza, pois, lentille",
            "Projet PARSADA COLEOFAST & IPSEELON",
        ),
        tag="Terrain + data",
        image="insect_field",
        url="terresinovia.fr/.../chalons-en-champagne",
    ),
    Offer(
        number="02",
        title="Ingénieur·e développement\n‘lutte ravageurs’",
        contract="CDD • 16 mois",
        region="Centre-Val de Loire",
        location="Le Subdray (18)",
        duration="Septembre 2026",
        start="40–46 k€ • statut cadre",
        published="Publié le 26 mai 2026",
        bullets=(
            "Expérimentations terrain et prélèvements",
            "Synthèse de données et travail en équipe",
            "Déplacements sur réseaux de parcelles",
        ),
        tag="Innovation agricole",
        image="crop_network",
        url="terresinovia.fr/.../le-subdray-18",
    ),
    Offer(
        number="03",
        title="Stage M1 / césure\nnectar extrafloral féverole",
        contract="Stage • 4 mois",
        region="Pays de la Loire",
        location="Angers / Olivet-Ardon",
        duration="Septembre–décembre 2026",
        start="Biologie végétale • agroécologie",
        published="Publié le 21 mai 2026",
        bullets=(
            "Phénotypage de variétés de féverole",
            "Mesures nectar, sucre et croissance",
            "Analyse statistique et rapport de stage",
        ),
        tag="Biodiversité fonctionnelle",
        image="faba_lab",
        url="terresinovia.fr/.../nectar-extrafloral",
    ),
)


def rgb(name: str) -> str:
    r, g, b = COLORS[name]
    return f"{r/255:.4f} {g/255:.4f} {b/255:.4f}"


def esc(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("cp1252", "replace")


class PageBuilder:
    def __init__(self) -> None:
        self.parts: list[bytes] = []

    def raw(self, s: str | bytes) -> None:
        self.parts.append(s if isinstance(s, bytes) else s.encode("ascii"))

    def fill(self, name: str) -> None:
        self.raw(f"{rgb(name)} rg\n")

    def stroke(self, name: str, width: int = 2) -> None:
        self.raw(f"{rgb(name)} RG {width} w\n")

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None = None, stroke: str | None = None, sw: int = 2) -> None:
        if fill:
            self.fill(fill)
        if stroke:
            self.stroke(stroke, sw)
        op = "B" if fill and stroke else "f" if fill else "S"
        self.raw(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re {op}\n")

    def circle(self, x: float, y: float, r: float, fill: str | None = None, stroke: str | None = None, sw: int = 2) -> None:
        k = 0.5522847498 * r
        if fill:
            self.fill(fill)
        if stroke:
            self.stroke(stroke, sw)
        self.raw(
            f"{x+r:.1f} {y:.1f} m {x+r:.1f} {y+k:.1f} {x+k:.1f} {y+r:.1f} {x:.1f} {y+r:.1f} c "
            f"{x-k:.1f} {y+r:.1f} {x-r:.1f} {y+k:.1f} {x-r:.1f} {y:.1f} c "
            f"{x-r:.1f} {y-k:.1f} {x-k:.1f} {y-r:.1f} {x:.1f} {y-r:.1f} c "
            f"{x+k:.1f} {y-r:.1f} {x+r:.1f} {y-k:.1f} {x+r:.1f} {y:.1f} c "
            f"{'B' if fill and stroke else 'f' if fill else 'S'}\n"
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, sw: int = 3) -> None:
        self.stroke(color, sw)
        self.raw(f"{x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S\n")

    def text(self, x: float, y: float, text: str, size: int = 24, color: str = "ink", font: str = "F1", leading: int | None = None) -> None:
        leading = leading or int(size * 1.18)
        lines = text.split("\n")
        self.fill(color)
        self.raw(f"BT /{font} {size} Tf {leading} TL {x:.1f} {y:.1f} Td ")
        for i, line in enumerate(lines):
            if i:
                self.raw("T* ")
            self.raw(b"(" + esc(line) + b") Tj ")
        self.raw("ET\n")

    def label(self, x: float, y: float, text: str, fill: str = "yellow", color: str = "deep_green") -> None:
        width = max(140, 11 * len(text) + 34)
        self.rect(x, y - 13, width, 45, fill=fill)
        self.text(x + 17, y, text.upper(), 17, color, "F2")

    def finish(self) -> bytes:
        return b"".join(self.parts)


def brand_logo(p: PageBuilder, x: int, y: int, scale: float = 1.0) -> None:
    p.text(x, y + int(28 * scale), "terres", int(38 * scale), "deep_green", "F2")
    p.text(x + int(118 * scale), y + int(28 * scale), "inovia", int(38 * scale), "green", "F2")
    p.rect(x, y, int(245 * scale), int(14 * scale), fill="yellow")
    for i, c in enumerate(["green", "light_green", "yellow", "orange"]):
        p.circle(x + int((280 + i * 28) * scale), y + int(41 * scale), int(11 * scale), fill=c)


def background(p: PageBuilder, accent: str = "green") -> None:
    p.rect(0, 0, PAGE, PAGE, fill="cream")
    p.circle(980, 990, 205, fill="light_green")
    p.circle(920, 1070, 125, fill="yellow")
    p.circle(45, 85, 145, fill=accent)
    p.rect(0, 0, PAGE, 18, fill="deep_green")
    for x in range(-80, PAGE, 120):
        p.line(x, 44, x + 250, 160, "light_green", 2)


def draw_insect_field(p: PageBuilder, x: int, y: int) -> None:
    p.circle(x + 260, y + 245, 190, fill="yellow")
    p.rect(x + 20, y + 30, 500, 190, fill="green")
    for i in range(8):
        p.line(x + 30 + i * 65, y + 32, x + 120 + i * 30, y + 220, "deep_green", 4)
    p.circle(x + 250, y + 315, 58, fill="orange")
    p.circle(x + 315, y + 315, 58, fill="orange")
    p.circle(x + 282, y + 292, 72, fill="deep_green")
    p.circle(x + 282, y + 375, 32, fill="deep_green")
    for dx in [-70, -45, 45, 70]:
        p.line(x + 282, y + 292, x + 282 + dx, y + 230, "ink", 5)


def draw_crop_network(p: PageBuilder, x: int, y: int) -> None:
    p.rect(x + 10, y + 20, 520, 400, fill="white")
    for i in range(5):
        p.line(x + 60, y + 80 + i * 62, x + 485, y + 110 + i * 50, "light_green", 4)
    nodes = [(95, 150), (205, 270), (345, 180), (440, 330), (315, 385)]
    for a, b in zip(nodes, nodes[1:]):
        p.line(x + a[0], y + a[1], x + b[0], y + b[1], "orange", 8)
    for nx, ny in nodes:
        p.circle(x + nx, y + ny, 34, fill="deep_green")
        p.circle(x + nx, y + ny, 14, fill="yellow")
    for i in range(9):
        px = x + 70 + i * 48
        p.line(px, y + 50, px + 8, y + 115, "green", 5)
        p.circle(px - 8, y + 105, 12, fill="light_green")
        p.circle(px + 18, y + 124, 12, fill="light_green")


def draw_faba_lab(p: PageBuilder, x: int, y: int) -> None:
    p.rect(x + 25, y + 25, 490, 390, fill="white")
    p.rect(x + 58, y + 72, 165, 230, fill="cream", stroke="green", sw=5)
    p.line(x + 140, y + 82, x + 140, y + 260, "deep_green", 7)
    for dx, dy in [(-42, 95), (42, 140), (-36, 175), (45, 210)]:
        p.circle(x + 140 + dx, y + dy, 28, fill="light_green")
    p.rect(x + 292, y + 100, 60, 240, fill="cream", stroke="deep_green", sw=5)
    p.rect(x + 292, y + 100, 60, 95, fill="yellow")
    p.rect(x + 382, y + 150, 65, 210, fill="cream", stroke="deep_green", sw=5)
    p.rect(x + 382, y + 150, 65, 70, fill="orange")
    p.circle(x + 322, y + 372, 33, fill="green")
    p.circle(x + 415, y + 393, 26, fill="green")
    for i in range(5):
        p.line(x + 288, y + 122 + i * 36, x + 352, y + 122 + i * 36, "muted", 2)


def footer(p: PageBuilder, index: int, total: int = 4) -> None:
    p.text(MARGIN, 38, CAREERS_URL, 18, "muted")
    p.text(948, 38, f"{index}/{total}", 18, "muted", "F2")


def cover() -> bytes:
    p = PageBuilder()
    background(p, "green")
    brand_logo(p, MARGIN, 905, 1.25)
    p.label(MARGIN, 785, "Carrousel LinkedIn", "yellow")
    p.text(MARGIN, 650, "3 dernières\noffres à la une", 82, "deep_green", "F2", 90)
    p.text(
        MARGIN,
        530,
        "Recherche, terrain, biodiversité : rejoignez un institut engagé\n"
        "pour les filières huiles, protéines végétales et chanvre.",
        28,
        "ink",
        "F1",
        36,
    )
    for i, offer in enumerate(OFFERS):
        y = 395 - i * 95
        p.rect(MARGIN, y - 18, 835, 72, fill="white")
        p.circle(MARGIN + 38, y + 18, 28, fill="yellow")
        p.text(MARGIN + 25, y + 9, offer.number, 18, "deep_green", "F2")
        p.text(MARGIN + 86, y + 18, offer.title.replace("\n", " — "), 23, "deep_green", "F2")
        p.text(MARGIN + 86, y - 9, offer.location, 18, "muted")
    footer(p, 1)
    return p.finish()


def offer_page(offer: Offer, page_index: int) -> bytes:
    p = PageBuilder()
    background(p, "orange" if offer.number == "03" else "green")
    brand_logo(p, MARGIN, 930, 0.82)
    p.label(705, 945, offer.published, "yellow")
    p.text(MARGIN, 805, offer.title, 58, "deep_green", "F2", 64)
    p.rect(MARGIN, 676, 255, 56, fill="deep_green")
    p.text(MARGIN + 24, 694, offer.contract, 24, "white", "F2")
    p.rect(MARGIN + 275, 676, 350, 56, fill="yellow")
    p.text(MARGIN + 300, 694, offer.location, 24, "deep_green", "F2")
    p.text(MARGIN, 604, f"{offer.region} • {offer.duration}", 30, "ink", "F2")
    p.text(MARGIN, 558, offer.start, 25, "muted")
    y = 475
    for bullet in offer.bullets:
        p.circle(MARGIN + 14, y + 8, 9, fill="orange")
        p.text(MARGIN + 42, y, bullet, 29, "ink")
        y -= 62
    p.rect(MARGIN, 185, 425, 78, fill="deep_green")
    p.text(MARGIN + 30, 213, "Postuler sur terresinovia.fr", 26, "white", "F2")
    p.text(MARGIN, 150, offer.url, 20, "muted")
    p.label(625, 585, offer.tag, "orange", "white")
    if offer.image == "insect_field":
        draw_insect_field(p, 505, 140)
    elif offer.image == "crop_network":
        draw_crop_network(p, 505, 140)
    else:
        draw_faba_lab(p, 505, 140)
    p.text(760, 88, offer.number, 96, "deep_green", "F2")
    footer(p, page_index)
    return p.finish()


def build_pdf(pages: Iterable[bytes]) -> bytes:
    pages = list(pages)
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_obj_num = 3 + len(pages) * 2
    for i, content in enumerate(pages):
        page_num = 3 + i * 2
        content_num = page_num + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE} {PAGE}] /Resources << /Font << /F1 {font_obj_num} 0 R /F2 {font_obj_num+1} 0 R >> >> /Contents {content_num} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for num, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{num} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def main() -> None:
    pages = [cover()] + [offer_page(offer, i + 2) for i, offer in enumerate(OFFERS)]
    OUT.write_bytes(build_pdf(pages))
    print(f"Generated {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
