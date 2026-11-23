"""Our own text and pictures for the Scribe live-run sources, and the formats
written by hand (DCX, DjVu, EPUB, MOBI). Part of ``build_scribe_live_sources.py``;
everything here is ours (CC0 1.0): the Riverbend Community Tool Library is invented.
"""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

TITLE = "The Riverbend Community Tool Library"
SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Borrowing a tool",
        [
            "Any resident of Riverbend can borrow up to three tools at a time. Bring a library "
            "card and a recent letter with your address on it the first time you visit.",
            "Most tools go out for seven days. Ladders and the tile saw go out for three, "
            "because the waiting list for them is always long.",
        ],
    ),
    (
        "Returning a tool",
        [
            "Clean the tool before you bring it back, and tell the volunteer at the desk if "
            "anything is broken or missing. Nobody is charged for honest wear.",
        ],
    ),
    (
        "Opening hours",
        [
            "The library opens on Tuesday and Thursday evenings and all day on Saturday. "
            "It closes for the first week of January for the annual count.",
        ],
    ),
]
STEPS = ["Find the tool in the catalogue.", "Check it out at the desk.", "Return it on time."]
BULLETS = ["Garden tools", "Woodworking tools", "Kitchen equipment for events"]
TABLE = [
    ("Tool", "Loan period", "Waiting list"),
    ("Cordless drill", "7 days", "2 people"),
    ("Extension ladder", "3 days", "9 people"),
    ("Pressure washer", "3 days", "5 people"),
]
CHART_ALT = "Bar chart: loans per month, January 40, February 55, March 70."
LINK = ("the Riverbend volunteer page", "https://example.org/riverbend/volunteer")
SPANISH = [
    ("La biblioteca de herramientas de Riverbend", 1),
    ("Cómo pedir una herramienta", 2),
    (
        "Cualquier vecino de Riverbend puede llevarse hasta tres herramientas a la vez. "
        "La primera visita, traiga su tarjeta de la biblioteca y una carta con su dirección.",
        0,
    ),
    ("Cómo devolverla", 2),
    (
        "Limpie la herramienta antes de devolverla y avise al voluntario si algo está roto. "
        "Nadie paga por el desgaste normal.",
        0,
    ),
]


