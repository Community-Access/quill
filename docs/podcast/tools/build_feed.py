#!/usr/bin/env python3
"""Build the QUILL Cast RSS feed and the accessible episode index page.

Reads ``docs/podcast/episodes.json`` (series + episode metadata),
``docs/podcast/audio_assets.json`` (the audio that really exists on the
``podcast-v1`` release, written by refresh_audio_manifest.py) and, when
present, ``docs/podcast/audio/durations.json`` (written by generate_kokoro.py),
then writes:

* ``docs/site/podcast/feed.xml`` — RSS 2.0 with iTunes tags. Only episodes
  whose audio is published get an ``<item>``; see :func:`published_audio`.
* ``docs/site/podcast/index.html`` — a plain, accessible episode list with
  links to the audio (where it exists) and the full transcripts.
* ``docs/site/podcast/transcripts/<slug>.html`` — one accessible page per
  episode, audio or not.

An episode's audio is linked only when the manifest says its file is on the
release *and* was recorded from the current script. The site once linked 54
MP3s while the release held 36 files from an older numbering, and the four
whose names still matched were recordings of scripts since rewritten; a link
is a promise that pressing play gives you what the page says.

Why an episode without audio is left out of the feed rather than listed with
no ``<enclosure>``: podcast apps treat the enclosure as the episode. Apple
Podcasts and most others drop an enclosure-less item silently, and some show it
as an unplayable row or a download error. Omitting it keeps every app's episode
list honest, while the transcript page stays on the site for readers.

Usage::

    python docs/podcast/tools/build_feed.py
"""

from __future__ import annotations

import email.utils
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PODCAST_ROOT = HERE.parent
REPO_ROOT = PODCAST_ROOT.parent.parent
AUDIO_DIR = PODCAST_ROOT / "audio"
SCRIPTS_DIR = PODCAST_ROOT / "scripts"
SITE_DIR = REPO_ROOT / "docs" / "site" / "podcast"
AUDIO_MANIFEST = PODCAST_ROOT / "audio_assets.json"

#: What an unpublished episode says where its player would be.
NOT_PUBLISHED = "The audio for this episode is not published yet."

_SPEAKER = re.compile(r"^\[(LIAM|JESSICA|PAUSE)\]$")

#: The eight-part curriculum, by inclusive episode-number range. These were
#: the old 36-episode ranges until 2026-10-15, so the index filed episodes 37-54
#: under "More episodes" and put rich formatting under "Speech"; keep them in
#: step with the part list in docs/podcast/README.md.
PARTS: tuple[tuple[str, int, int], ...] = (
    ("Part 1 - First Steps", 1, 7),
    ("Part 2 - The Everyday Editor", 8, 17),
    ("Part 3 - Documents and Formats", 18, 24),
    ("Part 4 - Files and Automation", 25, 27),
    ("Part 5 - Speech and Audio", 28, 33),
    ("Part 6 - AI", 34, 39),
    ("Part 7 - Organization and Production", 40, 51),
    ("Part 8 - Trust, Community, and the Power-User Finish", 52, 54),
)


def _episode_number(slug: str) -> int:
    match = re.match(r"ep(\d+)", slug)
    return int(match.group(1)) if match else 0


def audio_file_name(slug: str) -> str:
    """The release asset name an episode's audio is published under."""
    return f"{slug}.mp3"


def load_manifest(path: Path = AUDIO_MANIFEST) -> dict:
    """The committed audio manifest, or an empty one when it is absent."""
    if not path.exists():
        return {"assets": [], "episodes": []}
    return json.loads(path.read_text(encoding="utf-8"))


def published_audio(manifest: dict) -> dict[str, int]:
    """Map slug -> byte size for every episode whose audio may be linked.

    Three things must all hold: the manifest's entry for the episode says
    ``published`` (refresh_audio_manifest.py marks a file recorded before the
    script last changed as ``stale``), the entry's file is the name
    :func:`audio_file_name` derives today (so a renamed episode never inherits
    another slug's recording), and that file is among the release's assets.
    """
    sizes = {str(asset["name"]): int(asset["size"]) for asset in manifest.get("assets", [])}
    published: dict[str, int] = {}
    for entry in manifest.get("episodes", []):
        slug = str(entry["slug"])
        name = str(entry.get("file", ""))
        if entry.get("status") != "published" or name != audio_file_name(slug):
            continue
        if name in sizes:
            published[slug] = sizes[name]
    return published


