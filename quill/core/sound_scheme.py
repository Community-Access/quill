"""Editing a sound scheme: swap one event's sound, save the result, go back.

A **scheme** is what a desktop has always called the thing this edits: a named
set of "when X happens, play Y". QUILL already had the playback half of that --
a pack is a manifest mapping event ids to WAV files
(:mod:`quill.core.sound_pack`) -- and no way at all to change one. You could
choose between two shipped packs and silence individual events, and that was the
whole of it. Somebody who wanted their own sound for Save had to author a pack
by hand, as JSON, in a text editor, and point a settings field at it.

This module is the missing half, and it is deliberately wx-free so the rules can
be tested without a display and reused by both editors.

**Editing is non-destructive until you save.** A :class:`SchemeDraft` holds a
base pack plus a set of overrides -- "this event now plays that file on disk" --
and a set of removals. Nothing is written anywhere until :func:`save_scheme`,
and the base pack is never touched at all: the bundled packs are read-only by
construction, so *Restore Defaults* is not an undo log to be replayed but simply
the absence of an override. That is the whole reason the draft is shaped this
way. A design that copied the pack and edited the copy in place would make
"put it back the way it was" a feature that could fail.

**A saved scheme is an ordinary pack**, in an ordinary directory, with the same
manifest every other pack has. So it can be zipped into a ``.qsp`` and given to
somebody else, opened in a text editor, backed up, or thrown away -- and QUILL
loads it through exactly the path it loads its own packs through, with no
special case anywhere. A format only the app that wrote it can read is a format
that traps the work somebody put into it.

**Every sound that goes in is copied in.** A scheme that pointed at
``C:\\Users\\me\\Downloads\\ding.wav`` would break the first time that folder was
tidied, and would be useless to anyone it was sent to. Copying costs a few
kilobytes and makes the directory the whole truth.
"""

from __future__ import annotations

import json
import re
import shutil
import wave
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "MAX_SOUND_BYTES",
    "MAX_SOUND_SECONDS",
    "SchemeDraft",
    "SchemeError",
    "UserScheme",
    "delete_scheme",
    "describe_sound",
    "read_wave_facts",
    "save_scheme",
    "user_scheme_dir",
    "user_schemes",
    "user_schemes_dir",
    "validate_sound_file",
]

#: The manifest file inside every pack, scheme or otherwise.
_MANIFEST = "manifest.json"

#: Where a user's own schemes live, under their data directory.
_SCHEMES_DIRNAME = "sound_schemes"

#: Refused above this size. An earcon is a fraction of a second of mono audio;
#: anything past a couple of megabytes is a song somebody picked by mistake, and
#: playing it on every save would be a punishment rather than a feature.
MAX_SOUND_BYTES = 2 * 1024 * 1024

#: And above this length, for the same reason stated in time rather than bytes.
#: Generous: some people genuinely want a two-second chime for "document saved".
MAX_SOUND_SECONDS = 10.0


class SchemeError(CodedError):
    """A scheme could not be saved, or a chosen sound could not be used."""

    code = "QUILL-AUDIO-SOUND-SCHEME"


@dataclass(frozen=True, slots=True)
class UserScheme:
    """One scheme the user has saved, as it appears in a chooser."""

    name: str
    path: Path

    @property
    def setting_value(self) -> str:
        """What goes in ``settings.sound_pack_path`` to select this scheme."""
        return str(self.path)


@dataclass(frozen=True, slots=True)
class WaveFacts:
    """What a WAV file turns out to be, for saying out loud before you use it."""

    seconds: float
    channels: int
    sample_rate: int
    bytes: int


