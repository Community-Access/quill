"""Which checkers a document gets, and the one call both editors make.

Checkers are keyed by language: the language profile's name, lower-cased
("python", "c#"), with two refinements a profile cannot express -- a ``.jsonc``
file (and VS Code's settings files) is JSONC, which allows comments, and an
``.xhtml`` file is XML as well as HTML.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from quill.core.problems.builtin import BUILTIN_CHECKERS
from quill.core.problems.model import CheckReport, Problem, sort_problems
from quill.core.problems.outside import (
    NEEDS_A_PROJECT,
    Runner,
    run_outside_checkers,
    tools_for,
)

#: Files that are JSON with comments whatever their extension says.
_JSONC_NAMES = frozenset({
    "settings.json",
    "launch.json",
    "tasks.json",
    "keybindings.json",
    "tsconfig.json",
    "jsconfig.json",
    ".eslintrc.json",
    "devcontainer.json",
})

#: How a language is named in a sentence ("No checker installed for C#").
_LABELS = {
    "jsonc": "JSON with comments",
    "c#": "C#",
    "c++": "C++",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "php": "PHP",
    "html": "HTML",
    "xml": "XML",
    "json": "JSON",
    "toml": "TOML",
    "yaml": "YAML",
    "ini": "INI",
    "csv": "CSV",
    "sql": "SQL",
    "css": "CSS",
    "latex": "LaTeX",
    "powershell": "PowerShell",
}


def language_key(profile_name: str | None, path: Path | None = None) -> str:
    """The checker key for a document: its profile's name, refined by its file name."""
    if path is not None:
        name = path.name.lower()
        if path.suffix.lower() == ".jsonc" or name in _JSONC_NAMES:
            return "jsonc"
    key = (profile_name or "").strip().lower()
    return "plain" if key in {"", "plain text"} else key


def language_label(key: str) -> str:
    return _LABELS.get(key, key.title() if key.islower() else key)


def builtin_languages() -> tuple[str, ...]:
    """Every language checked with nothing installed."""
    return tuple(sorted(BUILTIN_CHECKERS))


def has_checker(key: str) -> bool:
    """True when Check This File has anything at all to try for *key*."""
    return key in BUILTIN_CHECKERS or bool(tools_for(key)) or key == "xhtml"


def check_document(
    text: str,
    *,
    language: str,
    path: Path | None = None,
    modified: bool = True,
    outside: bool = True,
    which: Callable[[str], str | None] = shutil.which,
    run: Runner | None = None,
) -> CheckReport:
    """Check *text* as *language* (a :func:`language_key`) with every checker
    that applies: the built-in one, then any outside tool on the PATH.

    *outside* False is the built-in tier alone, which never starts a process --
    what QUILL Lite uses, and what a test that must not find a real tool asks for.
    """
    keys = [language]
    if path is not None and path.suffix.lower() == ".xhtml":
        keys = ["xml", "html"]
    problems: list[Problem] = []
    ran: list[str] = []
    notes: list[str] = []
    for key in keys:
        builtin = BUILTIN_CHECKERS.get(key)
        if builtin is not None:
            name, checker = builtin
            problems.extend(checker(text, path))
            ran.append(name)
        if outside:
            result = run_outside_checkers(
                text, language=key, path=path, modified=modified, which=which, run=run
            )
            problems.extend(result.problems)
            ran.extend(result.ran)
            notes.extend(result.notes)
            if tools_for(key) and not result.ran and not result.notes and builtin is None:
                missing = f"No checker installed for {language_label(key)}"
                if key in NEEDS_A_PROJECT:
                    missing += f" ({NEEDS_A_PROJECT[key]})"
                notes.append(missing)
    if not ran and not notes:
        notes.append(f"No checker for {language_label(language)}")
    return CheckReport(
        language=language_label(language),
        problems=sort_problems(problems),
        checked_with=tuple(ran),
        notes=tuple(notes),
    )
