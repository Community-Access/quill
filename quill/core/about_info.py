"""Structured data for the About QUILL for All dialog.

The dialog used to assemble its content from a giant Markdown blob inside
``MainFrame._about_markdown``. JAWS in Forms mode read the flattened result
as one undifferentiated blob, so the version never surfaced as a navigable
element and the dialog appeared to be a no-op (#260).

This module splits the data plumbing out of the UI: :func:`gather_about_info`
collects everything the dialog needs into a single :class:`AboutInfo`
dataclass, and ``quill/ui/info_pages.py::show_about_quill_native`` renders
that dataclass into a ``wx.Notebook`` with Overview / Dependencies / Links
tabs plus Visit / Copy buttons.

The displayed version and channel come from the generated
:mod:`quill._build_info` module (when present) via
:mod:`quill.build_info`; the About dialog and crash reports always show
the same string because they read the same file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.branding import (
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_LICENSE_NAME,
    APP_ORGANIZATION,
    INDEPENDENCE_NOTICE,
)
from quill.build_info import get_short_version, get_support_info

# Org links shown on the Overview tab. Mirrors ``MainFrame._ABOUT_LINKS``.
_DEFAULT_ORG_LINKS: tuple[tuple[str, str], ...] = (
    ("Community Access", "https://community-access.org"),
    ("Blind Information Technology Solutions (BITS)", "https://bits-acb.org"),
    ("Techopolis", "https://techopolis.app"),
    ("GLOW (Community Access)", "https://letitglow.app"),
    ("AccessibleApps (Christopher Toth)", "https://github.com/accessibleapps"),
)

# Project + contributor profile links shown on the Links tab.
_DEFAULT_GITHUB_LINKS: tuple[tuple[str, str], ...] = (
    ("QUILL on GitHub", "https://github.com/Community-Access/quill"),
    ("Community Access on GitHub", "https://github.com/Community-Access"),
    ("Taylor Arndt on GitHub", "https://github.com/taylorarndt"),
    ("Michael Doise on GitHub", "https://github.com/mikedoise"),
    ("Becky K on GitHub", "https://github.com/BeckyK102125"),
    ("Doug Langley on GitHub", "https://github.com/douglangley"),
    ("Kelly Ford on GitHub", "https://github.com/kellylford"),
    (
        "Kelly Ford: Image Description Toolkit",
        "https://github.com/kellylford/Image-Description-Toolkit",
    ),
    (
        "Kelly Ford: QuickMail (accessible IMAP client)",
        "https://github.com/kellylford/QuickMail",
    ),
    ("Kelly Ford: RSSQuick (accessible RSS reader)", "https://github.com/kellylford/rssquick"),
    (
        "Kelly Ford: ChatViewer (Copilot Chat viewer)",
        "https://github.com/kellylford/ChatViewer",
    ),
    (
        "wx-accessible-webview on GitHub",
        "https://github.com/Community-Access/wx-accessible-webview",
    ),
)

_OVERVIEW_PARAGRAPHS: tuple[str, ...] = (
    "{product_name} {version} {channel} is a screen-reader-first writing and document "
    f"environment for Windows and Mac from {APP_ORGANIZATION}.",
    "With sincere thanks to our contributors and beta testers: Techopolis, "
    "Taylor Arndt, Michael Doise, Kayla Bentas, Shane Popplestone, Doug Langley, "
    "Becky K, and Kelly Ford.",
    "Special thanks to Kelly Ford (@kellylford, https://github.com/kellylford) "
    "for contributing the Vision Prompt Library in QUILL 0.6.0 - 12 "
    "IDT-evaluated image description styles, the retry-in-dialog workflow, and "
    "the Manage Image Prompts dialog. Kelly is also the creator of the Image "
    "Description Toolkit (https://github.com/kellylford/Image-Description-Toolkit), "
    "an independent project for accessible image interaction that everyone in "
    "the accessibility space should know about. His other screen-reader-first "
    "tools include QuickMail, RSSQuick, and ChatViewer.",
    "Special thanks to AccessibleApps (Christopher Toth, "
    "https://github.com/accessibleapps) for the open-source accessibility "
    "libraries that QUILL builds on: app_updater, smart_list, accessible_output2, "
    "html_to_text, app_elements, platform_utils, and keyboard_handler.",
    "BITS Whisperer brings speech and dictation integration to QUILL, arriving "
    "in phases: a speech-model manager with machine-aware recommendations, a "
    "provider center with local-first and cloud planning, readiness checks, and "
    "a download queue. Bundled Read Aloud voices (DECtalk and eSpeak NG) play "
    "immediately with no downloads; Piper and Kokoro models install through "
    "the Speech Center.",
)

_BIT_WHISPERER_PARA = (
    "BITS Whisperer brings speech and dictation integration to QUILL, arriving "
    "in phases: a speech-model manager with machine-aware recommendations, a "
    "provider center with local-first and cloud planning, readiness checks, and "
    "a download queue. Bundled Read Aloud voices (DECtalk and eSpeak NG) play "
    "immediately with no downloads; Piper and Kokoro models install through "
    "the Speech Center."
)


@dataclass(frozen=True)
class Link:
    """A single named URL."""

    name: str
    url: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Link name must not be empty")
        if not self.url.strip():
            raise ValueError(f"Link {self.name!r} has no URL")
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError(f"Link {self.name!r} URL must be http(s); got {self.url!r}")


@dataclass(frozen=True)
class DependencyRow:
    """One row of the Dependencies tab."""

    name: str
    scope: str
    version: str
    license: str
    homepage: str
    declared: str
    notes: str = ""
    source: str = ""

    @classmethod
    def from_compliance_row(cls, row: dict[str, str]) -> DependencyRow:
        return cls(
            name=str(row.get("name", "")),
            scope=str(row.get("scope", "")),
            version=str(row.get("version", "")),
            license=str(row.get("license", "")),
            homepage=str(row.get("homepage", "")),
            declared=str(row.get("declared", "")),
            notes=str(row.get("notes", "")),
            source=str(row.get("source", "")),
        )


@dataclass(frozen=True)
class AboutInfo:
    """Everything the About dialog needs to render.

    The UI consumes this dataclass directly. There is no Markdown
    intermediate - each tab reads only the fields it cares about so screen
    readers can navigate cleanly through headings, lists, and links.
    """

    product_name: str
    version: str
    display_version: str
    channel: str
    tagline: str
    overview_paragraphs: tuple[str, ...]
    glow_summary: str
    org_links: tuple[Link, ...]
    github_links: tuple[Link, ...]
    contributors: tuple[Link, ...]
    dependencies: tuple[DependencyRow, ...]
    bundled_components: tuple[DependencyRow, ...]
    dependencies_available: bool
    copyright: str = APP_COPYRIGHT
    license_name: str = APP_LICENSE_NAME
    independence_notice: str = INDEPENDENCE_NOTICE
    support_info: str = ""

    def headline(self) -> str:
        """The first thing JAWS/NVDA should read on the Overview tab."""
        return f"{self.product_name} {self.display_version}"


def _load_contributors() -> tuple[Link, ...]:
    from quill.core.contributors import CONTRIBUTORS

    seen: set[str] = set()
    out: list[Link] = []
    for name, url in CONTRIBUTORS:
        if url in seen:
            continue
        seen.add(url)
        try:
            out.append(Link(name=name, url=url))
        except ValueError:
            continue
    return tuple(out)


def _load_org_links() -> tuple[Link, ...]:
    out: list[Link] = []
    seen: set[str] = set()
    for name, url in _DEFAULT_ORG_LINKS:
        if url in seen:
            continue
        seen.add(url)
        out.append(Link(name=name, url=url))
    return tuple(out)


def _load_github_links() -> tuple[Link, ...]:
    out: list[Link] = []
    seen: set[str] = set()
    for name, url in _DEFAULT_GITHUB_LINKS:
        if url in seen:
            continue
        seen.add(url)
        out.append(Link(name=name, url=url))
    return tuple(out)


def _load_dependencies(pyproject_path: Path) -> tuple[DependencyRow, ...]:
    if not pyproject_path.exists():
        return ()
    from quill.core.compliance import build_dependency_notices

    rows = build_dependency_notices(pyproject_path)
    return tuple(DependencyRow.from_compliance_row(row) for row in rows)


def _load_bundled() -> tuple[DependencyRow, ...]:
    from quill.core.compliance import bundled_component_notices

    rows = bundled_component_notices()
    return tuple(DependencyRow.from_compliance_row(row) for row in rows)


def _load_glow_summary() -> str:
    try:
        from quill.core.glow import glow_engine_version_summary

        return glow_engine_version_summary()
    except Exception:
        return "GLOW engine: unknown"


def gather_about_info(
    *,
    version: str | None = None,
    display_version: str | None = None,
    channel: str | None = None,
    product_name: str | None = None,
    pyproject_path: Path | None = None,
    contributors: tuple[Link, ...] | None = None,
    org_links: tuple[Link, ...] | None = None,
    github_links: tuple[Link, ...] | None = None,
    dependency_loader: Callable[[Path], tuple[DependencyRow, ...]] | None = None,
    bundled_loader: Callable[[], tuple[DependencyRow, ...]] | None = None,
    glow_summary: str | None = None,
    support_info: str | None = None,
) -> AboutInfo:
    """Build an :class:`AboutInfo` from the canonical sources.

    All parameters are injectable so tests can supply deterministic data
    without needing a real ``pyproject.toml`` or the GLOW engine present.

    When ``version`` is not supplied, the function reads the generated
    :mod:`quill.build_info` module; ``quill/__init__.py::__version__`` is
    the fallback. The same source feeds :func:`get_support_info`, so the
    About dialog and the clipboard block always agree.
    """

    resolved_pyproject = pyproject_path if pyproject_path is not None else _default_pyproject_path()
    dep_loader = dependency_loader or _load_dependencies
    bundle_loader = bundled_loader or _load_bundled
    dependencies = dep_loader(resolved_pyproject)
    bundled = bundle_loader()

    short = display_version or get_short_version()
    resolved_channel = channel or _resolve_channel()
    resolved_version = version or __version__
    resolved_product = product_name or APP_DISPLAY_NAME
    resolved_support = support_info if support_info is not None else get_support_info()

    return AboutInfo(
        product_name=resolved_product,
        version=resolved_version,
        display_version=short,
        channel=resolved_channel,
        tagline=(
            f"{APP_DESCRIPTION} {resolved_product} helps people write, edit, "
            "convert, compare, and publish documents in a screen-reader-friendly "
            "environment."
        ),
        overview_paragraphs=tuple(
            p.format(product_name=resolved_product, version=short, channel=resolved_channel)
            if "{" in p
            else p
            for p in _OVERVIEW_PARAGRAPHS
        ),
        glow_summary=glow_summary if glow_summary is not None else _load_glow_summary(),
        org_links=org_links if org_links is not None else _load_org_links(),
        github_links=github_links if github_links is not None else _load_github_links(),
        contributors=contributors if contributors is not None else _load_contributors(),
        dependencies=dependencies,
        bundled_components=bundled,
        dependencies_available=resolved_pyproject.exists(),
        support_info=resolved_support,
    )


def _resolve_channel() -> str:
    """Return the channel from generated build info, or 'Release' as a safe fallback."""
    try:
        from quill import _build_info  # type: ignore[attr-defined]

        raw = str(getattr(_build_info, "CHANNEL", "stable")).lower()
    except Exception:
        raw = "stable"
    if raw == "stable":
        return "Release"
    return raw.capitalize()


def _default_pyproject_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
