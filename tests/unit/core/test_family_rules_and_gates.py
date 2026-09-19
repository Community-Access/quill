"""The rules, and the two keymap gates bad.md left unwritten.

`bad.md` was the plan of record for the 2026-09 parity program and it is closed.
Its rules and its unshipped gates move here, because a rule that lives only in a
planning file is a rule that stops existing when somebody deletes the file --
and every one of these was written down precisely because the failure it
prevents had already happened once.

**Rule citations resolve.** `keymap.py` and `lite/parity.py` cite rules by
number. Renumbering the list would silently rewrite those comments into lies, so
the citations are checked against :mod:`quill.core.family_rules`.

**Gate 1, the bound-command gate (rule 8).** Every registered editor command has
a default chord or a written reason not to. Walking a menu to find there is no
shortcut is a cost a screen-reader user pays on every visit, and the 2026-09
audit found fifteen commands that QUILL had implemented, menued and left
unreachable.

**Gate 2, the Quillin hotkey gate.** A bundled extension may not claim a chord
the editor already binds. Whichever loses is silent about losing, and an
extension quietly shadowing Ctrl+S is the worst version of this.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from quill.core.family_rules import FAMILY_RULES, rule
from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP

_ROOT = Path(__file__).resolve().parents[3]
_QUILL = _ROOT / "quill"

#: Every ``rule N`` / ``rule #N`` mention in the shipped tree.
_CITATION = re.compile(r"\brule\s+#?(\d{1,2})\b", re.IGNORECASE)


# -- the rules themselves ------------------------------------------------------


def test_the_rules_are_numbered_from_one_with_no_gaps() -> None:
    assert [item.number for item in FAMILY_RULES] == list(range(1, len(FAMILY_RULES) + 1))


def test_every_rule_says_what_it_is_and_why() -> None:
    for item in FAMILY_RULES:
        assert item.statement.strip().endswith("."), item.number
        assert len(item.because) > 40, f"rule {item.number} has no stated reason"


def test_every_rule_citation_in_the_tree_points_at_a_real_rule() -> None:
    """The reason the numbers may never be reshuffled."""
    misses: list[str] = []
    for path in sorted(_QUILL.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in _CITATION.finditer(text):
            number = int(match.group(1))
            try:
                rule(number)
            except KeyError:
                line = text.count("\n", 0, match.start()) + 1
                misses.append(f"{path.relative_to(_ROOT).as_posix()}:{line} cites rule {number}")
    assert not misses, "citations of rules that do not exist:\n  " + "\n  ".join(misses)


def test_the_two_files_that_cite_rules_still_do() -> None:
    """A guard on the guard: if these stop citing, the check above proves nothing."""
    for relative in ("core/keymap.py", "core/lite/parity.py"):
        text = (_QUILL / relative).read_text(encoding="utf-8")
        assert _CITATION.search(text), f"{relative} no longer cites any rule"


# -- gate 1: every editor command has a key, or a reason ------------------------

#: Commands with no default chord, each with the reason. A row here is a decision
#: somebody made; an empty chord with no row is a command nobody decided about.
#:
#: Three kinds of reason appear, and no fourth is accepted:
#:
#: * **the user binds it** -- a command whose right chord depends on the person
#:   (a voice or dictation verb somebody may not use at all);
#: * **reached another way** -- a command whose real front door is a dialog, a
#:   list row or a context menu, where a chord would be a second route to one
#:   place;
#: * **deliberately vacated** -- a chord given up to settle a collision, the
#:   command staying reachable from its menu.
#: Command families that are **not editor commands**, and so are outside rule 8
#: by rule 7: "editor chords are for the editor". Recorded once per family rather
#: than once per command, because the argument is the same every time and ninety
#: separate rows would be ninety places for it to rot.
#:
#: A family here is still reachable -- from its own menu, its own window, or the
#: command palette. What it does not get is a chord out of the editor's budget.
NOT_EDITOR_COMMANDS: dict[str, str] = {
    "vault.": "The Accessible Vault is a knowledge base inside QUILL, with its own "
    "window and its own menu. Twenty-two of the editor's chords is not a price "
    "text editing can pay for it (rule 7).",
    "github.": "Repository operations: branches, releases, pull requests, "
    "Codespaces. None of them edits text, and a person who never touches GitHub "
    "should not lose a chord to it (rule 7).",
    "localgit.": "As github: version control beside the editor rather than in it, and none of it "
    "edits text (rule 7).",
    "podcasts.": "QUILL Cast's own surface, reached from that app, where these commands have "
    "their own menu bar and their own keys (rule 7).",
    "radio.": "Quill Radio's own surface, reached from that app, which has its own menu bar and "
    "its own keys (rule 7).",
    "story.": "Story Studio is a manuscript organiser with its own window and its own menu, "
    "reached from there (rule 7).",
    "sync.": "A folder sync is a background service that runs without anybody pressing anything; "
    "its settings are its front door (rule 7).",
    "verbosity.": "The verbosity commands are settings surfaces; the *announcement* "
    "commands a listener presses (repeat, self-test) are in app.* and are "
    "deliberately user-bound below.",
    "file.github_": "GitHub file operations reached from the File menu: still repository work "
    "rather than text work (rule 7).",
    "file.open_github": "As file.github_: opening from a repository is a connection dialog, not "
    "a keystroke (rule 7).",
    "file.manage_remote_sites": "Remote-file plumbing: a connection manager, not a "
    "text command (rule 7).",
    "file.open_from_remote": "As manage_remote_sites: the connection dialog is the front door, "
    "and it has to be, because it asks which site (rule 7).",
    "file.save_to_remote": "As open_from_remote: which site to save to is a question, and a "
    "chord cannot ask it (rule 7).",
}

UNBOUND_WITH_REASON: dict[str, str] = {
    "app.repeat_last_announcement": "The user binds it. Which key a listener wants "
    "for 'say that again' depends on their reader's own layer keys, and guessing "
    "wrong puts it under something they use constantly.",
    "app.announcement_self_test": "Reached another way: Help, where somebody goes "
    "when they suspect nothing is reaching them. Once in a lifetime.",
    "app.open_media_player": "Rule 7: launching another app is not an editor chord. "
    "The QuillVille menu and its launcher F-keys reach it.",
    "edit.set_named_mark": "Reached another way: the mark family's own window, where "
    "naming a mark means typing the name anyway.",
    "edit.jump_to_named_mark": "As set_named_mark: the list is the front door, and it "
    "is the thing that shows you what the names are.",
    "edit.search_tray_slots": "Reached another way: the Copy Tray dialog "
    "(Ctrl+Alt+V), which is where the slots you would be searching are.",
    "format.list_studio_settings": "Reached another way: the Structured List Studio "
    "itself, whose settings these are.",
    "power.non_ascii_jump_to_report": "Reached another way: the non-ASCII report "
    "window, where the rows are what you jump from.",
    "power.non_ascii_jump_to_source": "As jump_to_report: a row in a report is the "
    "front door, and a chord would be a second route to one place.",
    "tools.ai_spell_check": "Deliberately vacated 2026-09 under rule 7: an AI verb "
    "does not hold an editor chord. F7 is the real spell checker.",
    "tools.ai_spell_check_interactive": "As ai_spell_check: deliberately vacated under rule 7, "
    "with F7 as the real spell checker.",
    "tools.ai_switch_engine": "Reached another way: the AI Hub, which is where the "
    "engines are configured in the first place.",
    "tools.csv_studio": "Experimental and opt-in (Preferences > Experimental). A "
    "chord for a feature most people have switched off is a chord spent.",
    "tools.table_studio": "As csv_studio: experimental and opt-in, so a chord would be spent on "
    "a feature most people have switched off.",
    "tools.voice_command": "The user binds it: a push-to-talk key has to be one "
    "their hands are free for, and that is personal.",
    "tools.voice_conversation": "As voice_command: the user binds it, because a push-to-talk key "
    "has to be one their hands are free for.",
    "tools.voice_wakeword": "As voice_command: the user binds it, and a wake word is a thing "
    "many people switch off entirely.",
    "format.blockquote": "Merged into Quote Lines (Ctrl+Shift+Q) in 2026-09: the two "
    "wrote the identical '> ' in Markdown. The menu row stays.",
    "format.quick_insert": "Reached another way: the palette and the Insert menu. A "
    "chord for 'insert something' has nothing to name.",
    "format.new_abbreviation_from_clipboard": "Reached another way: the Abbreviations "
    "manager, where the clipboard's text is already on screen to check.",
    "navigate.go_to_page": "Reached another way: one Go To window answers line, page "
    "and bookmark (2026-09), so the page-only door closed.",
    "tools.ai_grammar_style": "Deliberately vacated 2026-09 under rule 7: an AI verb "
    "does not hold an editor chord. The AI menu reaches it.",
    "tools.ai_thesaurus": "Deliberately vacated 2026-09 under rule 7; the AI menu "
    "reaches it, and Shift+F7 is the non-AI thesaurus.",
    "tools.ai_translate_selection": "Deliberately vacated 2026-09 under rule 7; the "
    "AI menu reaches it.",
    "github.configure_branch_protection": "Reached another way, and rule 7: a "
    "repository setting is not an editor command.",
    "tools.voice_status": "The user binds it: whether a spoken status readout is "
    "worth a chord depends entirely on whether you use voice at all.",
}


def _editor_command_ids() -> set[str]:
    """Every id in DEFAULT_KEYMAP, which is the editor's own command table."""
    return set(DEFAULT_KEYMAP)


