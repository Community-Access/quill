"""How captions look, and why the defaults are the defaults.

Section 508's 503.4.1 requires user controls for captions at the same menu level
as volume. WCAG adds two things the law does not spell out and that decide
whether captions are actually readable: **contrast** (1.4.3) and **scaling to
200% without loss** (1.4.4).

Both are harder for a video player than for a web page, for one reason: the
background is not ours. Caption text sits over arbitrary moving pictures, so no
text colour can be guaranteed to contrast with what is behind it. The only
honest answer is an **opaque background box by default** -- which is why the
default here is solid black behind white, not the semi-transparent grey most
players ship.

Sizes are expressed as a percentage of mpv's own default rather than in points,
so they scale with the window: a caption that is legible in a small window and
overflows a large one has failed at exactly the size somebody enlarged it for.

wx-free, strict-typed, pure. Everything here converts to mpv properties in one
function (:func:`mpv_properties`), so the player is the only thing that knows mpv
and this is the only thing that knows what a caption should look like.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Offered sizes, as a percentage of the player's default caption size. 200% is
#: present because WCAG 1.4.4 asks for it specifically; 300% is present because
#: somebody who needs 200% often needs more, and the standard is a floor.
SIZE_CHOICES: tuple[int, ...] = (100, 125, 150, 200, 300)

#: Colour choices, as ``(label, mpv colour)``. Deliberately few and deliberately
#: high-contrast: a full colour picker invites a listener to choose a
#: combination that fails, and the failure is silent until they cannot read a
#: caption during something they cared about.
TEXT_COLOURS: tuple[tuple[str, str], ...] = (
    ("White", "#FFFFFFFF"),
    ("Yellow", "#FFFFFF00"),
    ("Black", "#FF000000"),
)

BACKGROUND_COLOURS: tuple[tuple[str, str], ...] = (
    ("Black", "#FF000000"),
    ("Dark grey", "#FF303030"),
    ("White", "#FFFFFFFF"),
)

#: Where the caption sits. Top exists because a video with its own burned-in
#: subtitles, or an on-screen crawl, puts something worth reading at the bottom.
POSITIONS: tuple[tuple[str, str], ...] = (("Bottom", "bottom"), ("Top", "top"))


@dataclass(frozen=True, slots=True)
class CaptionStyle:
    """Everything adjustable about the look of a caption."""

    size_percent: int = 100
    text_colour: str = "#FFFFFFFF"
    background_colour: str = "#FF000000"
    #: 0 is fully transparent, 100 fully opaque. **Defaults to opaque**, because
    #: contrast against arbitrary video content cannot be guaranteed any other
    #: way -- see the module docstring.
    background_opacity: int = 100
    position: str = "bottom"

    def clamped(self) -> CaptionStyle:
        """The same style with every value inside its allowed range.

        A stored settings file is somebody else's input: a size of 4000 or an
        opacity of -3 must read as an ordinary value rather than reaching mpv.
        """
        size = min(SIZE_CHOICES[-1], max(SIZE_CHOICES[0], int(self.size_percent or 100)))
        opacity = min(100, max(0, int(self.background_opacity)))
        position = self.position if self.position in {p for _label, p in POSITIONS} else "bottom"
        return CaptionStyle(
            size_percent=size,
            text_colour=self.text_colour or "#FFFFFFFF",
            background_colour=self.background_colour or "#FF000000",
            background_opacity=opacity,
            position=position,
        )


def _with_alpha(colour: str, opacity_percent: int) -> str:
    """An ``#AARRGGBB`` colour with its alpha replaced by *opacity_percent*.

    mpv writes alpha first and counts it the ordinary way round (``FF`` opaque),
    so an opacity slider maps straight onto it.
    """
    body = colour[-6:] if len(colour) >= 6 else "000000"
    alpha = round(255 * min(100, max(0, opacity_percent)) / 100)
    return f"#{alpha:02X}{body}"


def mpv_properties(style: CaptionStyle) -> dict[str, str]:
    """*style* as the mpv properties that realise it.

    The single place that knows mpv's property names for captions, so a change
    of player is one function rather than a search. ``sub-font-size`` is mpv's
    own scale factor, which is why sizes here are percentages: they are the same
    number divided by a hundred.
    """
    clean = style.clamped()
    return {
        "sub-scale": f"{clean.size_percent / 100:.2f}",
        "sub-color": clean.text_colour,
        "sub-back-color": _with_alpha(clean.background_colour, clean.background_opacity),
        # mpv counts alignment from the top, so 100 is the bottom of the frame.
        "sub-align-y": "top" if clean.position == "top" else "bottom",
        # A border under any background, because a fully transparent background
        # is a choice a listener can make and unreadable text is not.
        "sub-border-size": "2",
    }


def describe(style: CaptionStyle) -> str:
    """The style as a sentence, for the announcement after a change."""
    clean = style.clamped()
    text = next((label for label, value in TEXT_COLOURS if value == clean.text_colour), "custom")
    back = next(
        (label for label, value in BACKGROUND_COLOURS if value == clean.background_colour),
        "custom",
    )
    opacity = (
        "opaque"
        if clean.background_opacity >= 100
        else ("transparent" if clean.background_opacity <= 0 else f"{clean.background_opacity}%")
    )
    return (
        f"Captions at {clean.size_percent}%, {text.lower()} on {back.lower()} "
        f"({opacity}), at the {clean.position}."
    )
