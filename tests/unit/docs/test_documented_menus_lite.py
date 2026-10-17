"""GATE-DOCMENU for QUILL Lite: what the changelog and guide promise is on the menus.

Jeff, 2026-10-16: "many commands mentioned are not in the menus like search in
files, search in open documents ... I launched from running from source and did
not find them." Both were real rows -- inside **Edit > Matches**, a submenu whose
name says nothing about a folder search, while QUILL filed the same commands
somewhere else again. Every chord gate was green throughout, because every key
was bound. What none of them asked is the question a reader with the changelog
in one hand actually asks: *is it on the menu, where the document says, for a
new install?*

This asks it, with the reader in ``menu_claims.py``. The menu is QUILL Lite's
own command table, filtered exactly as the menu builder filters it
(:func:`~quill.core.lite.command_areas.visible_commands`) with the areas a new
install starts with (``DEFAULT_OFF``). A claim that only exists once an area is
switched on -- AI help, timestamped backups, Go To Anything -- passes only where
the same chapter says how to switch it on, which is the guide's half of the
"off by default" decision recorded in the PRD.

Since the Edit menu move, Find in Open Documents, Search in Files and Replace
Across Files are rows of Edit itself in both editors; the last test pins that.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.lite.command_areas import visible_commands
from quill.core.lite.commands import SUBMENU_SEP, CommandRow
from quill.core.lite.features import DEFAULT_OFF
from quill.core.lite.keymap import DEFAULT_ALIASES
from tests.unit.docs.menu_claims import ROOT, MenuItem, OptIn, check_documents

_DOCS = ROOT / "standalone" / "quilllite" / "docs"
DOCUMENTS: tuple[Path, ...] = (_DOCS / "CHANGELOG.md", _DOCS / "userguide.md")

#: Claims that are right although the menu does not keep them, each with why.
#: Prefer fixing the document; an entry here is for a sentence that is *about*
#: another program's menu or about where a command used to be.
ALLOW: dict[str, str] = {
    "path:tools > speech > live dictation": (
        "QUILL's menu, named beside QUILL Lite's own Tools > Dictation for comparison"
    ),
    "path:tools > speech > live": "the same QUILL path, wrapped across two lines",
    "path:edit > insert": "history: where Insert's rows lived before the Insert menu",
    "path:file > dictate anywhere key": "Quill Inkwell's menu, in the Dictate Anywhere chapter",
    "path:tools > customize and support > bring my quill lite settings": (
        "QUILL's menu: the guide is telling the reader how to move settings across"
    ),
    "path:file > file": "QUILL's File > File Encoding window, named as the same window",
    "path:tools > writing": "history: QUILL's Tools menu as it was named in that release",
    # Keys of the Review Dictation window, not of the menu bar: they work only
    # while that window has focus, and the guide's table says so.
    "key:insert": "Review Dictation window key (Ctrl+Enter), not a menu command",
    "key:insert the words": "Review Dictation window key (Ctrl+Enter), not a menu command",
    "key:back to the words exactly as you said them": (
        "Review Dictation window key (Ctrl+Shift+Z), not a menu command"
    ),
}

#: Opt-in areas, and the words that tell a reader how to opt in. Customize
#: Features is the switch for every area; the AI chapter also says "AI help",
#: the area's own name in that dialog.
_SWITCH_PHRASES = ("Customize Features", "AI help")


def _items(rows: list[CommandRow]) -> list[MenuItem]:
    out: list[MenuItem] = []
    seen: set[tuple[str, ...]] = set()
    for menu, label, key, _handler, kind in rows:
        if kind == "sep":
            continue
        parts = tuple(menu.split(SUBMENU_SEP))
        for size in range(1, len(parts) + 1):
            if parts[:size] not in seen:
                seen.add(parts[:size])
                out.append(MenuItem(parts[:size]))
        if kind != "sub":
            out.append(MenuItem((*parts, label), key))
    return out


def _new_install() -> list[MenuItem]:
    return _items(visible_commands(lambda area: area not in DEFAULT_OFF))


def _everything() -> list[MenuItem]:
    return _items(visible_commands(lambda _area: True))


def _aliases() -> dict[str, str]:
    from quill.core.lite.commands import COMMANDS, plain_label

    names = {handler: plain_label(label) for _m, label, _k, handler, _kind in COMMANDS}
    return {chord: names[h] for h, chord in DEFAULT_ALIASES.items() if chord and h in names}


def test_every_documented_menu_path_and_command_is_on_a_new_install_menu() -> None:
    findings, used = check_documents(
        DOCUMENTS,
        _new_install(),
        ALLOW,
        extra_keys=_aliases(),
        opt_in=[OptIn(_everything(), _SWITCH_PHRASES)],
    )
    assert not findings, (
        "QUILL Lite's documents promise menu paths or commands a new install "
        "does not show (fix the document, the menu, or say how to switch the "
        "area on in the same chapter):\n  " + "\n  ".join(findings)
    )
    stale = sorted(set(ALLOW) - used)
    assert not stale, f"allowlist entries that no longer match anything: {stale}"


def test_the_gate_catches_the_report_it_was_written_for(tmp_path: Path) -> None:
    """The shapes Jeff's report came from, against a menu without the rows."""
    doc = tmp_path / "CHANGELOG.md"
    doc.write_text(
        "# Changes\n\n"
        "- **Search in Files** (**Ctrl+Alt+Shift+F**), on **Edit > Search Tools**.\n"
        "- Turn it on in **Tools > Nowhere Features**.\n",
        encoding="utf-8",
    )
    items = [item for item in _new_install() if "Search in Files" not in item.path[-1]]
    findings, _used = check_documents([doc], items, {})
    joined = "\n".join(findings)
    assert "edit > search tools" in joined
    assert "tools > nowhere features" in joined
    assert "Search in Files" in joined


def test_an_opt_in_command_passes_only_where_the_chapter_says_how(tmp_path: Path) -> None:
    doc = tmp_path / "userguide.md"
    doc.write_text(
        "# Guide\n\n## Backups\n\nUse **File > Earlier Versions...**.\n\n"
        "## Backups again\n\nTurn on backups in **Tools > Customize Features...**, then "
        "use **File > Earlier Versions...**.\n",
        encoding="utf-8",
    )
    findings, _used = check_documents(
        [doc], _new_install(), {}, opt_in=[OptIn(_everything(), _SWITCH_PHRASES)]
    )
    assert len(findings) == 1 and ":5:" in findings[0], findings


def test_the_wider_searches_are_rows_of_edit_itself() -> None:
    """Where Jeff looked: arrowing down Edit must say all three by name."""
    edit = [item.path[-1] for item in _new_install() if item.path[:1] == ("&Edit",)]
    for title in ("F&ind in Open Documents...", "&Search in Files...", "Replace Across Files..."):
        assert title in edit, f"{title} is not a row of Edit in a new install"