def _page_shell(title: str, body: str, *, depth: int = 0) -> str:
    """A site-styled page: QUILL stylesheet, landmark structure, home links."""
    prefix = "../" * depth
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<link rel="stylesheet" href="/assets/style.css">\n'
        '<link rel="alternate" type="application/rss+xml" title="The QUILL Cast" '
        f'href="{prefix}feed.xml">\n'
        "</head>\n<body>\n"
        # A skip link, and a <main> the skip link can actually reach. These pages
        # shipped with neither: a bare <main> with no id, so there was nothing to
        # bypass the nav with (2.4.1) even though every hand-built page on the
        # site has had one all along. tabindex="-1" is the load-bearing half --
        # <main> is not focusable without it, so a skip link pointing at it moves
        # focus nowhere and the next Tab returns to the nav the listener just
        # asked to skip. style.css styles the ring (main[tabindex="-1"]).
        '<a class="skip-link" href="#main">Skip to main content</a>\n'
        '<header class="site"><div class="wrap"><nav class="site" aria-label="Primary">'
        '<ul><li><a href="/index.html">QUILL home</a></li>'
        f'<li><a href="{prefix}index.html">All episodes</a></li>'
        '<li><a href="/tutorials/index.html">Tutorials</a></li>'
        '<li><a href="/docs/userguide.html">User guide</a></li></ul>'
        "</nav></div></header>\n"
        '<main id="main" tabindex="-1"><div class="wrap">\n'
        + body
        + "\n</div></main>\n</body>\n</html>\n"
    )


def _audio_player(slug: str, title: str, audio_url: str) -> str:
    """A native, keyboard-accessible player. preload="none" keeps the episode
    list light — nothing downloads until the listener presses play."""
    return (
        f'<audio controls preload="none" aria-label="Play {html.escape(title)}" '
        f'style="width:100%;max-width:36em">'
        f'<source src="{html.escape(audio_url)}" type="audio/mpeg">'
        f"Your browser does not support the audio element; "
        f'<a href="{html.escape(audio_url)}">download the MP3</a> instead.'
        "</audio>"
    )


def _cover_figure(show: dict[str, object]) -> str:
    cover_url = str(show.get("cover_url") or show["site_url"] + "cover.png")
    cover_alt = str(show.get("cover_alt") or f"{show['title']} cover art.")
    cover_description = str(show.get("cover_description") or "")
    description = ""
    if cover_description:
        description = (
            '<details class="cover-description">\n'
            "<summary>Full cover description</summary>\n"
            f"<p>{html.escape(cover_description)}</p>\n"
            "</details>\n"
        )
    return (
        '<figure class="podcast-cover">\n'
        f'<img src="{html.escape(cover_url)}" '
        f'alt="{html.escape(cover_alt)}" width="3000" height="3000" '
        'loading="eager" decoding="async">\n'
        f"<figcaption>{html.escape(show['title'])} cover art.</figcaption>\n"
        "</figure>\n"
        f"{description}"
    )


def _rss_image_tags(show: dict[str, object]) -> str:
    cover_url = str(show.get("cover_url") or show["site_url"] + "cover.png")
    return (
        "    <image>\n"
        f"      <url>{html.escape(cover_url)}</url>\n"
        f"      <title>{html.escape(show['title'])}</title>\n"
        f"      <link>{html.escape(show['site_url'])}</link>\n"
        "    </image>\n"
        f'    <itunes:image href="{html.escape(cover_url)}"/>\n'
    )


def _availability_sentence(total: int, published: int, minutes: int) -> str:
    """The index page's one plain sentence about what can be heard today."""
    if published == total:
        return (
            f"{total} episodes, about {minutes} minutes in total. Every episode has a "
            "built-in player below, a download link, and a full accessible transcript."
        )
    if published == 0:
        return (
            f"{total} episodes. The audio is not published yet, so the podcast feed "
            "has no episodes for now; every episode already has a full accessible "
            "transcript below."
        )
    return (
        f"{total} episodes. Audio is published for {published} of them so far; those "
        "have a built-in player and a download link below, and only those are in the "
        "podcast feed. Every episode has a full accessible transcript."
    )


