"""Which files a spell checker should stay quiet in, by their name alone.

Spell-check-as-you-type is a service in prose and an insult in code. Every
identifier, key, tag and flag in a source file is a word no dictionary has, so
a live checker in ``settings.json`` or ``main.py`` produces a wall of alerts
that are all wrong -- and the cost is not symmetric. A sighted user's eye
skates over a red underline it has learned to distrust; a screen-reader user
pays a spoken interruption, or an earcon, for every single one. The feature
that helps most in an essay is the feature that makes a config file unusable.

Notepad reached the same conclusion when it gained spell check in 2024 and
shipped the same answer: on for prose, off for the file types associated with
coding, decided by extension. This module is that rule, in one wx-free place
both QUILL and QuillLite read, so the two products cannot disagree about what
counts as code.

**By extension, deliberately, and not by sniffing the content.** A rule a
person can predict from the file's name is worth more here than a rule that is
right slightly more often: somebody who opens ``notes.py`` and hears nothing
has to be able to work out *why* without reading the source of the editor.

Two things this is careful about:

* **Markdown is prose.** ``.md`` is where people write, and it is the one
  extension that most looks like code and is not. It is on. Fenced blocks and
  inline code spans inside it are handled where they should be, by
  :mod:`quill.core.spellcheck_live`, which suppresses the region rather than
  the file.
* **An unnamed document is prose.** A new, never-saved document has no
  extension to judge, and the answer that costs least when wrong is to check
  it: a spurious alert in a scratch buffer is a smaller loss than silence in
  the letter somebody is actually writing.

This decides a *default*, never a lock. Both products let the choice be
overridden per document; what this file answers is what to do before anybody
has said anything.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["CODE_SUFFIXES", "is_code_filename", "live_check_default_for"]

#: Extensions whose contents are overwhelmingly identifiers rather than words.
#:
#: Grouped by what they are, so that adding one lands in the right place and a
#: reviewer can see what is claimed. Kept deliberately broad on configuration
#: and data: those are the files where the false-positive rate is highest and
#: the value of a spell check is lowest, because nobody is writing prose in a
#: lock file.
CODE_SUFFIXES: frozenset[str] = frozenset({
    # Compiled and systems languages
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cxx",
    ".hpp",
    ".hxx",
    ".cs",
    ".java",
    ".go",
    ".rs",
    ".swift",
    ".m",
    ".mm",
    ".kt",
    ".kts",
    ".scala",
    ".d",
    ".pas",
    ".f",
    ".f90",
    ".asm",
    ".s",
    # Scripting
    ".py",
    ".pyi",
    ".pyw",
    ".rb",
    ".pl",
    ".pm",
    ".php",
    ".lua",
    ".tcl",
    ".r",
    ".jl",
    ".dart",
    ".groovy",
    ".vb",
    ".vbs",
    # Web and markup that is structure rather than prose
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
    ".html",
    ".htm",
    ".xhtml",
    ".xml",
    ".xsl",
    ".xslt",
    ".svg",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".styl",
    # Shells and build
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".psm1",
    ".psd1",
    ".bat",
    ".cmd",
    ".mk",
    ".cmake",
    ".gradle",
    ".iss",
    ".spec",
    # Configuration and data
    ".json",
    ".jsonc",
    ".json5",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".env",
    ".plist",
    ".reg",
    ".lock",
    ".sql",
    ".graphql",
    ".gql",
    ".proto",
    # Machine output, not authored text
    ".log",
    ".diff",
    ".patch",
    ".map",
    ".csv",
    ".tsv",
})


def is_code_filename(name: str | Path | None) -> bool:
    """True when *name*'s extension marks it as code rather than prose.

    ``None`` and a name with no extension are both prose: see the module
    docstring on why an unnamed document is checked rather than skipped.
    """
    if name is None:
        return False
    suffix = Path(str(name)).suffix.lower()
    return bool(suffix) and suffix in CODE_SUFFIXES


def live_check_default_for(name: str | Path | None) -> bool:
    """Should spell-check-as-you-type start switched on for this file?

    The inverse of :func:`is_code_filename`, named for the question the caller
    is actually asking so no call site has to spell the negation out.
    """
    return not is_code_filename(name)
