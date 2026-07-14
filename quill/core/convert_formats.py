"""Broader Pandoc format catalogue for the File > Convert File dialog.

The Import / Export menus expose the deliberately small Tier-1 set in
:mod:`quill.core.pandoc_formats`. The standalone *Convert File* dialog is a
different surface: its whole point is to let a user reach as much of Pandoc as
their installed build supports. So this module provides a *hybrid* catalogue:

* :data:`CURATED_OUTPUTS` / :data:`CURATED_INPUTS` -- a hand-picked, ordered,
  screen-reader-friendly list of the formats most people actually want, with
  good labels and canonical output extensions. Shown by default.
* :func:`runtime_output_formats` / :func:`runtime_input_formats` -- probe the
  installed Pandoc (``--list-output-formats`` / ``--list-input-formats``) for
  the long tail. Used by the dialog's "All Pandoc formats" expansion.

Tokens here are *real Pandoc reader / writer names* (``gfm``, ``html5``,
``rst``, ``asciidoc``, ...), so they can be handed straight to
:func:`quill.io.pandoc.convert_file_with_pandoc` without the legacy aliasing
that :data:`quill.io.pandoc.WRITER_MAP` applies to the old three-format wizard.

Pure logic apart from the optional subprocess probe (which delegates to the
``external_tools`` / ``safe_subprocess`` layers). No ``wx`` imports.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Curated catalogue
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConvertFormat:
    """A Pandoc format offered in the Convert File dialog.

    ``token`` is the literal Pandoc reader/writer name (``--from`` / ``--to``).
    ``label`` is the human-facing menu string.
    ``extension`` is the canonical output extension (with leading dot) used to
    name the converted file. For input-only formats it is still the natural
    extension, used only to build file-picker wildcards.
    """

    token: str
    label: str
    extension: str


# Ordered most-common-first. Tokens are valid Pandoc writers.
CURATED_OUTPUTS: tuple[ConvertFormat, ...] = (
    ConvertFormat("gfm", "Markdown (GitHub-Flavored)", ".md"),
    ConvertFormat("commonmark", "Markdown (CommonMark)", ".md"),
    ConvertFormat("markdown", "Markdown (Pandoc)", ".md"),
    ConvertFormat("html5", "HTML", ".html"),
    ConvertFormat("docx", "Word Document", ".docx"),
    ConvertFormat("odt", "OpenDocument Text", ".odt"),
    ConvertFormat("rtf", "Rich Text Format", ".rtf"),
    ConvertFormat("plain", "Plain Text", ".txt"),
    ConvertFormat("epub", "EPUB Book", ".epub"),
    ConvertFormat("pdf", "PDF Document", ".pdf"),
    ConvertFormat("latex", "LaTeX", ".tex"),
    ConvertFormat("rst", "reStructuredText", ".rst"),
    ConvertFormat("asciidoc", "AsciiDoc", ".adoc"),
    ConvertFormat("org", "Org Mode", ".org"),
    ConvertFormat("mediawiki", "MediaWiki", ".wiki"),
    ConvertFormat("dokuwiki", "DokuWiki", ".txt"),
    ConvertFormat("docbook", "DocBook", ".xml"),
    ConvertFormat("texinfo", "Texinfo", ".texi"),
    ConvertFormat("man", "Unix man page", ".man"),
    ConvertFormat("fb2", "FictionBook2", ".fb2"),
    ConvertFormat("opml", "OPML Outline", ".opml"),
    ConvertFormat("jats", "JATS XML", ".xml"),
    ConvertFormat("jira", "Jira wiki markup", ".txt"),
    ConvertFormat("textile", "Textile", ".textile"),
    ConvertFormat("json", "Pandoc JSON AST", ".json"),
)

# Ordered most-common-first. Tokens are valid Pandoc readers.
CURATED_INPUTS: tuple[ConvertFormat, ...] = (
    ConvertFormat("markdown", "Markdown", ".md"),
    ConvertFormat("gfm", "Markdown (GitHub-Flavored)", ".md"),
    ConvertFormat("commonmark", "Markdown (CommonMark)", ".md"),
    ConvertFormat("html", "HTML", ".html"),
    ConvertFormat("docx", "Word Document", ".docx"),
    ConvertFormat("odt", "OpenDocument Text", ".odt"),
    ConvertFormat("rtf", "Rich Text Format", ".rtf"),
    ConvertFormat("epub", "EPUB Book", ".epub"),
    ConvertFormat("latex", "LaTeX", ".tex"),
    ConvertFormat("rst", "reStructuredText", ".rst"),
    ConvertFormat("asciidoc", "AsciiDoc", ".adoc"),
    ConvertFormat("org", "Org Mode", ".org"),
    ConvertFormat("mediawiki", "MediaWiki", ".wiki"),
    ConvertFormat("textile", "Textile", ".textile"),
    ConvertFormat("opml", "OPML Outline", ".opml"),
    ConvertFormat("csv", "CSV Table", ".csv"),
    ConvertFormat("json", "Pandoc JSON AST", ".json"),
)

_OUTPUT_BY_TOKEN: dict[str, ConvertFormat] = {f.token: f for f in CURATED_OUTPUTS}
_INPUT_BY_TOKEN: dict[str, ConvertFormat] = {f.token: f for f in CURATED_INPUTS}

# Map a source-file extension to a Pandoc reader token. Anything not listed
# here is passed to Pandoc without ``--from`` so Pandoc auto-detects it.
_READER_BY_EXTENSION: dict[str, str] = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdown": "markdown",
    ".mkd": "markdown",
    ".html": "html",
    ".htm": "html",
    ".docx": "docx",
    ".odt": "odt",
    ".rtf": "rtf",
    ".epub": "epub",
    ".tex": "latex",
    ".latex": "latex",
    ".rst": "rst",
    ".adoc": "asciidoc",
    ".asciidoc": "asciidoc",
    ".org": "org",
    ".wiki": "mediawiki",
    ".textile": "textile",
    ".opml": "opml",
    ".csv": "csv",
    ".tsv": "csv",
    ".json": "json",
    ".txt": "markdown",
}

# Reasonable output extensions for long-tail writers surfaced by the runtime
# probe. Falls back to ``".{token}"`` then ``".txt"`` (see :func:`extension_for`).
_RUNTIME_OUTPUT_EXTENSION: dict[str, str] = {
    "html": ".html",
    "html4": ".html",
    "html5": ".html",
    "slidy": ".html",
    "slideous": ".html",
    "dzslides": ".html",
    "revealjs": ".html",
    "s5": ".html",
    "epub2": ".epub",
    "epub3": ".epub",
    "markdown_strict": ".md",
    "markdown_github": ".md",
    "markdown_mmd": ".md",
    "markdown_phpextra": ".md",
    "beamer": ".tex",
    "context": ".tex",
    "ms": ".ms",
    "texinfo": ".texi",
    "asciidoctor": ".adoc",
    "muse": ".muse",
    "zimwiki": ".txt",
    "tikiwiki": ".txt",
    "twiki": ".txt",
    "vimwiki": ".wiki",
    "xwiki": ".txt",
    "haddock": ".txt",
    "ipynb": ".ipynb",
    "typst": ".typ",
    "native": ".native",
    "csljson": ".json",
    "biblatex": ".bib",
    "bibtex": ".bib",
    "ansi": ".txt",
}


def label_for(token: str) -> str:
    """Return a friendly label for a Pandoc ``token``.

    Uses the curated label when known, otherwise the raw token (which is what
    a power user reaching into the long tail would recognise anyway).
    """

    fmt = _OUTPUT_BY_TOKEN.get(token) or _INPUT_BY_TOKEN.get(token)
    return fmt.label if fmt is not None else token


def extension_for(token: str) -> str:
    """Return the canonical output extension for a writer ``token``."""

    fmt = _OUTPUT_BY_TOKEN.get(token)
    if fmt is not None:
        return fmt.extension
    runtime = _RUNTIME_OUTPUT_EXTENSION.get(token)
    if runtime is not None:
        return runtime
    # Last resort: a writer we have no mapping for. ``.{token}`` is usually a
    # sane guess (rst -> .rst, org -> .org); fall back to .txt if the token has
    # characters that do not make a clean extension.
    cleaned = token.strip().lower()
    if cleaned and cleaned.isalnum():
        return f".{cleaned}"
    return ".txt"


# Writer tokens whose output QUILL can sensibly re-open in its editor. Used to
# gate the dialog's secondary "Convert and Open" action; binary writers (docx,
# pdf, epub, odt, rtf) only ever land on disk.
_TEXT_OUTPUT_TOKENS: frozenset[str] = frozenset({
    "gfm",
    "commonmark",
    "markdown",
    "markdown_strict",
    "markdown_mmd",
    "markdown_phpextra",
    "markdown_github",
    "html",
    "html4",
    "html5",
    "plain",
})


def is_text_output(token: str) -> bool:
    """Return ``True`` if ``token`` produces text QUILL can open in a new tab."""

    return token in _TEXT_OUTPUT_TOKENS


def reader_for_path(path: str) -> str:
    """Return the Pandoc reader token for a source ``path``, or ``""``.

    An empty string means "let Pandoc auto-detect from the extension".
    """

    lowered = path.lower()
    dot = lowered.rfind(".")
    if dot < 0:
        return ""
    return _READER_BY_EXTENSION.get(lowered[dot:], "")


def input_wildcard() -> str:
    """Return a wx file-dialog wildcard for Convert File source selection."""

    exts = sorted({f.extension for f in CURATED_INPUTS} | set(_READER_BY_EXTENSION))
    patterns = ";".join(f"*{ext}" for ext in exts)
    return f"Supported documents ({patterns})|{patterns}|All files (*.*)|*.*"


# ---------------------------------------------------------------------------
# Runtime probe (hybrid "All Pandoc formats" expansion)
# ---------------------------------------------------------------------------


def _probe_formats(flag: str) -> list[str]:
    """Run ``pandoc <flag>`` and return its tokens, or ``[]`` on any failure."""

    from quill.core.external_tools import get_external_tool_status

    try:
        status = get_external_tool_status("pandoc")
    except Exception:  # noqa: BLE001 - external_tools is best-effort
        return []
    if not status.installed or not status.path:
        return []

    from quill.stability.safe_subprocess import run_subprocess_safely

    try:
        completed = run_subprocess_safely([str(status.path), flag], timeout_seconds=10.0)
    except Exception:  # noqa: BLE001 - probing is best-effort
        return []
    if completed.returncode != 0:
        return []
    tokens = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return sorted(set(tokens))


def runtime_output_formats() -> list[str]:
    """Return every writer the installed Pandoc supports (sorted), or ``[]``."""

    return _probe_formats("--list-output-formats")


def runtime_input_formats() -> list[str]:
    """Return every reader the installed Pandoc supports (sorted), or ``[]``."""

    return _probe_formats("--list-input-formats")


__all__ = [
    "CURATED_INPUTS",
    "CURATED_OUTPUTS",
    "ConvertFormat",
    "extension_for",
    "input_wildcard",
    "is_text_output",
    "label_for",
    "reader_for_path",
    "runtime_input_formats",
    "runtime_output_formats",
]
