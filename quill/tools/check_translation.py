"""CI gate for QUILL translation infrastructure.

Checks:
1. babel.cfg exists at the project root.
2. quill/locale/quill.pot exists (the master template).
3. Each .po file in quill/locale/ is syntactically parseable.
4. Each .po file has no missing placeholders relative to .pot.
5. Each .po file preserves mnemonic (&) count for menu and button strings.
6. Coverage summary reported per language (no threshold enforced by default;
   use --min-coverage to fail below a percentage).

Run::

    python -m quill.tools.check_translation [--pot-only] [--min-coverage N]

Exit code 0 = all checks pass.  Exit code 1 = failures reported to stdout.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOCALE_DIR = _PROJECT_ROOT / "quill" / "locale"
_BABEL_CFG = _PROJECT_ROOT / "babel.cfg"
_POT_FILE = _LOCALE_DIR / "quill.pot"

_PLACEHOLDER_RE = re.compile(r"%\([^)]+\)[sdi]|%[sdi]|\{[^}]*\}")


def _mnemonic_count(s: str) -> int:
    # && is an escaped literal & in wxPython, not a mnemonic. Strip all && pairs first.
    return s.replace("&&", "").count("&")


def _extract_placeholders(s: str) -> list[str]:
    return _PLACEHOLDER_RE.findall(s)


def _parse_po(path: Path) -> list[tuple[str, str, bool]]:
    """Return list of (msgid, msgstr, is_fuzzy) triples from a .po or .pot file.

    Handles multi-line quoted values and skips plural forms (msgstr[n]).
    The #, fuzzy comment precedes the msgid it qualifies; this parser carries
    the flag forward correctly so it lands on the right entry.
    """
    triples: list[tuple[str, str, bool]] = []
    msgid: list[str] = []
    msgstr: list[str] = []
    current_fuzzy = False  # fuzzy state of the entry being accumulated
    next_fuzzy = False  # set when #, fuzzy is seen; applied at next msgid
    in_msgid = False
    in_msgstr = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("#,") and "fuzzy" in line:
            next_fuzzy = True
        elif line.startswith("msgid "):
            # flush accumulated entry with its fuzzy state
            mid, mstr = "".join(msgid), "".join(msgstr)
            if mid or mstr:
                triples.append((mid, mstr, current_fuzzy))
            msgid.clear()
            msgstr.clear()
            # the pending fuzzy flag now belongs to this new entry
            current_fuzzy = next_fuzzy
            next_fuzzy = False
            in_msgid = True
            in_msgstr = False
            msgid.append(_unquote(line[6:]))
        elif line.startswith("msgid_plural "):
            in_msgid = False
        elif line.startswith("msgstr "):
            in_msgid = False
            in_msgstr = True
            msgstr.append(_unquote(line[7:]))
        elif line.startswith("msgstr["):
            in_msgstr = False  # skip plural forms
        elif line.startswith('"'):
            value = _unquote(line)
            if in_msgid:
                msgid.append(value)
            elif in_msgstr:
                msgstr.append(value)
        elif not line:
            in_msgid = False
            in_msgstr = False

    # flush final entry
    mid, mstr = "".join(msgid), "".join(msgstr)
    if mid or mstr:
        triples.append((mid, mstr, current_fuzzy))
    return triples


def _unquote(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")


def _pot_msgids(path: Path) -> dict[str, str]:
    """Return {msgid: msgid} for all non-empty msgids in a .pot."""
    return {mid: mid for mid, _, _ in _parse_po(path) if mid}


def check_babel_cfg() -> list[str]:
    if not _BABEL_CFG.is_file():
        return [f"Missing babel.cfg at {_BABEL_CFG}"]
    return []


def check_pot_exists() -> list[str]:
    if not _POT_FILE.is_file():
        return [
            f"Master template {_POT_FILE} not found. "
            "Run: pybabel extract -F babel.cfg -k _ -k 'ngettext:1,2' "
            "-k lazy_gettext --project QUILL "
            "-o quill/locale/quill.pot quill/"
        ]
    return []


def check_po_files(min_coverage: float = 0.0) -> list[str]:
    errors: list[str] = []
    po_files = sorted(_LOCALE_DIR.glob("*/LC_MESSAGES/quill.po"))
    if not po_files:
        return []

    pot_ids: dict[str, str] = {}
    if _POT_FILE.is_file():
        pot_ids = _pot_msgids(_POT_FILE)

    for po_path in po_files:
        lang = po_path.parts[-3]  # quill/locale/{lang}/LC_MESSAGES/quill.po
        triples = _parse_po(po_path)
        total = len(pot_ids)
        translated = 0

        for msgid, msgstr, is_fuzzy in triples:
            if not msgid:
                continue
            if is_fuzzy or not msgstr:
                continue
            if msgid in pot_ids:
                translated += 1

            # Placeholder check
            pot_ph = sorted(_extract_placeholders(msgid))
            po_ph = sorted(_extract_placeholders(msgstr))
            if pot_ph != po_ph:
                errors.append(
                    f"{lang}: placeholder mismatch for {msgid!r}: expected {pot_ph}, got {po_ph}"
                )

            # Mnemonic (&) count check
            pot_m = _mnemonic_count(msgid)
            po_m = _mnemonic_count(msgstr)
            if pot_m > 0 and pot_m != po_m:
                errors.append(
                    f"{lang}: mnemonic count mismatch for {msgid!r}: "
                    f"source has {pot_m} &, translation has {po_m} &"
                )

        pct = 100.0 * translated / total if total else 100.0
        coverage_line = f"{lang}: {pct:.0f}% ({translated}/{total} strings)"
        print(f"  coverage: {coverage_line}")
        if pct < min_coverage:
            errors.append(f"{lang}: coverage {pct:.0f}% is below required {min_coverage:.0f}%")

    return errors


def run(pot_only: bool = False, min_coverage: float = 0.0) -> int:
    all_errors: list[str] = []
    all_errors += check_babel_cfg()
    all_errors += check_pot_exists()
    if not pot_only:
        all_errors += check_po_files(min_coverage=min_coverage)
    if all_errors:
        for err in all_errors:
            print(f"TRANSLATION: {err}")
        return 1
    po_count = len(list(_LOCALE_DIR.glob("*/LC_MESSAGES/quill.po")))
    print(f"check_translation: OK ({po_count} .po files checked)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check QUILL translation infrastructure.")
    parser.add_argument(
        "--pot-only",
        action="store_true",
        help="Only check that babel.cfg and quill.pot exist; skip .po validation.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.0,
        metavar="N",
        help="Fail if any language is below N%% translated (default: 0, no threshold).",
    )
    args = parser.parse_args()
    sys.exit(run(pot_only=args.pot_only, min_coverage=args.min_coverage))


if __name__ == "__main__":
    main()