def _rfc2822(iso: str) -> str:
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return email.utils.format_datetime(moment)


def _duration_hms(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _transcript_html(slug: str, title: str, site_title: str, audio_url: str | None) -> str:
    lines = (SCRIPTS_DIR / f"{slug}.txt").read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if current and buf:
            body.append(
                f"<p><strong>{html.escape(current.title())}:</strong> "
                + html.escape(" ".join(buf))
                + "</p>"
            )
        buf = []

    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        match = _SPEAKER.match(text)
        if match is None:
            buf.append(text)
            continue
        flush()
        marker = match.group(1)
        if marker == "PAUSE":
            body.append("<hr>")
            current = None
        else:
            current = marker
    flush()
    if audio_url is None:
        audio = f"<p>{NOT_PUBLISHED} The full transcript follows.</p>\n"
    else:
        audio = (
            f"<p>{_audio_player(slug, title, audio_url)}</p>\n"
            f'<p><a href="{html.escape(audio_url)}">Download the MP3</a></p>\n'
        )
    content = (
        f"<h1>{html.escape(title)} - transcript</h1>\n"
        + audio
        + "\n".join(body)
        + '\n<p><a href="../index.html">Back to all episodes</a></p>'
    )
    return _page_shell(f"{title} - transcript - {site_title}", content, depth=1)


def main() -> int:
    meta = json.loads((PODCAST_ROOT / "episodes.json").read_text(encoding="utf-8"))
    show = meta["podcast"]
    episodes = meta["episodes"]
    durations: dict[str, float] = {}
    durations_path = AUDIO_DIR / "durations.json"
    if durations_path.exists():
        durations = json.loads(durations_path.read_text(encoding="utf-8"))
    published = published_audio(load_manifest())
    # A duration is only worth showing for audio somebody can play.
    durations = {slug: secs for slug, secs in durations.items() if slug in published}

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    transcripts_dir = SITE_DIR / "transcripts"
    transcripts_dir.mkdir(exist_ok=True)

    # Prune transcripts for episodes that no longer exist. The 36-episode to
    # 54-episode renumbering left 32 stale pages live on the site, each linking
    # an MP3 slug absent from the release -- a build that only ever adds cannot
    # notice a rename, so removal has to be part of the build.
    current_slugs = {episode["slug"] for episode in episodes}
    for stale in sorted(transcripts_dir.glob("*.html")):
        if stale.stem not in current_slugs:
            stale.unlink()
            print(f"Pruned stale transcript {stale.relative_to(REPO_ROOT)}")

    items: list[str] = []
    index_rows: list[tuple[int, str]] = []
    now = email.utils.format_datetime(datetime.now(UTC))

    for episode in episodes:
        slug = episode["slug"]
        title = episode["title"]
        description = episode["description"]
        transcript_url = show["site_url"] + f"transcripts/{slug}.html"
        transcript_link = f'<a href="transcripts/{slug}.html">Read the transcript</a>'
        audio_url: str | None = None
        if slug not in published:
            # No <item>: see the module docstring for why omission beats an
            # enclosure-less item. The index and transcript still list it.
            index_rows.append((
                _episode_number(slug),
                "<li>"
                f"<h3>{html.escape(title)}</h3>"
                f"<p>{html.escape(description)}</p>"
                f"<p>{NOT_PUBLISHED} {transcript_link}</p>"
                "</li>",
            ))
        else:
            audio_url = show["audio_base_url"] + audio_file_name(slug)
            duration = durations.get(slug, 0.0)
            # An unknown duration is left out, not written as 00:00:00, which
            # some apps show as a zero-length episode.
            duration_tag = (
                f"      <itunes:duration>{_duration_hms(duration)}</itunes:duration>\n"
                if duration
                else ""
            )
            items.append(
                "    <item>\n"
                f"      <title>{html.escape(title)}</title>\n"
                f"      <description>{html.escape(description)} "
                f"Full transcript: {html.escape(transcript_url)}</description>\n"
                f"      <link>{html.escape(transcript_url)}</link>\n"
                f'      <guid isPermaLink="false">quill-cast-{slug}</guid>\n'
                f"      <pubDate>{_rfc2822(episode['pubdate'])}</pubDate>\n"
                f'      <enclosure url="{html.escape(audio_url)}" '
                f'length="{published[slug]}" type="audio/mpeg"/>\n'
                + duration_tag
                + "      <itunes:explicit>false</itunes:explicit>\n"
                "    </item>"
            )
            minutes = f" ({duration / 60:.0f} min)" if duration else ""
            index_rows.append((
                _episode_number(slug),
                "<li>"
                f"<h3>{html.escape(title)}</h3>"
                f"<p>{html.escape(description)}</p>"
                f"<p>{_audio_player(slug, title, audio_url)}</p>"
                f'<p><a href="{html.escape(audio_url)}">Download MP3{minutes}</a> | '
                f"{transcript_link}</p>"
                "</li>",
            ))
        (SITE_DIR / "transcripts" / f"{slug}.html").write_text(
            _transcript_html(slug, title, show["title"], audio_url),
            encoding="utf-8",
            newline="\n",
        )

    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
        'xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{html.escape(show['title'])}</title>\n"
        f"    <link>{html.escape(show['site_url'])}</link>\n"
        f"    <description>{html.escape(show['description'])}</description>\n"
        f"    <language>{show['language']}</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        f'    <atom:link href="{html.escape(show["site_url"] + "feed.xml")}" '
        f'rel="self" type="application/rss+xml"/>\n'
        f"    <itunes:author>{html.escape(show['author'])}</itunes:author>\n"
        f"    <itunes:subtitle>{html.escape(show['subtitle'])}</itunes:subtitle>\n"
        f"    <itunes:summary>{html.escape(show['description'])}</itunes:summary>\n"
        f"    <itunes:explicit>false</itunes:explicit>\n"
        f'    <itunes:category text="{html.escape(show["category"])}"/>\n'
        f"    <itunes:owner><itunes:name>{html.escape(show['author'])}</itunes:name>"
        f"<itunes:email>{html.escape(show['email'])}</itunes:email></itunes:owner>\n"
        + _rss_image_tags(show)
        + "".join(f"{item}\n" for item in items)
        + "  </channel>\n</rss>\n"
    )
    (SITE_DIR / "feed.xml").write_text(feed, encoding="utf-8", newline="\n")

    total_minutes = round(sum(durations.values()) / 60) if durations else 0
    sections: list[str] = []
    for part_title, first, last in PARTS:
        rows = [row for number, row in index_rows if first <= number <= last]
        if not rows:
            continue
        sections.append(
            f"<section>\n<h2>{html.escape(part_title)}</h2>\n<ul>\n"
            + "\n".join(rows)
            + "\n</ul>\n</section>"
        )
    # Any episode outside the known ranges still gets listed, never lost.
    orphans = [
        row
        for number, row in index_rows
        if not any(first <= number <= last for _title, first, last in PARTS)
    ]
    if orphans:
        sections.append(
            "<section>\n<h2>More episodes</h2>\n<ul>\n" + "\n".join(orphans) + "\n</ul>\n</section>"
        )

    body = (
        f"<h1>{html.escape(show['title'])}</h1>\n"
        + _cover_figure(show)
        + f"<p>{html.escape(show['subtitle'])}.</p>\n"
        f"<p>{html.escape(show['description'])}</p>\n"
        "<section>\n"
        f'<h2 id="subscribe">Subscribe</h2>\n'
        '<p class="podcast-subscribe"><a class="btn" href="feed.xml">Subscribe with RSS</a> '
        f'<a class="btn secondary" href="{html.escape(show["site_url"] + "feed.xml")}">'
        "Open the feed URL</a></p>\n"
        f"<p>Use the RSS feed in any podcast app, or copy this feed address: "
        f"<code>{html.escape(show['site_url'] + 'feed.xml')}</code></p>\n"
        f"<p>{_availability_sentence(len(index_rows), len(published), total_minutes)}</p>\n"
        "</section>\n" + "\n".join(sections)
    )
    (SITE_DIR / "index.html").write_text(
        _page_shell(show["title"], body, depth=0), encoding="utf-8", newline="\n"
    )

    print(f"Wrote {SITE_DIR / 'feed.xml'}")
    print(f"Wrote {SITE_DIR / 'index.html'} and {len(episodes)} transcript pages")
    print(
        f"Audio published for {len(published)} of {len(episodes)} episodes; "
        f"the feed lists {len(items)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