def _is_editor_command(command_id: str) -> bool:
    return not any(command_id.startswith(prefix) for prefix in NOT_EDITOR_COMMANDS)


def test_every_editor_command_has_a_key_or_a_written_reason() -> None:
    unbound = {
        command_id
        for command_id, chord in DEFAULT_KEYMAP.items()
        if not str(chord or "").strip() and _is_editor_command(command_id)
    }
    undocumented = sorted(unbound - set(UNBOUND_WITH_REASON))
    assert not undocumented, (
        "commands with no key and no reason (rule 8) -- give each a chord, a row in "
        "UNBOUND_WITH_REASON, or a family in NOT_EDITOR_COMMANDS:\n  " + "\n  ".join(undocumented)
    )


def test_every_not_editor_family_has_a_command_in_it() -> None:
    """A prefix that matches nothing is an exemption nobody is using."""
    empty = sorted(
        prefix
        for prefix in NOT_EDITOR_COMMANDS
        if not any(command_id.startswith(prefix) for command_id in DEFAULT_KEYMAP)
    )
    assert not empty, "exemptions for families that no longer exist:\n  " + "\n  ".join(empty)


def test_every_family_exemption_cites_its_argument() -> None:
    for prefix, reason in sorted(NOT_EDITOR_COMMANDS.items()):
        assert len(reason) > 30, f"{prefix}: the exemption needs an argument"


