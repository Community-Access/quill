"""Plain-data model for a loaded BRF/BRL/PEF/UEB file.

The :class:`BRFDocument` is the type that flows from the read path
(``quill/io/open_read.py``) into the page map engine, the position
resolver, the status string composer, and the UI. It is a frozen
snapshot: re-read the file to get a new document.

This module is wx-free; it lives in ``quill/core`` and is the only place
that defines the BRF data shape. Strict-typed: mypy ``--strict`` must
stay clean.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.brf_ascii import LineEndingReport, detect_line_endings


@dataclass(slots=True)
class BRFDocument:
    """A loaded braille text file, normalized to a single in-memory text.

    Fields:

    * ``text`` — the file body after BOM strip. Trailing form feeds are
      preserved (they are load-bearing page terminators).
    * ``suffix`` — the lower-cased extension without the dot
      (``"brf"`` / ``"brl"`` / ``"pef"`` / ``"ueb"``).
    * ``encoding`` — always ``"ascii"`` for a successful BRF read; the
      loader falls back to ``"utf-8"`` if a non-ASCII codepoint was
      observed.
    * ``line_ending`` — the dominant line ending (``"\\r\\n"`` /
      ``"\\n"`` / ``"\\r"``); ``""`` for an empty file.
    * ``had_bom`` — True when a UTF-8 BOM was stripped.
    * ``line_endings`` — full :class:`LineEndingReport` for the file
      (the save path uses ``is_mixed`` to decide whether to surface a
      warning).
    * ``non_ascii_offsets`` — char offsets of every non-NABCC byte the
      loader saw, in document order. Empty when the file is clean BRF.
    * ``profile`` — the active braille profile key (set by the
      settings layer in BR-008).
    * ``cell_width`` / ``line_height`` — page geometry. Defaults are
      the standard UEB single-sided values: 40 cells, 25 lines.
    """

    text: str
    suffix: str
    encoding: str = "ascii"
    line_ending: str = "\n"
    had_bom: bool = False
    line_endings: LineEndingReport = field(
        default_factory=lambda: LineEndingReport(crlf=0, lf=0, cr=0, form_feed=0)
    )
    non_ascii_offsets: list[int] = field(default_factory=list)
    profile: str = "ueb_english"
    cell_width: int = 40
    line_height: int = 25

    def __post_init__(self) -> None:
        # Defensive: the read path is the only writer today, but tests
        # build BRFDocument literals and we want a single normalization
        # point so invariants cannot drift.
        if not isinstance(self.non_ascii_offsets, list):
            self.non_ascii_offsets = list(self.non_ascii_offsets)
        if self.cell_width <= 0:
            raise ValueError("cell_width must be positive")
        if self.line_height <= 0:
            raise ValueError("line_height must be positive")
        if self.suffix and self.suffix.startswith("."):
            self.suffix = self.suffix.lstrip(".").lower()

    @property
    def non_ascii_count(self) -> int:
        return len(self.non_ascii_offsets)

    @property
    def is_clean_brf(self) -> bool:
        return not self.non_ascii_offsets and not self.had_bom

    @property
    def is_mixed_line_endings(self) -> bool:
        return self.line_endings.is_mixed

    @property
    def form_feed_count(self) -> int:
        return self.text.count("\x0c")

    @classmethod
    def from_text_and_suffix(
        cls,
        text: str,
        suffix: str,
        *,
        had_bom: bool = False,
        non_ascii_offsets: list[int] | None = None,
        cell_width: int = 40,
        line_height: int = 25,
        profile: str = "ueb_english",
    ) -> BRFDocument:
        """Build a :class:`BRFDocument` from the read path's outputs.

        Computes the line-ending report and the dominant line ending so
        the rest of the pipeline never has to.
        """
        report = detect_line_endings(text)
        return cls(
            text=text,
            suffix=suffix,
            encoding="ascii" if not non_ascii_offsets else "utf-8",
            line_ending=report.dominant,
            had_bom=had_bom,
            line_endings=report,
            non_ascii_offsets=list(non_ascii_offsets) if non_ascii_offsets else [],
            profile=profile,
            cell_width=cell_width,
            line_height=line_height,
        )
