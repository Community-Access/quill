"""Colour contrast for WordPress palettes, said in words (wordpress.md 9.7).

Every colour choice in Block Settings says its contrast against the background
it will sit on -- "Accent (dark green), 7.2 to 1, passes" -- and the Palette
Report says that for every pairing in the theme. The maths is WCAG 2.x relative
luminance; the colour word comes from hue, lightness and saturation buckets,
so a writer who cannot see the swatch hears roughly what it is.

Pure stdlib, no wx.
"""

from __future__ import annotations

import colorsys
import math
import re
from dataclasses import dataclass

from quill.core.error_codes import CodedError

__all__ = [
    "AA_LARGE_TEXT",
    "AA_NORMAL_TEXT",
    "Colour",
    "ColourParseError",
    "contrast_ratio",
    "describe_choice",
    "format_ratio",
    "nearest_colour_name",
    "palette_report",
    "parse_colour",
    "rating",
    "relative_luminance",
]

#: WCAG AA minimum for body text.
AA_NORMAL_TEXT = 4.5
#: WCAG AA minimum for large text (18 pt, or 14 pt bold).
AA_LARGE_TEXT = 3.0


class ColourParseError(CodedError, ValueError):
    """A colour string QUILL cannot read as hex, rgb() or a CSS name."""

    code = "QUILL-WORDPRESS-CHECKS-BAD-COLOUR"


@dataclass(frozen=True)
class Colour:
    """An sRGB colour, channels 0-255, alpha 0.0-1.0."""

    red: int
    green: int
    blue: int
    alpha: float = 1.0

    def hex(self) -> str:
        """The opaque ``#rrggbb`` form (alpha dropped)."""
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"

    def over(self, background: Colour) -> Colour:
        """This colour composited over an opaque ``background``."""
        if self.alpha >= 1.0:
            return Colour(self.red, self.green, self.blue)
        a = max(0.0, self.alpha)

        def mix(fg: int, bg: int) -> int:
            return round(fg * a + bg * (1.0 - a))

        return Colour(
            mix(self.red, background.red),
            mix(self.green, background.green),
            mix(self.blue, background.blue),
        )


# The CSS named colours (CSS Color Module Level 4), all 148 of them; theme
# palettes and inline styles use the common ones, but a partial table would
# fail on whichever one a theme author happened to like.
_NAMED: dict[str, str] = {
    "aliceblue": "f0f8ff",
    "antiquewhite": "faebd7",
    "aqua": "00ffff",
    "aquamarine": "7fffd4",
    "azure": "f0ffff",
    "beige": "f5f5dc",
    "bisque": "ffe4c4",
    "black": "000000",
    "blanchedalmond": "ffebcd",
    "blue": "0000ff",
    "blueviolet": "8a2be2",
    "brown": "a52a2a",
    "burlywood": "deb887",
    "cadetblue": "5f9ea0",
    "chartreuse": "7fff00",
    "chocolate": "d2691e",
    "coral": "ff7f50",
    "cornflowerblue": "6495ed",
    "cornsilk": "fff8dc",
    "crimson": "dc143c",
    "cyan": "00ffff",
    "darkblue": "00008b",
    "darkcyan": "008b8b",
    "darkgoldenrod": "b8860b",
    "darkgray": "a9a9a9",
    "darkgreen": "006400",
    "darkgrey": "a9a9a9",
    "darkkhaki": "bdb76b",
    "darkmagenta": "8b008b",
    "darkolivegreen": "556b2f",
    "darkorange": "ff8c00",
    "darkorchid": "9932cc",
    "darkred": "8b0000",
    "darksalmon": "e9967a",
    "darkseagreen": "8fbc8f",
    "darkslateblue": "483d8b",
    "darkslategray": "2f4f4f",
    "darkslategrey": "2f4f4f",
    "darkturquoise": "00ced1",
    "darkviolet": "9400d3",
    "deeppink": "ff1493",
    "deepskyblue": "00bfff",
    "dimgray": "696969",
    "dimgrey": "696969",
    "dodgerblue": "1e90ff",
    "firebrick": "b22222",
    "floralwhite": "fffaf0",
    "forestgreen": "228b22",
    "fuchsia": "ff00ff",
    "gainsboro": "dcdcdc",
    "ghostwhite": "f8f8ff",
    "gold": "ffd700",
    "goldenrod": "daa520",
    "gray": "808080",
    "green": "008000",
    "greenyellow": "adff2f",
    "grey": "808080",
    "honeydew": "f0fff0",
    "hotpink": "ff69b4",
    "indianred": "cd5c5c",
    "indigo": "4b0082",
    "ivory": "fffff0",
    "khaki": "f0e68c",
    "lavender": "e6e6fa",
    "lavenderblush": "fff0f5",
    "lawngreen": "7cfc00",
    "lemonchiffon": "fffacd",
    "lightblue": "add8e6",
    "lightcoral": "f08080",
    "lightcyan": "e0ffff",
    "lightgoldenrodyellow": "fafad2",
    "lightgray": "d3d3d3",
    "lightgreen": "90ee90",
    "lightgrey": "d3d3d3",
    "lightpink": "ffb6c1",
    "lightsalmon": "ffa07a",
    "lightseagreen": "20b2aa",
    "lightskyblue": "87cefa",
    "lightslategray": "778899",
    "lightslategrey": "778899",
    "lightsteelblue": "b0c4de",
    "lightyellow": "ffffe0",
    "lime": "00ff00",
    "limegreen": "32cd32",
    "linen": "faf0e6",
    "magenta": "ff00ff",
    "maroon": "800000",
    "mediumaquamarine": "66cdaa",
    "mediumblue": "0000cd",
    "mediumorchid": "ba55d3",
    "mediumpurple": "9370db",
    "mediumseagreen": "3cb371",
    "mediumslateblue": "7b68ee",
    "mediumspringgreen": "00fa9a",
    "mediumturquoise": "48d1cc",
    "mediumvioletred": "c71585",
    "midnightblue": "191970",
    "mintcream": "f5fffa",
    "mistyrose": "ffe4e1",
    "moccasin": "ffe4b5",
    "navajowhite": "ffdead",
    "navy": "000080",
    "oldlace": "fdf5e6",
    "olive": "808000",
    "olivedrab": "6b8e23",
    "orange": "ffa500",
    "orangered": "ff4500",
    "orchid": "da70d6",
    "palegoldenrod": "eee8aa",
    "palegreen": "98fb98",
    "paleturquoise": "afeeee",
    "palevioletred": "db7093",
    "papayawhip": "ffefd5",
    "peachpuff": "ffdab9",
    "peru": "cd853f",
    "pink": "ffc0cb",
    "plum": "dda0dd",
    "powderblue": "b0e0e6",
    "purple": "800080",
    "rebeccapurple": "663399",
    "red": "ff0000",
    "rosybrown": "bc8f8f",
    "royalblue": "4169e1",
    "saddlebrown": "8b4513",
    "salmon": "fa8072",
    "sandybrown": "f4a460",
    "seagreen": "2e8b57",
    "seashell": "fff5ee",
    "sienna": "a0522d",
    "silver": "c0c0c0",
    "skyblue": "87ceeb",
    "slateblue": "6a5acd",
    "slategray": "708090",
    "slategrey": "708090",
    "snow": "fffafa",
    "springgreen": "00ff7f",
    "steelblue": "4682b4",
    "tan": "d2b48c",
    "teal": "008080",
    "thistle": "d8bfd8",
    "tomato": "ff6347",
    "turquoise": "40e0d0",
    "violet": "ee82ee",
    "wheat": "f5deb3",
    "white": "ffffff",
    "whitesmoke": "f5f5f5",
    "yellow": "ffff00",
    "yellowgreen": "9acd32",
}

