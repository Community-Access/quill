"""Tiny Scribe-shaped files of our own, for the F1-F8 quirk tests in CI.

Every file here is written by this module at test time: nothing is copied
from Pneuma's corpus or from Scribe. Each reproduces one quirk Pneuma's
corpus showed (``scribe-test-plan.md`` section 2), in the same shape and with
the same bytes that matter, so GitHub CI guards the fixes without
``QUILL_SCRIBE_CORPUS``. The text is ours (a made-up garden club handbook).
"""

from __future__ import annotations

import base64
import zipfile
from pathlib import Path

#: A 1 by 1 transparent PNG, ours.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
#: The linear alt text Scribe gives an equation picture (F7), in our words.
EQUATION_ALT = "x subscript 1 = [a, a - 1, ..., 2, 1]"
#: A title Scribe could read from a scan: a stamp, then the real heading (F6).
STAMPED_TITLE = ".R. Stamp THE GARDEN CLUB HANDBOOK"

_BODY = """<h1>Garden Club Handbook</h1>
<h2>Watering</h2>
<ul><li>Water early</li><li>Check the soil</li></ul>
<table><tr><th>Day</th><th>Morning</th></tr><tr><td>Monday</td><td>Beans</td></tr></table>
<p>See <a href="https://example.org/garden">the club page</a>.</p>
"""


def accessible_html(path: Path) -> Path:
    """Accessible HTML whose picture is a relative name the download leaves out (F2)."""
    path.write_text(
        '<!DOCTYPE html>\n<html lang="en"><head><title>Garden Club Handbook</title></head>'
        f"<body>{_BODY}"
        '<img src="handbook_html_0a1b2c.png" alt="Rainfall chart"></body></html>\n',
        encoding="utf-8",
    )
    return path


def offline_page(path: Path) -> Path:
    """The offline web page as one HTML file with its picture inside (F1)."""
    data = base64.b64encode(PNG_1X1).decode("ascii")
    path.write_text(
        '<!DOCTYPE html>\n<html lang="en"><head><title>Garden Club Handbook</title></head>'
        f'<body>{_BODY}<img src="data:image/png;base64,{data}" alt="Rainfall chart">'
        "</body></html>\n",
        encoding="utf-8",
    )
    return path


def offline_zip(path: Path) -> Path:
    """The offline web page as a zip of the page and its picture (F1)."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("index.html", f'<html lang="en"><body>{_BODY}<img src="a.png" alt="A">')
        archive.writestr("a.png", PNG_1X1)
    return path


def math_html(path: Path) -> Path:
    """Scribe's mathematics today (F7): a picture with linear alt text, no MathML."""
    path.write_text(
        '<!DOCTYPE html>\n<html lang="en"><body><h1>Counting rows</h1>'
        "<p>The longest row is</p>"
        f'<p><img src="eq1.png" alt="{EQUATION_ALT}"></p>'
        "<p>and n squared is plain text inline.</p></body></html>\n",
        encoding="utf-8",
    )
    return path


#: BRF lines, 40 cells at most: the quirks Scribe's files had (F4) -- a TAB, the
#: UTF-8 bytes C2 B4 (an acute accent carried over from the source), CRLF line
#: ends, a form feed after every page and so one at the very end.
BRF_PAGE_1 = b",g>d5 ,clu# ,h&book\r\n,wat]+\tm\xc2\xb4n+s\r\n" + b" " * 37 + b"#a\r\n"
BRF_PAGE_2 = b",! soil is dry\r\n" + b" " * 37 + b"#b\r\n"
BRF_BYTES = BRF_PAGE_1 + b"\x0c" + BRF_PAGE_2 + b"\x0c"


def brf_with_quirks(path: Path) -> Path:
    path.write_bytes(BRF_BYTES)
    return path


