"""GATE-SITE-LINKS: every internal link on the published site resolves.

Issue #1558 reported that QUILL Cast episode pages carried broken links, and
the investigation found why nothing had noticed: 32 transcript pages from the
show's old 36-episode numbering were still committed and still served, each
linking an MP3 slug absent from the release -- and no tool anywhere validated a
single href. The tutorials index had the mirror-image defect: two finished
lessons existed in ``docs/tutorials/`` and were simply never linked.

The site a visitor sees is assembled by ``.github/workflows/github-pages.yml``
in three moves: the hand-built shell (``docs/site/**``) copied wholesale, every
``docs/**/*.html`` outside the shell flattened by bare basename into
``/docs/``, and seven governance documents rendered from Markdown at deploy
time. A link checker that reads only the shell would flag ``/docs/userguide.html``
as broken (it is manufactured at deploy), so this gate models that assembly and
then requires every internal ``href`` and ``src`` in the shell to land on a
published file.

External URLs are not fetched -- a network test would flake and this is a unit
suite -- with one exception made *checkable*: the podcast pages address their
own site through the absolute ``https://community-access.github.io/quill/``
prefix, which maps straight back onto the published tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

_ROOT = Path(__file__).resolve().parents[3]
_SITE = _ROOT / "docs" / "site"
_DOCS = _ROOT / "docs"

#: The site's own absolute prefix, as written by the podcast feed builder.
_SELF_PREFIX = "https://community-access.github.io/quill/"

#: What step 3 of the Pages workflow renders at deploy time, keyed by the
#: published name under /docs/, valued by the Markdown source it needs.
_DEPLOY_RENDERED: dict[str, str] = {
    "contributing.html": "docs/CONTRIBUTING.md",
    "governance.html": "docs/GOVERNANCE.md",
    "code-of-conduct.html": "docs/CODE_OF_CONDUCT.md",
    "maintainers.html": "docs/MAINTAINERS.md",
    "security.html": "docs/SECURITY.md",
    "privacy.html": "docs/legal/PRIVACY.md",
    "responsible-ai-use.html": "docs/legal/RESPONSIBLE_AI_USE.md",
}

_HREF = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

#: HTML-escaped markup is *displayed* code -- a guide teaching what an anchor
#: looks like writes ``&lt;a href="address"&gt;`` and that address is prose.
_ESCAPED_MARKUP = re.compile(r"&lt;.*?&gt;", re.DOTALL)


def _published_paths() -> set[str]:
    """Every path the deploy serves, as posix paths relative to the site root."""
    published: set[str] = set()
    for path in _SITE.rglob("*"):
        if path.is_file():
            published.add(path.relative_to(_SITE).as_posix())
    for path in _DOCS.rglob("*.html"):
        if _SITE in path.parents or path.name == "index.html":
            continue
        published.add(f"docs/{path.name}")
    for name, source in _DEPLOY_RENDERED.items():
        if (_ROOT / source).exists():
            published.add(f"docs/{name}")
    return published


def _internal_targets(page: Path, text: str) -> list[tuple[str, str]]:
    """(raw link, resolved site path) for every internal link on the page."""
    base = PurePosixPath(page.relative_to(_SITE).as_posix()).parent
    text = _ESCAPED_MARKUP.sub("", text)
    found: list[tuple[str, str]] = []
    for raw in _HREF.findall(text):
        link = raw.strip()
        if link.startswith(_SELF_PREFIX):
            link = "/" + link[len(_SELF_PREFIX) :]
        if link.startswith(("http://", "https://", "mailto:", "data:", "#")):
            continue
        link = link.split("#", 1)[0].split("?", 1)[0]
        if not link:
            continue
        if link.startswith("/"):
            resolved = PurePosixPath(link.lstrip("/"))
        else:
            resolved = base / link
        # Normalise the ".."s a relative link walks through.
        parts: list[str] = []
        for part in resolved.parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        target = "/".join(parts)
        if not target or link.endswith("/"):
            target = f"{target}/index.html".lstrip("/")
        found.append((raw, target))
    return found


def test_every_internal_link_on_the_site_resolves() -> None:
    published = _published_paths()
    pages = sorted(_SITE.rglob("*.html")) + sorted(_SITE.rglob("*.xml"))
    assert pages, "no site pages found -- the site moved and this gate did not"
    broken: list[str] = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for raw, target in _internal_targets(page, text):
            if target not in published:
                broken.append(f"{page.relative_to(_ROOT).as_posix()}: {raw}")
    assert not broken, (
        "site links that resolve to nothing the deploy publishes. A page that "
        "404s reads, to a visitor, as a product that stopped being maintained:\n  "
        + "\n  ".join(broken)
    )


def test_every_transcript_page_is_a_current_episode() -> None:
    """The 36-to-54 renumbering left 32 orphan transcripts live for months.

    ``build_feed.py`` prunes these now, but the prune only runs when somebody
    rebuilds the feed -- this holds the invariant between builds, in both
    directions: no transcript without an episode, no episode without its
    transcript.
    """
    episodes = json.loads((_DOCS / "podcast" / "episodes.json").read_text(encoding="utf-8"))
    slugs = {episode["slug"] for episode in episodes["episodes"]}
    transcripts = {path.stem for path in (_SITE / "podcast" / "transcripts").glob("*.html")}
    assert transcripts - slugs == set(), (
        "transcript pages for episodes that no longer exist -- every one links "
        f"a dead MP3: {sorted(transcripts - slugs)}"
    )
    assert slugs - transcripts == set(), (
        f"episodes whose transcript page is missing: {sorted(slugs - transcripts)}"
    )


#: Any link at the podcast audio release, whatever the page builds it from.
_PODCAST_AUDIO = re.compile(
    r"https://github\.com/Community-Access/quill/releases/download/podcast-v1/([^\"'<>\s]+)"
)


def _load_build_feed():
    """build_feed.py itself, so the gate applies the builder's own rule."""
    import importlib.util

    path = _DOCS / "podcast" / "tools" / "build_feed.py"
    spec = importlib.util.spec_from_file_location("_podcast_build_feed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _podcast_audio_links() -> list[tuple[str, str]]:
    """(page, linked file name) for every podcast audio link on the site."""
    found: list[tuple[str, str]] = []
    for page in sorted(_SITE.rglob("*.html")) + sorted(_SITE.rglob("*.xml")):
        for name in _PODCAST_AUDIO.findall(page.read_text(encoding="utf-8")):
            found.append((page.relative_to(_ROOT).as_posix(), name))
    return found


def test_podcast_audio_links_are_in_the_manifest() -> None:
    """External audio is outside the link check above, which is how 54 dead
    MP3 links survived it: the ``podcast-v1`` release held 36 files from the
    old numbering, and the four whose names still matched were recordings of
    scripts rewritten since. ``docs/podcast/audio_assets.json`` records what the
    release really holds (refresh_audio_manifest.py); a page may link an MP3
    only when that manifest marks it published for that episode.
    """
    build_feed = _load_build_feed()
    published = {
        build_feed.audio_file_name(slug)
        for slug in build_feed.published_audio(build_feed.load_manifest())
    }
    dead = [f"{page}: {name}" for page, name in _podcast_audio_links() if name not in published]
    assert not dead, (
        "podcast audio links the manifest does not vouch for -- a player that "
        "fails or plays a different episode. Generate and upload the audio, run "
        "docs/podcast/tools/refresh_audio_manifest.py, then build_feed.py:\n  " + "\n  ".join(dead)
    )


def test_podcast_audio_manifest_names_every_current_episode() -> None:
    """The manifest's per-episode file names are derived as build_feed derives
    them, for exactly the episodes in ``episodes.json``. A renamed or added
    episode makes it stale, and a stale manifest could vouch for a recording
    under the wrong slug."""
    build_feed = _load_build_feed()
    manifest = build_feed.load_manifest()
    episodes = json.loads((_DOCS / "podcast" / "episodes.json").read_text(encoding="utf-8"))
    expected = [(e["slug"], build_feed.audio_file_name(e["slug"])) for e in episodes["episodes"]]
    recorded = [(e["slug"], e["file"]) for e in manifest["episodes"]]
    assert recorded == expected, (
        "docs/podcast/audio_assets.json is out of step with episodes.json; run "
        "docs/podcast/tools/refresh_audio_manifest.py"
    )
    assets = {asset["name"] for asset in manifest["assets"]}
    for entry in manifest["episodes"]:
        assert entry["status"] in {"published", "stale", "missing"}, entry
        assert (entry["file"] in assets) == (entry["status"] != "missing"), entry


def test_the_feed_carries_exactly_the_published_episodes() -> None:
    """Podcast apps ignore or mis-show an item with no enclosure, so an
    episode without audio is left out of the feed (its transcript page stays).
    The feed and the manifest must agree in both directions."""
    build_feed = _load_build_feed()
    published = build_feed.published_audio(build_feed.load_manifest())
    feed = (_SITE / "podcast" / "feed.xml").read_text(encoding="utf-8")
    items = re.findall(r"<item>.*?</item>", feed, re.DOTALL)
    assert len(items) == len(published), "rebuild with docs/podcast/tools/build_feed.py"
    assert all("<enclosure " in item for item in items), "an item without audio"
    for slug in published:
        page = (_SITE / "podcast" / "transcripts" / f"{slug}.html").read_text(encoding="utf-8")
        assert build_feed.NOT_PUBLISHED not in page, slug


def test_the_audio_gate_recognises_a_release_link() -> None:
    """A pattern that matches nothing passes every broken page ever built."""
    sample = (
        '<source src="https://github.com/Community-Access/quill/releases/download/'
        'podcast-v1/ep99-nothing.mp3" type="audio/mpeg">'
    )
    assert _PODCAST_AUDIO.findall(sample) == ["ep99-nothing.mp3"]
    build_feed = _load_build_feed()
    stale = {
        "assets": [{"name": "ep01-a.mp3", "size": 5}, {"name": "ep02-b.mp3", "size": 7}],
        "episodes": [
            {"slug": "ep01-a", "file": "ep01-a.mp3", "status": "stale"},
            {"slug": "ep02-b", "file": "ep02-b.mp3", "status": "published"},
            {"slug": "ep03-c", "file": "ep02-b.mp3", "status": "published"},
            {"slug": "ep04-d", "file": "ep04-d.mp3", "status": "published"},
        ],
    }
    # Stale, borrowed (another slug's file) and absent files are all refused.
    assert build_feed.published_audio(stale) == {"ep02-b": 7}


def test_the_gate_is_actually_reading_the_site() -> None:
    """A scan that finds no links passes every broken site ever built."""
    published = _published_paths()
    assert len(published) > 100, f"only {len(published)} published paths modelled"
    total = 0
    for page in _SITE.rglob("*.html"):
        total += len(_internal_targets(page, page.read_text(encoding="utf-8")))
    assert total > 300, f"only {total} internal links found across the site"


def test_the_downloadable_manual_matches_its_source() -> None:
    """The site serves a committed copy of the listen-along manual's EPUB.

    The Pages deploy flattens only ``*.html``, so the EPUB a reading app
    imports is the copy under ``docs/site/docs/`` -- which could silently fall
    behind the rendered original. The render is byte-reproducible
    (SOURCE_DATE_EPOCH), so equality is the right check, not mtimes.
    """
    source = _ROOT / "docs" / "user guide" / "quill-step-by-step.epub"
    served = _SITE / "docs" / "quill-step-by-step.epub"
    assert served.exists(), "the site's copy of the manual EPUB is missing"
    assert source.read_bytes() == served.read_bytes(), (
        "docs/site/docs/quill-step-by-step.epub has drifted from the rendered "
        "original -- re-copy it after re-rendering the manual"
    )
