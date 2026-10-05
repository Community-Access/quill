"""My dictation instructions: how Tidy Dictated Text should tidy *your* writing.

dict.md 5.3 C, after VS Code's dictation instructions (``~/.copilot/dictation.md``,
"Voice: Configure Dictation Instructions"), in QUILL's own words. A plain
Markdown file beside My Words and Phrases (``dictation-instructions.md`` next to
``dictation.md``, in each editor's data folder, so a portable copy keeps it in
the portable folder) where a person writes what they want: "write numbers as
digits", "British spelling", "QUILL is always in capitals", "I am a lawyer:
keep legal terms exactly".

**When it is used.** Only by **Tidy Dictated Text** (Ctrl+F3), on the selection
or the paragraph you choose, as one request when you ask -- never on every
phrase as you speak, which would send every sentence to the internet, cost
money on each one and slow dictation down on exactly the modest computers and
connections QUILL is for. It goes with the same AI help rules as always: a
ChatGPT plan or your own key, the request said out loud as "Working", nothing
replaced until you press Replace My Selection.

**How it is sent.** Your text and your instructions are sent as two marked
parts, and the AI is told the text is data to correct, never a request to
follow -- VS Code's rule too, because dictated text is often a question or an
instruction to somebody else ("ask Sam to send the report"), and the tidy-up
must not answer it.

wx-free.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["FILE_NAME", "TEMPLATE", "ensure_instructions", "instructions_path", "read", "wrap"]

FILE_NAME = "dictation-instructions.md"

TEMPLATE = """\
# My dictation instructions

Tell Tidy Dictated Text (Ctrl+F3) how you like your dictated writing tidied.
Write one instruction per line, in plain words. Delete these examples and add
your own; anything inside the arrows below is ignored.

<!--
Examples:
- Write numbers as digits.
- Use British spelling.
- QUILL is always written in capitals.
- Never change legal terms.
-->
"""

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
#: Generous, but a file this long is a mistake rather than a preference.
_MAX_CHARACTERS = 4_000


def instructions_path(profile_path: Path) -> Path:
    """The instructions file beside *profile_path* (``dictation.md``)."""
    return Path(profile_path).with_name(FILE_NAME)


def ensure_instructions(path: Path) -> Path:
    """*path*, created from :data:`TEMPLATE` first when it is not there yet."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE, encoding="utf-8")
    return path


def read(path: Path) -> str:
    """The person's instructions, without the template's heading, help and
    examples; ``""`` when there are none. Never raises."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    text = _COMMENT.sub("", text)
    template_lines = {line.strip() for line in _COMMENT.sub("", TEMPLATE).splitlines()}
    kept = [
        line for line in text.splitlines() if line.strip() and line.strip() not in template_lines
    ]
    return "\n".join(kept).strip()[:_MAX_CHARACTERS]


def wrap(text: str, instructions: str) -> str:
    """What Tidy Dictated Text sends: the text alone, or the text and the
    instructions as two marked parts (the tidy instruction explains both)."""
    if not instructions.strip():
        return text
    return (
        f"<dictation-instructions>\n{instructions.strip()}\n</dictation-instructions>\n\n"
        f"<dictated-text>\n{text}\n</dictated-text>"
    )