def epub2_language_c(path: Path) -> Path:
    """EPUB 2 as calibre writes it for Scribe: ``dc:language`` is ``C`` (F5)."""
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:title>Garden Club Handbook</dc:title><dc:language>C</dc:language>"
        '<dc:identifier id="id">garden-1</dc:identifier></metadata>'
        '<manifest><item id="c1" href="text/part1.html" media-type="application/xhtml+xml"/>'
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>'
        '<spine toc="ncx"><itemref idref="c1"/></spine></package>'
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap>'
        '<navPoint id="p1" playOrder="1"><navLabel><text>Garden Club Handbook</text></navLabel>'
        '<content src="text/part1.html"/></navPoint></navMap></ncx>'
    )
    chapter = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en"><body>'
        "<h1>Garden Club Handbook</h1><p>Water early, before the sun is high.</p>"
        "<p>Check the soil with a finger.</p></body></html>"
    )
    container = (
        '<?xml version="1.0"?><container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
        '<rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("content.opf", opf)
        archive.writestr("toc.ncx", ncx)
        archive.writestr("text/part1.html", chapter)
    return path


#: Three sections, each its own SMIL and MP3 (Scribe splits the audio).
DAISY_SECTIONS = ("Garden Club Handbook", "Watering", "Planting")


def daisy3_zip(path: Path, folder: str = "garden_handbook") -> Path:
    """A DAISY 3 book as Scribe zips it (F3): one folder, the OPF saying
    ``Z39.86-2002``, and a picture ``dtbook.xml`` names but the zip lacks."""
    nav = "".join(
        f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>{title}</text></navLabel>'
        f'<content src="s{i}.smil#t{i}"/></navPoint>'
        for i, title in enumerate(DAISY_SECTIONS, start=1)
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f"<docTitle><text>Garden Club Handbook</text></docTitle><navMap>{nav}</navMap></ncx>"
    )
    manifest = "".join(
        f'<item id="s{i}" href="s{i}.smil" media-type="application/smil"/>'
        f'<item id="a{i}" href="a{i}.mp3" media-type="audio/mpeg"/>'
        for i in range(1, len(DAISY_SECTIONS) + 1)
    )
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://openebook.org/namespaces/oeb-package/1.0/" unique-identifier="u">'
        '<metadata><dc-metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:Title>Garden Club Handbook</dc:Title><dc:Format>ANSI/NISO Z39.86-2002</dc:Format>"
        '<dc:Identifier id="u">garden-1</dc:Identifier></dc-metadata></metadata>'
        '<manifest><item id="ncx" href="dtb.ncx" media-type="application/x-dtbncx+xml"/>'
        f'<item id="book" href="dtbook.xml" media-type="application/x-dtbook+xml"/>{manifest}'
        "</manifest></package>"
    )
    dtbook = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<dtbook xmlns="http://www.daisy.org/z3986/2005/dtbook/" version="2005-3"><book>'
        '<level1><h1 id="t1">Garden Club Handbook</h1>'
        '<imggroup><img src="pic1.png" alt="Rainfall chart"/></imggroup></level1>'
        '<level1><h1 id="t2">Watering</h1></level1><level1><h1 id="t3">Planting</h1></level1>'
        "</book></dtbook>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{folder}/dtb.opf", opf)
        archive.writestr(f"{folder}/dtb.ncx", ncx)
        archive.writestr(f"{folder}/dtbook.xml", dtbook)
        for i in range(1, len(DAISY_SECTIONS) + 1):
            archive.writestr(
                f"{folder}/s{i}.smil",
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<smil xmlns="http://www.w3.org/2001/SMIL20/"><body><seq>'
                f'<par id="t{i}"><audio src="a{i}.mp3" clipBegin="0:00:00.000" '
                'clipEnd="0:00:01.000"/></par></seq></body></smil>',
            )
            archive.writestr(f"{folder}/a{i}.mp3", b"\xff\xfb\x90\x00" + b"\x00" * 64)
    return path


__all__ = [
    "BRF_BYTES",
    "DAISY_SECTIONS",
    "EQUATION_ALT",
    "PNG_1X1",
    "STAMPED_TITLE",
    "accessible_html",
    "brf_with_quirks",
    "daisy3_zip",
    "epub2_language_c",
    "math_html",
    "offline_page",
    "offline_zip",
]