_HEX_RE = re.compile(r"#?([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
_RGB_RE = re.compile(r"rgba?\(\s*([^)]*)\)", re.IGNORECASE)


def _channel(token: str) -> int:
    token = token.strip()
    if token.endswith("%"):
        value = float(token[:-1]) * 255.0 / 100.0
    else:
        value = float(token)
    return max(0, min(255, round(value)))


def _alpha(token: str) -> float:
    token = token.strip()
    value = float(token[:-1]) / 100.0 if token.endswith("%") else float(token)
    return max(0.0, min(1.0, value))


def parse_colour(value: str | Colour) -> Colour:
    """Read ``#rgb``, ``#rgba``, ``#rrggbb``, ``#rrggbbaa``, ``rgb()``/``rgba()``
    or a CSS colour name. Raises :class:`ColourParseError` on anything else."""
    if isinstance(value, Colour):
        return value
    text = value.strip()
    lowered = text.lower()
    if lowered in _NAMED:
        text = "#" + _NAMED[lowered]
    hex_match = _HEX_RE.fullmatch(text)
    if hex_match and (text.startswith("#") or len(text) in (6, 8)):
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits)
        red, green, blue = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
        alpha = int(digits[6:8], 16) / 255.0 if len(digits) == 8 else 1.0
        return Colour(red, green, blue, alpha)
    rgb_match = _RGB_RE.fullmatch(text)
    if rgb_match:
        body = rgb_match.group(1)
        # Both the legacy comma form and the modern "r g b / a" form.
        if "," in body:
            parts = body.split(",")
        else:
            colour_part, _, alpha_part = body.partition("/")
            parts = colour_part.split()
            if alpha_part.strip():
                parts.append(alpha_part)
        try:
            if len(parts) == 3:
                return Colour(*(_channel(p) for p in parts))
            if len(parts) == 4:
                red, green, blue = (_channel(p) for p in parts[:3])
                return Colour(red, green, blue, _alpha(parts[3]))
        except ValueError as exc:
            raise ColourParseError(f"Cannot read the colour {value!r}.") from exc
    raise ColourParseError(f"Cannot read the colour {value!r}.")