@dataclass
class SchemeDraft:
    """A scheme being edited: a base pack, some overrides, some removals.

    ``overrides`` maps an event id to a file **on disk** that the user picked.
    ``removed`` is the set of events they cleared back to nothing at all -- which
    is different from disabling an event (that is a settings concern and lives in
    ``sound_events_disabled``) and different again from restoring the default
    (which is simply dropping the override).

    Three states per event, and they are genuinely three:

    * no override, not removed -- whatever the base pack says, which for a
      bundled pack is the sound QUILL ships;
    * an override -- the file the user chose;
    * removed -- silence, deliberately, even though the base pack has a sound.
    """

    base_events: dict[str, str] = field(default_factory=dict)
    base_dir: Path | None = None
    overrides: dict[str, Path] = field(default_factory=dict)
    removed: set[str] = field(default_factory=set)

    # -- reading ------------------------------------------------------------ #

    def source_for(self, event: str) -> Path | None:
        """The file this event would play, or None for silence."""
        if event in self.overrides:
            return self.overrides[event]
        if event in self.removed:
            return None
        name = self.base_events.get(event)
        if not name or self.base_dir is None:
            return None
        candidate = self.base_dir / name
        return candidate if candidate.is_file() else None

    def is_default(self, event: str) -> bool:
        """Whether this event is untouched -- neither overridden nor removed."""
        return event not in self.overrides and event not in self.removed

    def is_silent(self, event: str) -> bool:
        return self.source_for(event) is None

    @property
    def dirty(self) -> bool:
        """Whether anything has been changed since the draft was made."""
        return bool(self.overrides or self.removed)

    # -- editing ------------------------------------------------------------ #

    def set_sound(self, event: str, path: Path) -> None:
        """Point *event* at *path*. Validates first, so a bad pick never lands."""
        validate_sound_file(path)
        self.overrides[event] = Path(path)
        self.removed.discard(event)

    def silence(self, event: str) -> None:
        """Give *event* no sound at all, even though the base pack has one."""
        self.overrides.pop(event, None)
        self.removed.add(event)

    def restore(self, event: str) -> None:
        """Put *event* back to what the base pack says. Cannot fail."""
        self.overrides.pop(event, None)
        self.removed.discard(event)

    def restore_all(self) -> None:
        """Put every event back. The escape hatch, and it is one line for a
        reason: whatever somebody has done in here, getting out of it must never
        be a sequence of steps that could be got wrong halfway."""
        self.overrides.clear()
        self.removed.clear()


def read_wave_facts(path: Path) -> WaveFacts | None:
    """What *path* is, or None when it is not a readable WAV.

    None rather than an exception: the caller is usually describing a file for a
    person to hear about, and "this is not a sound file QUILL can use" is a
    sentence, not a failure.
    """
    try:
        size = path.stat().st_size
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 1
            return WaveFacts(
                seconds=frames / rate,
                channels=handle.getnchannels(),
                sample_rate=rate,
                bytes=size,
            )
    except (OSError, wave.Error, ValueError, EOFError):
        # EOFError is what the stdlib raises for a *truncated* WAV -- a download
        # that stopped halfway, which is exactly the file somebody browses to and
        # cannot tell from a good one. Without it in this list the Sound Scheme
        # window raises while merely describing a row.
        return None


def validate_sound_file(path: Path) -> WaveFacts:
    """Check that *path* can be an earcon, or raise :class:`SchemeError`.

    Checked here rather than at playback time, because a sound that fails at
    playback fails *silently* -- the event simply makes no noise, and the user
    has no way to tell that from an event they forgot to set. Refusing at the
    moment of choosing is the only point at which the answer can be a sentence.
    """
    path = Path(path)
    if not path.is_file():
        raise SchemeError(f"{path.name} is not a file that exists.")
    facts = read_wave_facts(path)
    if facts is None:
        raise SchemeError(
            f"{path.name} is not a WAV file QUILL can play. Sound schemes use "
            "uncompressed WAV; convert an MP3 or an OGG first."
        )
    if facts.bytes > MAX_SOUND_BYTES:
        raise SchemeError(
            f"{path.name} is {facts.bytes // 1024} kilobytes, and the limit is "
            f"{MAX_SOUND_BYTES // 1024}. An earcon is a fraction of a second."
        )
    if facts.seconds > MAX_SOUND_SECONDS:
        raise SchemeError(
            f"{path.name} is {facts.seconds:.0f} seconds long, and the limit is "
            f"{MAX_SOUND_SECONDS:.0f}. A sound this long would still be playing "
            "when the next one starts."
        )
    return facts


