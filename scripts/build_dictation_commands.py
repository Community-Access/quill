"""Write the dictation command reference from the table dictation itself reads.

The list of everything dictation understands lives in one place,
``quill/core/windows_dictation/vocabulary.py``. This renders it (through
``quill.core.windows_dictation.reference``) into the Markdown both editors
publish, so the reference a person reads is the list that works.
``tests/unit/scripts/test_dictation_commands_doc.py`` fails when a copy falls
behind; the HTML and EPUB beside each copy are rendered from it as usual.

Usage::

    python scripts/build_dictation_commands.py          # rewrite both copies
    python scripts/build_dictation_commands.py --check  # fail if either is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from quill.core.windows_dictation.reference import commands_reference  # noqa: E402

TARGETS = (
    _REPO / "standalone" / "quilllite" / "docs" / "dictation-commands.md",
    _REPO / "docs" / "user guide" / "dictation-commands.md",
)


def rendered() -> str:
    return commands_reference(markdown=True)


def stale() -> list[Path]:
    text = rendered()
    return [
        path
        for path in TARGETS
        if not path.is_file() or path.read_text(encoding="utf-8").replace("\r\n", "\n") != text
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        out_of_date = stale()
        for path in out_of_date:
            print(f"{path} is out of date. Run: python scripts/build_dictation_commands.py")
        return 1 if out_of_date else 0
    text = rendered()
    for path in TARGETS:
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