def _linear(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: str | Colour) -> float:
    """WCAG 2.x relative luminance, 0.0 (black) to 1.0 (white). Alpha ignored."""
    c = parse_colour(colour)
    return 0.2126 * _linear(c.red) + 0.7152 * _linear(c.green) + 0.0722 * _linear(c.blue)


_WHITE = Colour(255, 255, 255)


def contrast_ratio(fg: str | Colour, bg: str | Colour) -> float:
    """The WCAG contrast ratio of ``fg`` on ``bg``, 1.0 to 21.0.

    A translucent background is first laid over white (the page); a translucent
    foreground is then laid over that background, which is what a reader sees.
    """
    background = parse_colour(bg).over(_WHITE)
    foreground = parse_colour(fg).over(background)
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def rating(ratio: float, *, large_text: bool = False) -> str:
    """ "passes", "passes for large text only" or "too faint for text" (WCAG AA)."""
    if large_text:
        return "passes" if ratio >= AA_LARGE_TEXT else "too faint for text"
    if ratio >= AA_NORMAL_TEXT:
        return "passes"
    if ratio >= AA_LARGE_TEXT:
        return "passes for large text only"
    return "too faint for text"


def format_ratio(ratio: float) -> str:
    """ "7.2 to 1". Rounded *down* to one decimal, so 4.48 never reads as 4.5
    beside a verdict that says it fails."""
    value = math.floor(ratio * 10 + 1e-9) / 10
    number = f"{value:.1f}".removesuffix(".0")
    return f"{number} to 1"


def nearest_colour_name(colour: str | Colour) -> str:
    """A plain colour word -- "dark green", "pale yellow", "light grey" -- from
    hue, lightness and saturation buckets. Rough on purpose: it says what a
    colour is like, not which of 148 names it is."""
    c = parse_colour(colour)
    hue, lightness, saturation = colorsys.rgb_to_hls(c.red / 255.0, c.green / 255.0, c.blue / 255.0)
    if saturation < 0.12 or lightness < 0.04 or lightness > 0.97:
        if lightness < 0.1:
            return "black"
        if lightness > 0.94:
            return "white"
        if lightness < 0.35:
            return "dark grey"
        if lightness > 0.75:
            return "light grey"
        return "grey"
    degrees = hue * 360.0
    if degrees < 15 or degrees >= 345:
        base = "red"
    elif degrees < 40:
        base = "orange"
    elif degrees < 65:
        base = "yellow"
    elif degrees < 165:
        base = "green"
    elif degrees < 190:
        base = "teal"
    elif degrees < 255:
        base = "blue"
    elif degrees < 315:
        base = "purple"
    else:
        base = "pink"
    # Dark orange and dark yellow are what people call brown.
    if base in ("orange", "yellow") and lightness < 0.4:
        return "dark brown" if lightness < 0.2 else "brown"
    # Light red is what people call pink.
    if base == "red" and lightness >= 0.7:
        base = "pink"
    if lightness < 0.3:
        prefix = "dark "
    elif lightness < 0.6:
        prefix = ""
    elif lightness < 0.85:
        prefix = "light "
    else:
        prefix = "pale "
    if saturation < 0.3 and prefix in ("", "dark "):
        prefix = prefix + "greyish "
    return f"{prefix}{base}"


def describe_choice(name: str, fg: str | Colour, bg: str | Colour) -> str:
    """ "Accent (dark green), 7.2 to 1, passes" for a colour ``fg`` on ``bg``.

    The colour word is left out when the name already is it ("Pale yellow,
    1.4 to 1, too faint for text").
    """
    ratio = contrast_ratio(fg, bg)
    seen = parse_colour(fg).over(parse_colour(bg).over(_WHITE))
    return f"{_label(name, seen)}, {format_ratio(ratio)}, {rating(ratio)}"


def _label(name: str, colour: Colour) -> str:
    """ "Accent (dark green)"; just "Dark green" when the name is missing or
    already says it."""
    word = nearest_colour_name(colour)
    label = name.strip() or word.capitalize()
    if label.casefold() != word.casefold():
        label = f"{label} ({word})"
    return label


def palette_report(palette: list[tuple[str, str]], backgrounds: list[tuple[str, str]]) -> list[str]:
    """Every pairing of a palette colour on a background, one line each:
    "Accent (dark green) on Base (white), 7.2 to 1, passes".

    A colour paired with itself is left out: it is the background, not text on
    it. Each argument is a list of ``(name, colour)``.
    """
    lines: list[str] = []
    for bg_name, bg in backgrounds:
        background = parse_colour(bg)
        bg_label = _label(bg_name, background.over(_WHITE))
        for fg_name, fg in palette:
            foreground = parse_colour(fg)
            if foreground == background:
                continue
            ratio = contrast_ratio(foreground, background)
            label = _label(fg_name, foreground.over(background.over(_WHITE)))
            lines.append(f"{label} on {bg_label}, {format_ratio(ratio)}, {rating(ratio)}")
    return lines