def describe_sound(path: Path | None) -> str:
    """One line about a sound, for a list row or a status line.

    Written to be *heard*: the duration first, because that is the fact that
    decides whether a sound belongs on an event that fires forty times an hour.
    """
    if path is None:
        return "Silent"
    facts = read_wave_facts(path)
    if facts is None:
        return f"{path.name} (cannot be read)"
    milliseconds = int(facts.seconds * 1000)
    if milliseconds < 1000:
        length = f"{milliseconds} ms"
    else:
        length = f"{facts.seconds:.1f} seconds"
    return f"{path.name}, {length}"


def user_schemes_dir(data_dir: Path) -> Path:
    """Where this user's own schemes live."""
    return Path(data_dir) / _SCHEMES_DIRNAME


def user_scheme_dir(data_dir: Path, name: str) -> Path:
    """The directory a scheme called *name* would live in."""
    return user_schemes_dir(data_dir) / _slug(name)


def user_schemes(data_dir: Path) -> list[UserScheme]:
    """Every scheme the user has saved, by display name.

    A directory without a readable manifest is skipped rather than reported: a
    half-written scheme from an interrupted save should not stop the chooser
    from opening, and the user's remedy is to save it again.
    """
    base = user_schemes_dir(data_dir)
    found: list[UserScheme] = []
    if not base.is_dir():
        return found
    for child in sorted(base.iterdir()):
        manifest = child / _MANIFEST
        if not child.is_dir() or not manifest.is_file():
            continue
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = raw.get("name") if isinstance(raw, dict) else None
        found.append(UserScheme(name=str(name or child.name), path=child))
    found.sort(key=lambda scheme: scheme.name.lower())
    return found


def save_scheme(
    draft: SchemeDraft,
    name: str,
    data_dir: Path,
    *,
    author: str = "",
    description: str = "",
) -> Path:
    """Write *draft* out as a scheme called *name*. Returns its directory.

    Every sound is **copied in**, including the ones inherited from the base
    pack. That is what makes the directory the whole truth: it survives the
    bundled pack changing in a later version, it survives the user tidying their
    Downloads folder, and it can be zipped and sent to somebody else. The few
    hundred kilobytes it costs are the price of a scheme that cannot rot.

    Written to a temporary directory and moved into place, so an interrupted
    save leaves the previous version of the scheme intact rather than a
    half-written one. The same rule the rest of the app's writes follow.
    """
    label = name.strip()
    if not label:
        raise SchemeError("A scheme needs a name.")
    target = user_scheme_dir(data_dir, label)
    staging = target.with_name(target.name + ".saving")
    events: dict[str, str] = {}
    try:
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)
        for event in sorted(set(draft.base_events) | set(draft.overrides)):
            source = draft.source_for(event)
            if source is None:
                continue  # removed, or a base entry whose file has gone
            filename = f"{event}{source.suffix.lower() or '.wav'}"
            shutil.copyfile(source, staging / filename)
            events[event] = filename
        manifest = {
            "format": "qsp",
            "version": "1",
            "name": label,
            "author": author or "",
            "description": description or f"A sound scheme saved from QUILL: {label}.",
            "license": "",
            "events": events,
        }
        (staging / _MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if target.exists():
            shutil.rmtree(target)
        staging.replace(target)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        raise SchemeError(f"Could not save the scheme: {error}") from error
    return target


def delete_scheme(scheme: UserScheme) -> None:
    """Remove a saved scheme. Only ever one of the user's own."""
    try:
        shutil.rmtree(scheme.path)
    except OSError as error:
        raise SchemeError(f"Could not delete {scheme.name}: {error}") from error


def _slug(name: str) -> str:
    """A directory name from a display name.

    Conservative on purpose: this becomes a path, and a scheme called "../.."
    must be a folder called something harmless rather than an interesting
    question about where the files went.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", name).strip().strip(".")
    cleaned = re.sub(r"\s+", "-", cleaned).lower()
    return cleaned or "scheme"
