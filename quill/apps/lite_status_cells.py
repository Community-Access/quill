r"""What QuillLite's status bar cells *are*: the catalogue, and how one is sized.

Split out of :mod:`quill.apps.lite_window_status`, which is the behaviour --
when the bar refreshes, what it reads, where focus goes. This is the data: the
twelve cells, the sentence each one answers F1 with, the two names a codec and
a line ending are given, and the one rule about how wide a button is allowed to
be. A catalogue and a controller grow for different reasons and at different
rates, and the controller is the one that has to stay readable.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import wx

from quill.core.lite.textfile import ENCODING_CHOICES, NEWLINE_CHOICES
from quill.core.status_cell_width import ratchet_width
from quill.core.status_message import IDLE_MESSAGE

__all__ = [
    "CELLS",
    "RICH_ENCODING_CELL",
    "RICH_LINE_ENDINGS_CELL",
    "StatusCell",
    "encoding_name",
    "native_cell_labels",
    "newline_name",
]

#: How long caret movement may leave the bar stale. QUILL's own coalescing
#: window (``StatusBarMixin._STATUSBAR_COALESCE_MS``): a tenth of a second is
#: imperceptible, and refreshing synchronously on every caret event was several
#: full-buffer scans per keystroke.
_COALESCE_MS = 90

#: The message cell is the one whose text has no natural ceiling.
_MESSAGE = "message"

#: How many characters of a status message the *label* shows. The message cell
#: is the only one whose text is unbounded -- a path, an OS error, a sentence --
#: and a button label wider than its button is ellipsised by wxMSW. Capped here
#: and read in full by Enter on the cell (and by the F6 landing announcement),
#: which is the trade the fixed cells never have to make: Position and Encoding
#: say two facts nothing else in the app will tell you, so they are never
#: shortened.
#:
#: It was ninety, and ninety was too many. The row wraps, so one cell wide
#: enough to hold a sentence pushes the eleven after it onto further rows --
#: and the bottom row is what a reader scraping the window finds. The report
#: that fixed this number read ``"CRLF (Windows) Modified"``: the last two
#: cells of twelve, alone on the last row, because Ctrl+Shift+Y had just put
#: two hundred characters in the first one. The scrape itself is answered by
#: the native bar (:mod:`quill.ui.native_status_bar`); this is the other half,
#: which is that the visible row should not wrap in the first place.
_MESSAGE_LABEL_CHARS = 40

#: The margin each cell button is added with, and the slack left under the last
#: row when the bar's height is measured.
_CELL_GAP = 2

#: A height no wrapped row can reach, used to lay the cells out at a known width
#: so their real extent can be measured. ``wx.WrapSizer.CalcMin`` reports one
#: row whatever it is told (``InformFirstDirection`` returns False and changes
#: nothing), so the wrapped height has to come from an actual layout pass.
_REFLOW_PROBE_HEIGHT = 10_000


def _widen_to_label(button: wx.Button) -> bool:
    """Widen *button* to hold its current label. Returns whether it grew.

    A cell may get wider and never narrower, and
    :func:`~quill.core.status_cell_width.ratchet_width` is where that rule and
    the bug report behind it are written down.

    Never raises: a cell being re-measured during teardown is a dead C++
    wrapper, and the bar must not take the window down with it.
    """
    try:
        button.InvalidateBestSize()
        width = ratchet_width(button.GetBestSize().width, button.GetMinSize().width)
        if width <= button.GetMinSize().width:
            return False
        button.SetMinSize((width, -1))
    except RuntimeError:
        return False
    return True


def _clip_message(message: str) -> str:
    """*message* shortened to what a status button can show without ellipsising.

    Cut at the last space inside the budget so a half-word is never left
    dangling, and mark the cut so the label does not read as the whole message.
    The full text is still one Enter away on the cell.
    """
    if len(message) <= _MESSAGE_LABEL_CHARS:
        return message
    head = message[:_MESSAGE_LABEL_CHARS].rstrip()
    space = head.rfind(" ")
    if space > _MESSAGE_LABEL_CHARS // 2:
        head = head[:space]
    return f"{head.rstrip()}..."


@dataclass(frozen=True, slots=True)
class StatusCell:
    """One cell: its key, the name it announces, and what F1 says about it."""

    key: str
    label: str
    help_text: str


CELLS: tuple[StatusCell, ...] = (
    StatusCell(
        "position",
        "Position",
        "Where the cursor is: line and column, out of how many lines. "
        "Press Enter to go to a line by number.",
    ),
    StatusCell(
        "words",
        "Word Count",
        "How many words the whole document has. A word is a run of characters with "
        "a space or a line break on each side, which is how QUILL counts them too, "
        "so the two products never disagree about the length of the same file.",
    ),
    StatusCell(
        "characters",
        "Character Count",
        "How many characters the whole document has, spaces and line breaks "
        "included. This counts characters as you would read them, not bytes on "
        "disk: an accented letter is one character here whatever the encoding.",
    ),
    StatusCell(
        "selection",
        "Selection",
        "How much text is selected. It reads 'No selection' when there is none.",
    ),
    StatusCell(
        "typing_mode",
        "Typing Mode",
        "Whether typing inserts characters or overwrites the ones already there. "
        "The native editing control keeps this mode and will not report it, so "
        "this cell is the only way to ask. Press Enter to switch.",
    ),
    StatusCell(
        "tab_mode",
        "Tab Mode",
        "What the Tab key does: type a tab character, or indent the whole line. "
        "Shift+Tab outdents either way. Press Enter to switch.",
    ),
    StatusCell(
        "format",
        "Format",
        "What kind of document this is: plain text, Markdown, HTML or rich "
        "text. It decides what Bold writes, what the heading keys write, which "
        "of the two tag pickers the Insert menu offers, and whether the cursor "
        "can tell you what list you are in. Press Enter to ring on to the next "
        "kind; press Control Alt F6 to go straight to one.",
    ),
    StatusCell(
        "heading",
        "Heading",
        "The heading the cursor is inside -- the point-size ladder in a rich "
        "text document, the Markdown hashes in a plain one. "
        "Press Enter for the list of every heading.",
    ),
    StatusCell(
        "list",
        "List",
        "The list the cursor is inside, how many items it has at this level, "
        "and how far down you are -- the three facts a screen reader gives you "
        "about a list on a web page and cannot give you about one in an editor. "
        "It reads 'Not in a list' when you are not. Press Enter to stop or "
        "resume announcing lists as you move.",
    ),
    StatusCell(
        "encoding",
        "Encoding",
        "The character encoding this file was read with and will be written back "
        "with: UTF-8, UTF-8 with a byte order mark, UTF-16, or Windows-1252. "
        "Press Enter to change it.",
    ),
    StatusCell(
        "line_endings",
        "Line Endings",
        "Whether this file uses Windows line endings (CRLF) or Unix ones (LF). "
        "QuillLite writes back whichever it read, so a file does not change shape "
        "just because it was opened. Press Enter to change it.",
    ),
    StatusCell("saved", "Saved State", "Whether this document has unsaved changes."),
    # Last, and the position is load-bearing twice over. The row **wraps**, so
    # the one cell whose width has no ceiling has to be the one with nothing
    # after it to push -- it was first, and a two-hundred-character message
    # shoved the other eleven cells onto rows a screen reader scraping the
    # window could not see ("CRLF (Windows) Modified"). And the native bar
    # reads the message last, after the facts somebody pressed the key for, so
    # the row and the native bar now walk in the same order. F6 landing on
    # Position rather than on "Ready" is the third thing this bought.
    StatusCell(
        _MESSAGE,
        "Status Message",
        "The last thing QuillLite announced. Speech is gone once it is spoken; "
        "this is where it can be read again.",
    ),
)

#: Codec and line-ending names, read from the same table the File Format
#: dialog offers, so the status bar and the chooser can never call the same
#: thing two different things. The one extra entry is what the chooser does
#: not offer: classic-Mac CR, which can be read but is not worth writing.
_ENCODING_NAMES = dict(ENCODING_CHOICES)
_NEWLINE_NAMES = dict(NEWLINE_CHOICES) | {"\r": "CR (classic Mac)"}


def encoding_name(codec: str) -> str:
    """How a codec is named to a person; the raw codec if it is not one of ours."""
    return _ENCODING_NAMES.get(codec, codec)


def newline_name(newline: str) -> str:
    """How a line ending is named to a person."""
    return _NEWLINE_NAMES.get(newline, "Mixed")


#: The cells whose value already names itself. "9,696 words" and "Line 3,
#: column 1 of 200" need no label in front of them; "Insert" and "UTF-8" are
#: not sentences on their own and get one. This matters only for the native
#: bar, which is read as one line with no control names in it -- on the button
#: row the reader announces each cell's name for us.
_SELF_NAMING = frozenset({
    _MESSAGE,
    "position",
    "selection",
    "words",
    "characters",
    "heading",
    "list",
    "saved",
})


def native_cell_labels(values: Mapping[str, str]) -> list[str]:
    """The cells' text for the native status bar, in the order they are shown.

    Two departures from the visible row, both about it being read as a single
    sentence rather than walked control by control. A cell whose value does not
    name itself is prefixed with its label, and the **message goes last** --
    it is the one cell holding something that already *was* spoken, so the
    facts somebody pressed the key for come first. An idle message is left out
    altogether rather than read as "Ready" at the end of every answer.
    """
    ordered: list[str] = []
    message = ""
    for cell in CELLS:
        value = str(values.get(cell.key) or "").strip()
        if not value:
            continue
        if cell.key == _MESSAGE:
            if value != IDLE_MESSAGE:
                message = value
            continue
        ordered.append(value if cell.key in _SELF_NAMING else f"{cell.label}: {value}")
    if message:
        ordered.append(message)
    return ordered


#: What the Encoding and Line Endings cells say about a document that has
#: neither -- rich text stores its own characters as RTF escapes and its own
#: breaks as paragraph marks, so there is no text codec and no line ending to
#: report (bad.md F7).
RICH_ENCODING_CELL = "RTF (rich text)"
RICH_LINE_ENDINGS_CELL = "Not applicable (rich text)"
