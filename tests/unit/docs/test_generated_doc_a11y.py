"""GATE-DOCA11Y: the two things a Pandoc re-render must not take away.

Both were lost silently once, and neither had anything watching it.

Pandoc's bundled ``styles.html`` partial sets ``table { display: block }``, which
takes the table role out of the accessibility tree in Blink and Gecko -- and the
row and cell roles go with it. 62 keyboard-reference tables in QUILL Lite's user
guide alone read as a flat run of words, on a site whose readers are
overwhelmingly screen-reader users, and nothing reported it because the pages
*look* right.

And the shared template's ``<main>`` had no ``tabindex``, so the skip link every
one of these pages ships moved focus nowhere: ``main:focus`` in the site
stylesheet could never match, and the next Tab went back into the nav the reader
had just asked to skip.

**Asserted at both ends on purpose.** The template alone would pass while every
committed render still carried the old bytes; the renders alone would pass until
somebody regenerated them from an unfixed template. The pair is what makes a
re-render safe.

Excluded: ``archived/`` under the site's docs tree holds frozen historical
renders. They are fixed too, but they are not regenerated, so pinning them here
would only add a tripwire for a file nobody touches.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE = _ROOT / "docs" / "pandoc" / "quill-accessible.html5"
_SITE = _ROOT / "docs" / "site"

#: ``table { ... }`` and nothing else -- not ``table caption {``, not ``.cmp th``.
_TABLE_RULE = re.compile(r"(?<![\w.#-])table\s*\{([^}]*)\}")
_FIRST_MAIN = re.compile(r"<main\b[^>]*>")
_DISPLAY = re.compile(r"display\s*:\s*([\w-]+)")
_PANDOC_META = 'name="generator" content="pandoc'


def _rendered_pages() -> list[Path]:
    """Every committed page rendered through the shared accessible template.

    Keyed on the Pandoc generator meta plus the template's own skip-link rule,
    so the hand-built shell pages under ``docs/site/`` (which are checked
    separately, below) are not this gate's business. Both doc roots are covered:
    the top-level ``docs/`` tree and each standalone app's bundled ``docs/``,
    because ``sync_site_docs.py`` copies one onto the other and a fix applied to
    only one side is a fix that the next sync reverts.
    """
    roots = [_ROOT / "docs"] + sorted((_ROOT / "standalone").glob("*/docs"))
    pages: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.html"):
            parts = path.parts
            if "dist" in parts or "archived" in parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _PANDOC_META in text and ".skip-link:focus { left: 0; }" in text:
                pages.append(path)
    return pages


def _effective_table_display(text: str) -> str | None:
    """The ``display`` a browser ends up applying to ``<table>`` on this page.

    Every ``table { ... }`` rule in document order, last one wins -- which is the
    whole mechanism the fix relies on: the template's override block comes after
    Pandoc's injected partial, at equal specificity.
    """
    value: str | None = None
    for rule in _TABLE_RULE.finditer(text):
        found = _DISPLAY.search(rule.group(1))
        if found:
            value = found.group(1)
    return value


def test_the_template_keeps_both_fixes() -> None:
    text = _TEMPLATE.read_text(encoding="utf-8")
    assert '<main id="main-content" tabindex="-1">' in text, (
        "quill-accessible.html5 lost the tabindex on <main>. Without it the skip "
        "link on every rendered page moves focus nowhere: <main> is not focusable, "
        "so focus stays on the link and the next Tab re-enters the nav."
    )
    display = _effective_table_display(text)
    assert display == "table", (
        "quill-accessible.html5 must end with a `table { display: table }` "
        f"override after Pandoc's $styles.html()$ partial; effective value is "
        f"{display!r}. display:block drops the table role in Blink and Gecko and "
        "takes the row and cell roles with it."
    )


def test_every_rendered_page_has_a_focusable_main() -> None:
    offenders = []
    for path in _rendered_pages():
        text = path.read_text(encoding="utf-8", errors="replace")
        first = _FIRST_MAIN.search(text)
        if first is None or 'tabindex="-1"' not in first.group(0):
            offenders.append(path.relative_to(_ROOT).as_posix())
    assert not offenders, (
        "These pages ship a skip link whose target cannot take focus. Re-render "
        "them through docs/pandoc/quill-accessible.html5:\n  " + "\n  ".join(offenders)
    )


def test_no_rendered_page_strips_its_table_semantics() -> None:
    offenders = []
    for path in _rendered_pages():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _effective_table_display(text) != "table":
            offenders.append(path.relative_to(_ROOT).as_posix())
    assert not offenders, (
        "These pages let Pandoc's `table { display: block }` stand, so every "
        "table on them reads as a flat run of words in NVDA and JAWS. Re-render "
        "them through docs/pandoc/quill-accessible.html5:\n  " + "\n  ".join(offenders)
    )


def test_the_gate_is_actually_reading_the_renders() -> None:
    """A guard against the assertions above passing over an empty list.

    The two sweeps are only meaningful if they found the corpus. The count is a
    floor rather than an equality so that adding a document does not fail it.
    """
    pages = _rendered_pages()
    assert len(pages) >= 200, (
        f"expected the rendered-docs corpus, found {len(pages)} pages -- the "
        "detection keys (the Pandoc generator meta and the template's skip-link "
        "rule) have probably changed shape"
    )


def test_every_hand_built_page_can_reach_its_own_skip_link() -> None:
    """The other half: the site shell, which is written by hand rather than rendered.

    Same defect, different files. ``style.css`` has styled ``main:focus`` since
    the shell was written, and every page shipped a bare ``<main>``, so the rule
    matched nothing and the skip link on all of them was decorative.
    """
    offenders = []
    for path in sorted(_SITE.rglob("*.html")):
        if "archived" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if 'href="#main"' not in text:
            continue
        match = re.search(r"<[a-z]+\b[^>]*\bid=\"main\"[^>]*>", text)
        if match is None:
            offenders.append(f'{path.relative_to(_ROOT).as_posix()} (no id="main" to land on)')
        elif 'tabindex="-1"' not in match.group(0):
            offenders.append(f'{path.relative_to(_ROOT).as_posix()} (id="main" is not focusable)')
    assert not offenders, (
        'A page links to "#main" but focus cannot land there. Add tabindex="-1" '
        "to the element, which adds no tab stop:\n  " + "\n  ".join(offenders)
    )
