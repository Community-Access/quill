"""Local (imported-file) podcasts: turn a folder of audio files, or a
hand-picked set of them, into a new ``is_local`` show with one episode
per file.

Storage is deliberately outside ``app_data_dir()`` -- unlike the main
podcast library file, which QUILL Sync can point at a cloud-synced folder,
local podcasts are explicitly never synced (their whole appeal is "files
already on this machine," and audio files are exactly the kind of large
binary content a sync folder shouldn't carry). The show/episode *records*
for a local show still live in the main library file alongside subscribed
shows today (the same ``PodcastLibrary.shows`` list, gated by
``is_local``) -- giving those records their own non-synced store too,
matching the original architecture sketch's ``local_store.py``, is a
smaller follow-up; what matters more is that the audio files themselves,
the part that would actually bloat or corrupt a sync folder, never land
inside ``app_data_dir()``.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastShow

SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4b", ".m4a", ".flac", ".ogg")


def local_podcasts_root() -> Path:
    """Storage root for imported local-podcast audio files."""
    return Path.home() / ".quill-local" / "podcasts"


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "show"


def _title_from_filename(path: Path) -> str:
    """Best-effort title from a filename; falls back to the stem verbatim
    when nothing meaningful survives cleanup."""
    from quill.core.speech.audiobook import title_from_filename

    guessed = title_from_filename(path)
    return guessed or path.stem


def find_audio_files(paths: list[Path]) -> list[Path]:
    """Expand *paths* (files and/or folders) into a flat, sorted list of
    supported audio files. Folders are scanned non-recursively (one level),
    matching "a whole folder of them" rather than an arbitrary deep walk."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                p
                for p in sorted(path.iterdir())
                if p.is_file() and p.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
            files.append(path)
    return files


def _staged_copy(source: Path, dest_dir: Path) -> Path | None:
    """Copy *source* into *dest_dir*, verified, or ``None`` having cleaned up (R9).

    Copy, verify, *then* let the caller make a record -- the order Earshot's PRD
    insists on, and for the reason it gives: a record created first and a copy that
    failed second leaves a visible row pointing at nothing, which is worse than no
    import at all because the listener then has to work out what it is.

    Returns ``None`` on any failure, having removed whatever it staged, so the next
    launch finds no orphan. Silent about *why* here because the caller is a pure
    function returning a show; the UI path checks room up front, which is where the
    sentence a listener needs actually belongs.
    """
    from quill.core.podcasts.local_import_guard import discard, verify_copy

    dest = dest_dir / source.name
    try:
        already_there = dest.resolve() == source.resolve()
    except OSError:
        already_there = False
    if already_there:
        return dest
    try:
        shutil.copy2(source, dest)
    except OSError:
        discard(dest)
        return None
    if not verify_copy(source, dest):
        discard(dest)
        return None
    return dest


def _episode_for(source: Path, dest: Path) -> PodcastEpisode:
    """One episode from one imported file, named by what the file says (R11).

    Tags first, filename second. A folder of ``track07.mp3`` used to become a show
    of episodes called "Track07" while the files carried a real title, artist and
    duration all along -- the filename is the fallback, not the answer.

    ``read_tags`` never raises and answers empty when ``mutagen`` is absent or the
    tags are corrupt, so a copy of Cast without the extra imports exactly as it
    always did and nothing here has to know why.
    """
    from quill.core.podcasts.local_duplicates import content_hash
    from quill.core.podcasts.local_tags import read_tags

    tags = read_tags(dest)
    return PodcastEpisode(
        guid=uuid.uuid4().hex,
        title=tags.title or _title_from_filename(source),
        audio_url="",
        downloaded_path=str(dest),
        played=False,
        duration_seconds=tags.duration_seconds,
        # The artist is the nearest thing a loose file has to a show, and it is
        # what a cross-show row reads as the second half of "title -- podcast".
        description=tags.artist,
        # Import order, so Personal Audio can list newest-added first. An imported
        # file has no publication date of its own, and taking one from the file's
        # timestamp would sort a 2009 recording below something added today.
        published=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        # The bytes, for duplicate detection (R10): a filename is never a
        # duplicate. Hashed from the copy, which is identical to the original and
        # is the file Cast will still have if the original moves.
        content_hash=content_hash(dest),
        # What the listener calls it, kept for support and a future rename. The
        # managed copy's name is Cast's business; this is theirs.
        source_filename=source.name,
    )


def create_local_show(show_title: str, audio_files: list[Path]) -> PodcastShow:
    """Copy each file in *audio_files* into ``local_podcasts_root()``,
    creating one episode per file. Returns the new show (not yet added to
    any library -- the caller does that)."""
    dest_dir = local_podcasts_root() / _slug(show_title)
    dest_dir.mkdir(parents=True, exist_ok=True)

    episodes: list[PodcastEpisode] = []
    for source in audio_files:
        dest = _staged_copy(source, dest_dir)
        if dest is None:
            continue
        episodes.append(_episode_for(source, dest))
    return PodcastShow(
        id=uuid.uuid4().hex,
        title=show_title,
        feed_url="",
        is_local=True,
        episodes=episodes,
    )


def scan_watched_folder(show: PodcastShow) -> int:
    """Copy in any audio file from *show*'s ``watched_folder`` that isn't
    already one of its episodes (matched by original filename), adding a
    new episode for each. Returns the count of newly added episodes; a
    no-op (returns 0) if the show has no watched folder set or it no
    longer exists."""
    if not show.watched_folder:
        return 0
    folder = Path(show.watched_folder)
    if not folder.is_dir():
        return 0

    known_names = {Path(e.downloaded_path).name for e in show.episodes if e.downloaded_path}
    new_files = [f for f in find_audio_files([folder]) if f.name not in known_names]
    if not new_files:
        return 0

    dest_dir = local_podcasts_root() / _slug(show.title)
    dest_dir.mkdir(parents=True, exist_ok=True)
    added = 0
    for source in new_files:
        dest = _staged_copy(source, dest_dir)
        if dest is None:
            continue
        show.episodes.append(_episode_for(source, dest))
        added += 1
    return added
