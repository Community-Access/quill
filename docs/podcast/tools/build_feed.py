#!/usr/bin/env python3
"""Build the QUILL Cast RSS feed and the accessible episode index page.

Reads ``docs/podcast/episodes.json`` (series + episode metadata),
``docs/podcast/audio/durations.json`` (written by generate_kokoro.py), and the
generated MP3 files (for byte sizes), then writes:

* ``docs/site/podcast/feed.xml`` — RSS 2.0 with iTunes tags, enclosures
  pointing at the ``podcast-v1`` GitHub release assets.
* ``docs/site/podcast/index.html`` — a plain, accessible episode list with
  links to the audio and the full transcripts.
* ``docs/site/podcast/transcripts/<slug>.html`` — one accessible page per
  transcript.

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

_SPEAKER = re.compile(r"^\[(LIAM|JESSICA|PAUSE)\]$")

#: The seven-part curriculum, by inclusive episode-number range.
PARTS: tuple[tuple[str, int, int], ...] = (
    ("Part 1 - First Steps", 1, 6),
    ("Part 2 - The Everyday Editor", 7, 13),
    ("Part 3 - Documents and Formats", 14, 18),
    ("Part 4 - Files and Automation", 19, 20),
    ("Part 5 - Speech", 21, 24),
    ("Part 6 - AI", 25, 28),
    ("Part 7 - Organization, Production, and Trust", 29, 36),
)


def _episode_number(slug: str) -> int:
    match = re.match(r"ep(\d+)", slug)
    return int(match.group(1)) if match else 0


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
        '<header class="site"><div class="wrap"><nav class="site" aria-label="Primary">'
        '<ul><li><a href="/index.html">QUILL home</a></li>'
        f'<li><a href="{prefix}index.html">All episodes</a></li>'
        '<li><a href="/tutorials/index.html">Tutorials</a></li>'
        '<li><a href="/docs/userguide.html">User guide</a></li></ul>'
        "</nav></div></header>\n"
        '<main><div class="wrap">\n' + body + "\n</div></main>\n</body>\n</html>\n"
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
        '<img src="cover.png" '
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


def _rfc2822(iso: str) -> str:
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return email.utils.format_datetime(moment)


def _duration_hms(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _transcript_html(slug: str, title: str, site_title: str, audio_url: str) -> str:
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
    content = (
        f"<h1>{html.escape(title)} - transcript</h1>\n"
        f"<p>{_audio_player(slug, title, audio_url)}</p>\n"
        f'<p><a href="{html.escape(audio_url)}">Download the MP3</a></p>\n'
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

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "transcripts").mkdir(exist_ok=True)

    items: list[str] = []
    index_rows: list[tuple[int, str]] = []
    now = email.utils.format_datetime(datetime.now(UTC))

    for episode in episodes:
        slug = episode["slug"]
        title = episode["title"]
        description = episode["description"]
        audio_url = show["audio_base_url"] + f"{slug}.mp3"
        transcript_url = show["site_url"] + f"transcripts/{slug}.html"
        mp3 = AUDIO_DIR / f"{slug}.mp3"
        size = mp3.stat().st_size if mp3.exists() else 0
        duration = durations.get(slug, 0.0)

        items.append(
            "    <item>\n"
            f"      <title>{html.escape(title)}</title>\n"
            f"      <description>{html.escape(description)} "
            f"Full transcript: {html.escape(transcript_url)}</description>\n"
            f"      <link>{html.escape(transcript_url)}</link>\n"
            f'      <guid isPermaLink="false">quill-cast-{slug}</guid>\n'
            f"      <pubDate>{_rfc2822(episode['pubdate'])}</pubDate>\n"
            f'      <enclosure url="{html.escape(audio_url)}" '
            f'length="{size}" type="audio/mpeg"/>\n'
            f"      <itunes:duration>{_duration_hms(duration)}</itunes:duration>\n"
            f"      <itunes:explicit>false</itunes:explicit>\n"
            "    </item>"
        )
        minutes = f"{duration / 60:.0f} min" if duration else "duration pending"
        index_rows.append((
            _episode_number(slug),
            "<li>"
            f"<h3>{html.escape(title)}</h3>"
            f"<p>{html.escape(description)}</p>"
            f"<p>{_audio_player(slug, title, audio_url)}</p>"
            f'<p><a href="{html.escape(audio_url)}">Download MP3 ({minutes})</a> | '
            f'<a href="transcripts/{slug}.html">Read the transcript</a></p>'
            "</li>",
        ))
        (SITE_DIR / "transcripts" / f"{slug}.html").write_text(
            _transcript_html(slug, title, show["title"], audio_url), encoding="utf-8"
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
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    (SITE_DIR / "feed.xml").write_text(feed, encoding="utf-8")

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
        f'<a class="btn secondary" href="{html.escape(show["site_url"] + "feed.xml")}">Open the feed URL</a></p>\n'
        f"<p>Use the RSS feed in any podcast app, or copy this feed address: "
        f"<code>{html.escape(show['site_url'] + 'feed.xml')}</code></p>\n"
        f"<p>{len(index_rows)} episodes, about {total_minutes} minutes in total. "
        "Every episode has a built-in player below, a download link, and a full "
        "accessible transcript.</p>\n"
        "</section>\n" + "\n".join(sections)
    )
    (SITE_DIR / "index.html").write_text(
        _page_shell(show["title"], body, depth=0), encoding="utf-8"
    )

    print(f"Wrote {SITE_DIR / 'feed.xml'}")
    print(f"Wrote {SITE_DIR / 'index.html'} and {len(episodes)} transcript pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