def test_the_reason_table_does_not_outlive_its_rows() -> None:
    """A command that has since been given a key must lose its excuse."""
    stale = sorted(
        command_id
        for command_id in UNBOUND_WITH_REASON
        if str(DEFAULT_KEYMAP.get(command_id, "") or "").strip()
    )
    assert not stale, (
        "these have a default chord now, so their UNBOUND_WITH_REASON rows are "
        "stale:\n  " + "\n  ".join(stale)
    )


def test_every_reason_names_a_command_that_exists() -> None:
    unknown = sorted(set(UNBOUND_WITH_REASON) - _editor_command_ids())
    assert not unknown, "reasons for commands that are not in the keymap:\n  " + "\n  ".join(
        unknown
    )


def test_a_reason_is_a_sentence_not_a_shrug() -> None:
    for command_id, reason in sorted(UNBOUND_WITH_REASON.items()):
        assert len(reason) > 40, f"{command_id}: the reason has to be an argument"
        assert reason.strip().endswith((".", "!")), command_id


# -- gate 2: a Quillin may not claim an editor chord ----------------------------


def _editor_chords() -> dict[str, str]:
    """``normalised chord -> command id`` for everything the editor binds."""
    claimed: dict[str, str] = {}
    for mapping in (DEFAULT_KEYMAP, DEFAULT_ALIASES):
        for command_id, chord in mapping.items():
            text = str(chord or "").strip()
            if text:
                claimed.setdefault(text.replace(" ", "").lower(), command_id)
    return claimed


def _bundled_manifests() -> list[tuple[str, dict[str, object]]]:
    found: list[tuple[str, dict[str, object]]] = []
    root = _QUILL / "quillins_bundled"
    for path in sorted(root.rglob("manifest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            found.append((path.relative_to(_ROOT).as_posix(), data))
    return found


def _declared_hotkeys(manifest: dict[str, object]) -> list[str]:
    """Every chord a manifest asks for, whatever shape it declares them in."""
    chords: list[str] = []
    raw = manifest.get("hotkeys")
    if isinstance(raw, dict):
        chords.extend(str(value) for value in raw.values())
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, str):
                chords.append(entry)
            elif isinstance(entry, dict):
                for key in ("key", "chord", "binding", "hotkey"):
                    if key in entry:
                        chords.append(str(entry[key]))
                        break
    for command in manifest.get("commands", []) or []:
        if isinstance(command, dict):
            for key in ("hotkey", "key", "chord", "binding"):
                if key in command:
                    chords.append(str(command[key]))
                    break
    return [chord for chord in chords if chord.strip()]


def test_no_bundled_quillin_claims_a_chord_the_editor_binds() -> None:
    claimed = _editor_chords()
    clashes: list[str] = []
    for relative, manifest in _bundled_manifests():
        for chord in _declared_hotkeys(manifest):
            key = chord.replace(" ", "").lower()
            owner = claimed.get(key)
            if owner is not None:
                clashes.append(f"{relative}: {chord} is already {owner}")
    assert not clashes, (
        "a Quillin and the editor claiming one chord means one of them silently "
        "never fires:\n  " + "\n  ".join(clashes)
    )


def test_the_quillin_scan_is_actually_looking_at_something() -> None:
    """A scanner that finds no manifests passes every extension ever written."""
    manifests = _bundled_manifests()
    assert len(manifests) >= 5, f"only {len(manifests)} bundled manifests found"