def chart_png() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (480, 300), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    for index, (month, value) in enumerate((("Jan", 40), ("Feb", 55), ("Mar", 70))):
        left = 60 + index * 140
        draw.rectangle((left, 260 - value * 3, left + 80, 260), fill=(40, 90, 160))
        draw.text((left + 20, 268), month, fill="black", font=font)
    draw.text((20, 10), "Loans per month", fill="black", font=font)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def page_image(lines: list[str] | None = None) -> object:
    """A letter-size page of our text, as a scan would see it (150 dpi, grey)."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("L", (1275, 1650), 255)
    draw = ImageDraw.Draw(image)
    big, body = ImageFont.load_default(size=44), ImageFont.load_default(size=28)
    draw.text((120, 120), TITLE, fill=0, font=big)
    y = 230
    for heading, paragraphs in SECTIONS:
        draw.text((120, y), heading, fill=0, font=big)
        y += 70
        for paragraph in lines or paragraphs:
            words, line = paragraph.split(), ""
            for word in words:
                if len(line) + len(word) > 62:
                    draw.text((120, y), line, fill=0, font=body)
                    y += 40
                    line = ""
                line = f"{line} {word}".strip()
            draw.text((120, y), line, fill=0, font=body)
            y += 60
    return image


def _dcx(pages: list[object]) -> bytes:
    """A DCX fax file: the magic number, the page offsets, then each PCX page."""
    blobs = []
    for page in pages:
        out = io.BytesIO()
        page.save(out, "PCX")  # type: ignore[attr-defined]
        blobs.append(out.getvalue())
    header_size = 4 + 1024 * 4
    offsets, position = [], header_size
    for blob in blobs:
        offsets.append(position)
        position += len(blob)
    header = struct.pack("<I", 987654321) + b"".join(struct.pack("<I", o) for o in offsets)
    header = header.ljust(header_size, b"\0")
    return header + b"".join(blobs)


def _chunk(name: bytes, data: bytes) -> bytes:
    return name + struct.pack(">I", len(data)) + data + (b"\0" if len(data) % 2 else b"")


def _djvu(page: object) -> bytes:
    """A one-page DjVu: an INFO chunk and a JPEG-encoded background layer (BGjp)."""
    out = io.BytesIO()
    page.convert("RGB").save(out, "JPEG", quality=85)  # type: ignore[attr-defined]
    width, height = page.size  # type: ignore[attr-defined]
    info = struct.pack(">HHBB", width, height, 24, 0) + struct.pack("<H", 150) + bytes([22, 1])
    body = b"DJVU" + _chunk(b"INFO", info) + _chunk(b"BGjp", out.getvalue())
    return b"AT&T" + b"FORM" + struct.pack(">I", len(body)) + body


def build_epub(target: Path) -> None:
    chapters = [
        (f"chapter{n}.xhtml", heading, paragraphs)
        for n, (heading, paragraphs) in enumerate(SECTIONS[:2], 1)
    ]
    with zipfile.ZipFile(target, "w") as book:
        book.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")
        book.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument'
            ':xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type='
            '"application/oebps-package+xml"/></rootfiles></container>',
            zipfile.ZIP_DEFLATED,
        )
        items = "".join(
            f'<item id="c{n}" href="{name}" media-type="application/xhtml+xml"/>'
            for n, (name, _h, _p) in enumerate(chapters, 1)
        )
        spine = "".join(f'<itemref idref="c{n}"/>' for n in range(1, len(chapters) + 1))
        book.writestr(
            "OEBPS/content.opf",
            '<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf"'
            ' version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/'
            f'elements/1.1/"><dc:identifier id="id">urn:quill:riverbend</dc:identifier><dc:title>'
            f'{TITLE}</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">'
            '2026-11-23T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" '
            'media-type="application/xhtml+xml" properties="nav"/><item id="chart" href="chart.png"'
            f' media-type="image/png"/>{items}</manifest><spine>{spine}</spine></package>',
            zipfile.ZIP_DEFLATED,
        )
        links = "".join(f'<li><a href="{n}">{h}</a></li>' for n, h, _p in chapters)
        book.writestr("OEBPS/nav.xhtml", _xhtml("Contents", f'<nav epub:type="toc"><ol>{links}'
                                                "</ol></nav>"), zipfile.ZIP_DEFLATED)  # fmt: skip
        for index, (name, heading, paragraphs) in enumerate(chapters):
            text = f"<h1>{heading}</h1>" + "".join(f"<p>{p}</p>" for p in paragraphs)
            if index == 0:
                text += f'<p><img src="chart.png" alt="{CHART_ALT}"/></p>'
            book.writestr(f"OEBPS/{name}", _xhtml(heading, text), zipfile.ZIP_DEFLATED)
        book.writestr("OEBPS/chart.png", chart_png())


def _xhtml(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en"><head><title>'
        f"{title}</title></head><body>{body}</body></html>"
    )


def build_mobi(target: Path) -> None:
    """MOBI 6, uncompressed: a PalmDB of record 0 (PalmDOC, MOBI and EXTH
    headers and the full name), the text records, and an end-of-file record."""
    html = "<html><head><guide></guide></head><body>"
    for heading, paragraphs in SECTIONS[:2]:
        html += f"<h2>{heading}</h2>" + "".join(f"<p>{p}</p>" for p in paragraphs)
        html += "<mbp:pagebreak/>"
    text = (html + "</body></html>").encode("ascii")
    records = [text[i : i + 4096] for i in range(0, len(text), 4096)]
    name = TITLE.encode("ascii")
    exth_records = b"".join(
        struct.pack(">II", kind, 8 + len(value)) + value
        for kind, value in ((100, b"QUILL project"), (503, name), (524, b"en"))
    )
    exth = b"EXTH" + struct.pack(">II", 12 + len(exth_records), 3) + exth_records
    exth += b"\0" * (-len(exth) % 4)
    mobi = bytearray(232)
    mobi[0:4] = b"MOBI"
    values = {4: 232, 8: 2, 12: 65001, 16: 0x5152494C, 20: 6}
    for offset in range(0x18, 0x40, 4):
        values[offset] = 0xFFFFFFFF
    values.update({
        0x40: len(records) + 1,
        0x44: 16 + 232 + len(exth),
        0x48: len(name),
        0x4C: 9,
        0x58: 6,
        0x5C: 0xFFFFFFFF,
        0x70: 0x40,
        0x94: 0xFFFFFFFF,
        0x98: 0xFFFFFFFF,
        0xB4: 1,
        0xB8: 0xFFFFFFFF,
        0xBC: 0xFFFFFFFF,
        0xC0: 0xFFFFFFFF,
        0xC4: 0xFFFFFFFF,
        0xD0: 0xFFFFFFFF,
        0xD8: 0xFFFFFFFF,
        0xDC: 0xFFFFFFFF,
        0xE4: 0xFFFFFFFF,
    })
    for offset, value in values.items():
        mobi[offset : offset + 4] = struct.pack(">I", value)
    mobi[0xB0:0xB2] = struct.pack(">H", 1)
    mobi[0xB2:0xB4] = struct.pack(">H", len(records))
    palmdoc = struct.pack(">HHIHHHH", 1, 0, len(text), len(records), 4096, 0, 0)
    record0 = palmdoc + bytes(mobi) + exth + name + b"\0\0"
    record0 += b"\0" * (-len(record0) % 4)
    all_records = [record0, *records, b"\xe9\x8e\r\n"]
    header = name[:31].ljust(32, b"\0")
    header += struct.pack(">HHIIIIII", 0, 0, 0x7B000000, 0x7B000000, 0, 0, 0, 0)
    header += b"BOOKMOBI" + struct.pack(">IIH", 2 * len(all_records) - 1, 0, len(all_records))
    offset = len(header) + 8 * len(all_records) + 2
    entries = b""
    for index, record in enumerate(all_records):
        entries += struct.pack(">I", offset) + struct.pack(">I", 2 * index)[1:].rjust(4, b"\0")
        offset += len(record)
    target.write_bytes(header + entries + b"\0\0" + b"".join(all_records))
