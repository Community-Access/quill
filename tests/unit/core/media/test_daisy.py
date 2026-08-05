"""Unit tests for ``quill.core.media.daisy`` (NCX navigation parsing)."""

from __future__ import annotations

import pytest

from quill.core.media import DaisyHeading, DaisyParseError, parse_ncx
from quill.core.media.daisy import (
    first_audio_src,
    parse_clip_ms,
    resolve_heading_times,
    smil_clip_begin_ms,
)

_NCX = """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="n1" playOrder="1">
      <navLabel><text>Chapter One</text></navLabel>
      <content src="ch1.smil#s1"/>
      <navPoint id="n1a" playOrder="2">
        <navLabel><text>Section 1.1</text></navLabel>
        <content src="ch1.smil#s2"/>
      </navPoint>
    </navPoint>
    <navPoint id="n2" playOrder="3">
      <navLabel><text>Chapter Two</text></navLabel>
      <content src="ch2.smil#s1"/>
    </navPoint>
  </navMap>
</ncx>
"""


def test_parse_ncx_headings_in_order() -> None:
    headings = parse_ncx(_NCX)
    assert headings == [
        DaisyHeading(title="Chapter One", play_order=1, src="ch1.smil#s1", depth=1),
        DaisyHeading(title="Section 1.1", play_order=2, src="ch1.smil#s2", depth=2),
        DaisyHeading(title="Chapter Two", play_order=3, src="ch2.smil#s1", depth=1),
    ]


def test_depth_reflects_nesting() -> None:
    depths = [h.depth for h in parse_ncx(_NCX)]
    assert depths == [1, 2, 1]


def test_missing_navmap_raises() -> None:
    with pytest.raises(DaisyParseError):
        parse_ncx("<ncx xmlns='http://www.daisy.org/z3986/2005/ncx/'></ncx>")


def test_malformed_xml_raises() -> None:
    with pytest.raises(DaisyParseError):
        parse_ncx("<ncx><navMap><navPoint></ncx>")


def test_non_namespaced_ncx_also_parses() -> None:
    xml = (
        "<ncx><navMap><navPoint playOrder='1'>"
        "<navLabel><text>Intro</text></navLabel>"
        "<content src='a.smil'/></navPoint></navMap></ncx>"
    )
    assert parse_ncx(xml) == [DaisyHeading(title="Intro", play_order=1, src="a.smil", depth=1)]


@pytest.mark.parametrize(
    ("text", "ms"),
    [
        ("npt=12.5s", 12_500),
        ("12.5s", 12_500),
        ("12500ms", 12_500),
        ("12.5", 12_500),
        ("0:12.5", 12_500),
        ("1:02:03.5", 3_723_500),
        ("", None),
        ("bogus", None),
    ],
)
def test_parse_clip_ms(text: str, ms: int | None) -> None:
    assert parse_clip_ms(text) == ms


_SMIL = """<?xml version="1.0"?>
<smil xmlns="http://www.w3.org/ns/SMIL">
  <body>
    <par id="s1"><text src="c.html#t1"/>
      <audio src="a.mp3" clipBegin="npt=0s" clipEnd="npt=30s"/></par>
    <par id="s2"><text src="c.html#t2"/>
      <audio src="a.mp3" clipBegin="npt=30.25s"/></par>
  </body>
</smil>
"""


def test_smil_clip_begin() -> None:
    assert smil_clip_begin_ms(_SMIL, "s1") == 0
    assert smil_clip_begin_ms(_SMIL, "s2") == 30_250
    assert smil_clip_begin_ms(_SMIL, "missing") is None


def test_first_audio_src() -> None:
    assert first_audio_src(_SMIL) == "a.mp3"
    assert first_audio_src("<smil><body/></smil>") is None
    assert first_audio_src("not xml <<<") is None


def test_resolve_heading_times() -> None:
    headings = [
        DaisyHeading("One", 1, "ch1.smil#s1", 1),
        DaisyHeading("Two", 2, "ch1.smil#s2", 1),
        DaisyHeading("Gone", 3, "missing.smil#x", 1),
    ]
    resolved = resolve_heading_times(headings, lambda name: _SMIL if name == "ch1.smil" else None)
    assert [h.time_ms for h in resolved] == [0, 30_250, None]
    # audio_src is filled from the SMIL <audio src=...>
    assert resolved[0].audio_src == "a.mp3"
    assert resolved[2].audio_src == ""


_SMIL_MULTI = """<?xml version="1.0"?>
<smil xmlns="http://www.w3.org/ns/SMIL"><body>
  <par id="p"><audio src="part2.mp3" clipBegin="npt=5s"/></par>
</body></smil>
"""


def test_resolve_multi_file() -> None:
    from quill.core.media.daisy import smil_audio_clip

    assert smil_audio_clip(_SMIL, "s2") == ("a.mp3", 30_250)
    headings = [
        DaisyHeading("One", 1, "ch1.smil#s1", 1),
        DaisyHeading("Two", 2, "part2.smil#p", 1),
    ]
    smils = {"ch1.smil": _SMIL, "part2.smil": _SMIL_MULTI}
    resolved = resolve_heading_times(headings, lambda name: smils.get(name))
    assert [(h.audio_src, h.time_ms) for h in resolved] == [("a.mp3", 0), ("part2.mp3", 5_000)]
