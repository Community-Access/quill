"""Using the listener's own YouTube sign-in, borrowed from their web browser.

Off by default, and the switch lives in Quill Radio's Preferences. When it is
on, every request Quill Radio makes to YouTube through yt-dlp carries the
sign-in the listener's browser already holds -- which is what lets **My
YouTube** (Home, Subscriptions, Watch Later, Liked videos, your own playlists)
answer at all, and what lets an age-restricted or members-only video play for
somebody entitled to it.

### What is stored, and what never is

Only *where* the sign-in comes from: the browser's name (``"firefox"``), or the
path of a ``cookies.txt`` file the listener picked. **No cookie value is ever
copied, stored or logged by Quill.** yt-dlp is handed the browser name or the
file path at the moment of each request and reads the cookies itself, in
memory; nothing it reads is written back (``cookiefile`` is opened read-only
because yt-dlp is never asked to save it -- see :func:`cookie_options`).

The settings file is deliberately left out of Export My Setup: a browser name
and a file path describe *this* computer, and moving them to another one would
point at somebody else's browser or at a file that is not there.

### Why the Chromium browsers can fail

Chrome, Edge, Brave, Opera and Vivaldi lock their cookie database while they
run, and recent versions of Chrome and Edge encrypt it in a way only the
browser itself can open ("app-bound encryption"). yt-dlp reports either case as
an error, and :func:`describe_failure` turns that into one plain sentence that
says what to try: close the browser, use Firefox, or export a cookies.txt file.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "radio-youtube-signin.json"

#: ``(yt-dlp browser name, what the listener reads)``, in the order the choice
#: lists them. Every one is in yt-dlp's ``SUPPORTED_BROWSERS`` on Windows;
#: Safari is not offered because it does not exist there.
BROWSERS: tuple[tuple[str, str], ...] = (
    ("edge", "Microsoft Edge"),
    ("chrome", "Google Chrome"),
    ("firefox", "Mozilla Firefox"),
    ("brave", "Brave"),
    ("opera", "Opera"),
    ("vivaldi", "Vivaldi"),
)

#: The choice's last row: a cookies.txt file instead of a browser.
FILE_SOURCE = "file"

#: Browsers built on Chromium, whose cookie store can be locked or app-bound.
CHROMIUM = frozenset({"edge", "chrome", "brave", "opera", "vivaldi"})

#: The one paragraph Preferences and the user guide both say. Kept here so the
#: two cannot drift into saying different things about privacy.
PRIVACY_NOTE = (
    "When this is on, Quill Radio reads your browser's YouTube sign-in each "
    "time it asks YouTube for something, so My YouTube can show your Home "
    "page, your subscriptions, Watch Later, Liked videos and your playlists. "
    "Quill Radio never copies, saves or logs your sign-in: it only remembers "
    "which browser (or which cookies.txt file) to read, and YouTube sees the "
    "same account it sees when you use that browser. Anyone who can use your "
    "Windows account can already do this, so it opens nothing new. Turn it off "
    "any time and Quill Radio goes back to asking YouTube as a guest."
)


@dataclass(frozen=True, slots=True)
class SignInSettings:
    """Whether to use a sign-in, and where to read it from."""

    enabled: bool = False
    #: A ``BROWSERS`` name, or :data:`FILE_SOURCE`.
    source: str = "firefox"
    #: The cookies.txt path, used only when ``source`` is :data:`FILE_SOURCE`.
    cookies_file: str = ""

    @property
    def source_label(self) -> str:
        if self.source == FILE_SOURCE:
            return "a cookies.txt file"
        return dict(BROWSERS).get(self.source, self.source)


def _path(data_dir: Path | None) -> Path:
    return (data_dir or app_data_dir()) / _FILE_NAME


def load(data_dir: Path | None = None) -> SignInSettings:
    """The stored choice, or the off default. Never raises."""
    try:
        raw = read_json(_path(data_dir), {})
    except OSError:
        return SignInSettings()
    if not isinstance(raw, dict):
        return SignInSettings()
    source = str(raw.get("source", "") or "firefox")
    if source != FILE_SOURCE and source not in dict(BROWSERS):
        source = "firefox"
    return SignInSettings(
        enabled=bool(raw.get("enabled", False)),
        source=source,
        cookies_file=str(raw.get("cookies_file", "") or ""),
    )


def save(settings: SignInSettings, data_dir: Path | None = None) -> None:
    """Write the choice (a name and a path, never a cookie). Best effort."""
    try:
        write_json_atomic(
            _path(data_dir),
            {
                "enabled": settings.enabled,
                "source": settings.source,
                "cookies_file": settings.cookies_file,
            },
        )
    except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
        return


def source_index(settings: SignInSettings) -> int:
    """The choice row for *settings* (browsers first, the file last)."""
    names = [name for name, _label in BROWSERS]
    if settings.source == FILE_SOURCE:
        return len(names)
    return names.index(settings.source) if settings.source in names else 2


def source_from_index(index: int) -> str:
    names = [name for name, _label in BROWSERS]
    return names[index] if 0 <= index < len(names) else FILE_SOURCE


def choice_labels() -> list[str]:
    return [label for _name, label in BROWSERS] + ["A cookies.txt file I choose"]


def is_on(settings: SignInSettings | None = None, *, safe_mode: bool = False) -> bool:
    """Whether requests should carry the sign-in right now."""
    if safe_mode:
        return False
    chosen = settings if settings is not None else load()
    if not chosen.enabled:
        return False
    if chosen.source == FILE_SOURCE:
        return bool(chosen.cookies_file.strip())
    return True


def cookie_options(
    settings: SignInSettings | None = None, *, safe_mode: bool = False
) -> dict[str, object]:
    """The yt-dlp options that carry the sign-in, or ``{}`` when it is off.

    A browser name or a file path -- that is all yt-dlp is given, and all this
    module ever holds. Safe Mode never signs in.
    """
    chosen = settings if settings is not None else load()
    if not is_on(chosen, safe_mode=safe_mode):
        return {}
    if chosen.source == FILE_SOURCE:
        return {"cookiefile": chosen.cookies_file.strip()}
    return {"cookiesfrombrowser": (chosen.source,)}


def describe_failure(error: object, settings: SignInSettings | None = None) -> str:
    """One plain sentence when *error* is the sign-in failing, else ``""``.

    yt-dlp's own wording is technical and points at its issue tracker; what a
    listener needs is what went wrong and what to try next. Matched on the
    phrases yt-dlp actually raises (cookies.py), lower-cased.
    """
    text = str(error or "").lower()
    chosen = settings if settings is not None else load()
    name = chosen.source_label
    locked = "could not copy chrome cookie database" in text or (
        "permission denied" in text and "cookie" in text
    )
    if locked:
        return (
            f"Quill Radio could not read your sign-in from {name}, because {name} "
            "keeps it locked while it is open. Close it and try again, or choose "
            "Firefox or a cookies.txt file in Preferences."
        )
    if "dpapi" in text or "app-bound" in text or "v20" in text or "decrypt" in text:
        return (
            f"{name} protects its sign-in so that only {name} itself can read it, "
            "so Quill Radio cannot use it. Choose Firefox or a cookies.txt file in "
            "Preferences instead."
        )
    if "could not find" in text and "cookies database" in text:
        return (
            f"Quill Radio could not find {name}'s sign-in on this computer. Is it "
            "installed, and have you signed in to YouTube in it?"
        )
    if "cookie" in text and ("no such file" in text or "missing_filename" in text):
        return (
            "The cookies.txt file chosen in Preferences is not there any more. "
            "Choose it again, or choose a browser."
        )
    if "sign in" in text or "login required" in text or "requires authentication" in text:
        return (
            "YouTube wants you signed in for this. Turn on Use my YouTube sign-in "
            "in Preferences, and make sure you are signed in to YouTube in that "
            "browser."
        )
    return ""


__all__ = [
    "BROWSERS",
    "CHROMIUM",
    "FILE_SOURCE",
    "PRIVACY_NOTE",
    "SignInSettings",
    "choice_labels",
    "cookie_options",
    "describe_failure",
    "is_on",
    "load",
    "save",
    "source_from_index",
    "source_index",
]
