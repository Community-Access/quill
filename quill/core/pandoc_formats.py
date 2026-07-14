"""Tier-1 Pandoc format registry for QUILL's Import / Export menu (issue #262).

Issue #262 proposes a curated, confidence-based subset of Pandoc formats rather
than exposing every reader/writer. This module is the single source of truth
for that list and the extension -> format lookup the file picker, wizard, and
single-file handlers all share.

Pure logic. No ``wx`` imports. Strict-typed; always in scope for ``mypy``.

Why a hard-coded Tier-1 list rather than ``pandoc --list-input-formats``:

* Tier-1 is a QUILL product decision (see issue #262) and lives in the repo so
  the menu and tests do not depend on which Pandoc build the user has.
* The full Pandoc list is still probed at runtime by :func:`probe_pandoc_version`
  so the wizard can warn about an absent or very-old Pandoc. But the *Tier-1*
  list is intentionally fixed; we do not silently widen it when Pandoc adds a
  format.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# Tier-1 input formats (issue #262). Frozen so callers cannot mutate the
# canonical list; tests assert these names exactly.
TIER1_INPUTS: frozenset[str] = frozenset({
    "markdown",
    "commonmark",
    "gfm",
    "html",
    "docx",
    "odt",
    "rtf",
    "plain_text",
    "csv",
    "epub",
    "latex",
})

# Tier-1 output formats (issue #262). Excludes formats that Pandoc cannot
# reliably produce (PDF import is not supported; see issue #262's "PDF: export
# yes, import no" guidance).
TIER1_OUTPUTS: frozenset[str] = frozenset({
    "markdown",
    "commonmark",
    "gfm",
    "html",
    "docx",
    "odt",
    "rtf",
    "plain_text",
    "epub",
    "pdf",
})


@dataclass(frozen=True, slots=True)
class PandocFormat:
    """A Pandoc format QUILL exposes to users.

    ``name`` is the value passed to ``pandoc --from`` / ``--to``.
    ``display_name`` is the human label used in menus and the wizard.
    ``extensions`` is the canonical set of file extensions for this format,
    in lowercase and including the leading dot.
    ``primary_extension`` is the single preferred extension (e.g. ``.md`` for
    Markdown, ``.html`` for HTML) used to default Save dialogs. It is always a
    member of ``extensions``; ``extensions`` is an unordered set, so callers
    must not rely on ``sorted()`` to pick the preferred one.
    """

    name: str
    display_name: str
    extensions: frozenset[str]
    primary_extension: str


# Ordered by the issue #262 "safest QUILL menu design" recommendation, so the
# menu / wizard show Tier-1 formats in a predictable, screen-reader-friendly
# order. The order is preserved by :data:`TIER1_FORMATS_ORDER`.
_FORMATS: tuple[PandocFormat, ...] = (
    PandocFormat(
        "markdown",
        "Markdown",
        frozenset({".md", ".markdown", ".mdown", ".mkd", ".mkdn"}),
        ".md",
    ),
    PandocFormat(
        "commonmark",
        "CommonMark",
        frozenset({".md", ".markdown"}),
        ".md",
    ),
    PandocFormat(
        "gfm",
        "GitHub-Flavored Markdown",
        frozenset({".md", ".markdown"}),
        ".md",
    ),
    PandocFormat(
        "html",
        "HTML",
        frozenset({".html", ".htm"}),
        ".html",
    ),
    PandocFormat(
        "docx",
        "Word Document",
        frozenset({".docx"}),
        ".docx",
    ),
    PandocFormat(
        "odt",
        "OpenDocument Text",
        frozenset({".odt"}),
        ".odt",
    ),
    PandocFormat(
        "rtf",
        "Rich Text Format",
        frozenset({".rtf"}),
        ".rtf",
    ),
    PandocFormat(
        "plain_text",
        "Plain Text",
        frozenset({".txt"}),
        ".txt",
    ),
    PandocFormat(
        "csv",
        "CSV / TSV Table",
        frozenset({".csv", ".tsv"}),
        ".csv",
    ),
    PandocFormat(
        "epub",
        "EPUB Book",
        frozenset({".epub"}),
        ".epub",
    ),
    PandocFormat(
        "latex",
        "LaTeX / TeX",
        frozenset({".tex", ".ltx", ".latex"}),
        ".tex",
    ),
    # PDF is Tier-1 *output only* (issue #262). It is not registered as an
    # input format; PDF import is intentionally not supported.
    PandocFormat(
        "pdf",
        "PDF Document",
        frozenset({".pdf"}),
        ".pdf",
    ),
)

# Index by format name for O(1) lookups.
_FORMATS_BY_NAME: dict[str, PandocFormat] = {fmt.name: fmt for fmt in _FORMATS}

# Index by extension for path-based lookups. Extensions are normalised to
# lowercase before indexing.
_FORMATS_BY_EXTENSION: dict[str, PandocFormat] = {}
for _fmt in _FORMATS:
    for _ext in _fmt.extensions:
        # First format wins for shared extensions (Markdown has multiple);
        # the order of _FORMATS encodes the precedence (Markdown > CommonMark
        # > GFM).
        _FORMATS_BY_EXTENSION.setdefault(_ext, _fmt)


def formats_for_direction(direction: str) -> tuple[PandocFormat, ...]:
    """Return the ordered Tier-1 formats for ``"import"`` or ``"export"``."""

    if direction == "import":
        allowed = TIER1_INPUTS
    elif direction == "export":
        allowed = TIER1_OUTPUTS
    else:
        raise ValueError(f"direction must be 'import' or 'export', got {direction!r}")
    return tuple(fmt for fmt in _FORMATS if fmt.name in allowed)


def get_format(name: str) -> PandocFormat | None:
    """Return the :class:`PandocFormat` for ``name`` or ``None`` if not Tier-1."""

    return _FORMATS_BY_NAME.get(name)


def pandoc_format_for_path(path: str | Path) -> str | None:
    """Return the Tier-1 Pandoc format name for ``path``, or ``None``.

    Resolution is by file extension (case-insensitive). ``None`` means
    the extension is not associated with any Tier-1 format; callers should
    surface a clear "unsupported format" message rather than guess.
    """

    # ``path`` may be a ``str`` or a ``pathlib.Path``; normalise here.
    suffix = str(path).lower().rsplit(".", 1)
    if len(suffix) != 2:
        return None
    ext = "." + suffix[1]
    fmt = _FORMATS_BY_EXTENSION.get(ext)
    return fmt.name if fmt is not None else None


def extensions_for(name: str) -> frozenset[str]:
    """Return the canonical extensions for ``name``, or an empty frozenset."""

    fmt = _FORMATS_BY_NAME.get(name)
    return fmt.extensions if fmt is not None else frozenset()


def primary_extension_for(name: str) -> str | None:
    """Return the preferred file extension for ``name`` (e.g. ``".md"``).

    Save dialogs use this to default a filename. Returns ``None`` when the
    format is unknown. Unlike ``sorted(extensions_for(name))`` this returns
    the canonical extension (``.md`` for Markdown, ``.html`` for HTML) rather
    than the alphabetically-first one.
    """

    fmt = _FORMATS_BY_NAME.get(name)
    return fmt.primary_extension if fmt is not None else None


def is_editable_in_quill(name: str) -> bool:
    """Return ``True`` if a file converted to ``name`` should be re-opened.

    Per issue #262's single-file post-conversion prompt: when the target
    format is editable in QUILL we offer to open the result in a new window.
    PDF / DOCX / EPUB / ODT / RTF / LaTeX are *producible* but not directly
    editable, so no prompt.
    """

    if name not in TIER1_OUTPUTS:
        return False
    fmt = _FORMATS_BY_NAME.get(name)
    if fmt is None:
        return False
    # Anything ending in plain text or markdown-family is editable. RTF and
    # LaTeX are text-ish but QUILL's editor is a structured-text control,
    # so we exclude them; HTML is editable; CSV/TSV is editable as a table.
    editable = {
        "markdown",
        "commonmark",
        "gfm",
        "html",
        "plain_text",
        "csv",
    }
    return fmt.name in editable


# ---------------------------------------------------------------------------
# Pandoc availability probing (delegates to the existing external_tools layer).
# ---------------------------------------------------------------------------


def probe_pandoc_version() -> str | None:
    """Return the first line of ``pandoc --version`` or ``None`` if absent.

    Thin wrapper over :func:`quill.core.external_tools.get_external_tool_status`
    so the format layer does not need its own subprocess plumbing. The
    external_tools layer already caches the status; this function just
    surfaces the version string the wizard intro page reads aloud.
    """

    from quill.core.external_tools import get_external_tool_status

    try:
        status = get_external_tool_status("pandoc")
    except Exception:  # noqa: BLE001 - external_tools is best-effort
        return None
    if not status.installed:
        return None
    version = status.version
    return f"pandoc {version}" if version else "pandoc"


def reset_probe_cache() -> None:
    """No-op kept for API compatibility with the previous module layout.

    The actual cache lives in :mod:`quill.core.external_tools`; tests that
    need to clear it should call that module's reset hook (if any) directly.
    """


def all_formats() -> Iterable[PandocFormat]:
    """Yield every registered Tier-1 format (import or export)."""

    return tuple(_FORMATS)
