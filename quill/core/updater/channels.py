"""Release channels: Stable, Beta and Dev, and where each app's choice is kept.

The channel is a property of the *listing*, not of the program: the same build
moves from Dev to Beta to Stable unchanged (release-channels plan, section 0).
So the channel a person is on is their setting, kept here, and never something
compiled into the app.

**Where it is kept.** One family file, ``channels.json``, in
``%LOCALAPPDATA%\\QuillVille`` for installed copies, or in the portable bundle's
``data`` folder for a portable copy. One file, because "move all my apps
together" is then one write, every app can see which channel its siblings are
on (the shared-runtime rule needs that), and QUILL Lite -- whose own data lives
somewhere else -- is not left out::

    {"version": 1,
     "apps": {"radio": {"channel": "beta", "pending_return": false,
                        "joined_at": "2026-10-03T10:00:00Z", "joined_from": "3.2.0",
                        "snapshot": "C:\\\\...\\\\radio-3.2.0-joined-beta-20261003.qrbackup"}}}

An app with no entry is on Stable. An unreadable file is set aside (renamed
``channels.json.unreadable``) and read as "everything on Stable" -- the one
answer that can never offer somebody a build they did not ask for.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Literal

__all__ = [
    "BETA",
    "CHANNELS",
    "DEV",
    "STABLE",
    "Channel",
    "ChannelState",
    "ChannelsFile",
    "channel_label",
    "channel_meaning",
    "channels_path",
    "family_dir",
    "includes_prereleases",
    "is_riskier",
    "load_channels",
    "save_channels",
    "shown_channel",
    "state_for",
    "update_states",
]

Channel = Literal["stable", "beta", "dev"]

STABLE: Channel = "stable"
BETA: Channel = "beta"
DEV: Channel = "dev"

#: Least risky first; the index is the risk.
CHANNELS: tuple[Channel, ...] = (STABLE, BETA, DEV)

_LABELS: dict[str, str] = {STABLE: "Stable", BETA: "Beta", DEV: "Dev"}

#: The one-line meaning shown beside each choice (plan 2.1), in the family's
#: plain, people-first voice.
_MEANINGS: dict[str, str] = {
    STABLE: (
        "The version we recommend. It has been checked with JAWS and NVDA, "
        "and it is what most people use."
    ),
    BETA: (
        "New features a few weeks early. Mostly finished, but some things may not work right yet."
    ),
    DEV: (
        "Builds from the work in progress, sometimes several a week. Things "
        "will break. Only choose this if a developer asked you to, or you "
        "enjoy testing."
    ),
}

_FILE_NAME = "channels.json"
_SCHEMA_VERSION = 1


def channel_label(channel: str) -> str:
    """``"Beta"`` for ``"beta"``; an unknown value reads as Stable."""
    return _LABELS.get(str(channel), _LABELS[STABLE])


def channel_meaning(channel: str) -> str:
    return _MEANINGS.get(str(channel), _MEANINGS[STABLE])


def normalize_channel(value: object) -> Channel:
    text = str(value or "").strip().lower()
    if text == BETA:
        return BETA
    if text == DEV:
        return DEV
    return STABLE


def is_riskier(target: str, current: str) -> bool:
    """True when *target* is a less finished channel than *current*."""
    return CHANNELS.index(normalize_channel(target)) > CHANNELS.index(normalize_channel(current))


@dataclass(frozen=True)
class ChannelState:
    """One app's channel and the facts that go with it."""

    channel: Channel = STABLE
    #: On Beta or Dev, asked to come back to Stable, and waiting for Stable to
    #: reach the version installed (plan 5.3). Offers stop meanwhile.
    pending_return: bool = False
    #: While waiting, keep taking Beta fixes anyway (plan 5.3; off by default).
    keep_beta_while_waiting: bool = False
    joined_at: str = ""
    joined_from: str = ""
    #: The copy of this app's settings saved when it joined Beta or Dev.
    snapshot: str = ""
    #: Who set it: "you" (the Release Channel dialog), "installed" (the app
    #: found it was a pre-release with nothing stored), "legacy" (QUILL's old
    #: Get beta updates box).
    set_by: str = ""

    @property
    def is_stable(self) -> bool:
        return self.channel == STABLE

    def to_json(self) -> dict[str, object]:
        data = asdict(self)
        # Keep the file small and readable: defaults are left out.
        defaults = asdict(ChannelState())
        return {key: value for key, value in data.items() if value != defaults[key]} | {
            "channel": self.channel
        }

    @classmethod
    def from_json(cls, raw: object) -> ChannelState:
        if not isinstance(raw, dict):
            return cls()
        return cls(
            channel=normalize_channel(raw.get("channel")),
            pending_return=bool(raw.get("pending_return", False)),
            keep_beta_while_waiting=bool(raw.get("keep_beta_while_waiting", False)),
            joined_at=str(raw.get("joined_at") or ""),
            joined_from=str(raw.get("joined_from") or ""),
            snapshot=str(raw.get("snapshot") or ""),
            set_by=str(raw.get("set_by") or ""),
        )


@dataclass(frozen=True)
class ChannelsFile:
    """The whole ``channels.json``: every app's :class:`ChannelState`."""

    apps: dict[str, ChannelState] = field(default_factory=dict)
    #: Keys a newer build wrote that this one does not understand; kept and
    #: written back so an older app never erases a newer one's facts.
    extra: dict[str, object] = field(default_factory=dict)

    def state(self, app_key: str) -> ChannelState:
        return self.apps.get(app_key, ChannelState())

    def has(self, app_key: str) -> bool:
        return app_key in self.apps

    def with_state(self, app_key: str, state: ChannelState) -> ChannelsFile:
        apps = dict(self.apps)
        apps[app_key] = state
        return replace(self, apps=apps)

    def to_json(self) -> dict[str, object]:
        return {
            **self.extra,
            "version": _SCHEMA_VERSION,
            "apps": {key: self.apps[key].to_json() for key in sorted(self.apps)},
        }

    @classmethod
    def from_json(cls, raw: object) -> ChannelsFile:
        if not isinstance(raw, dict):
            raise ValueError("channels.json must hold a JSON object")
        apps_raw = raw.get("apps", {})
        if not isinstance(apps_raw, dict):
            raise ValueError("channels.json 'apps' must be an object")
        apps = {str(key): ChannelState.from_json(value) for key, value in apps_raw.items()}
        extra = {key: value for key, value in raw.items() if key not in ("version", "apps")}
        return cls(apps=apps, extra=extra)


# -- where it lives -----------------------------------------------------------


def family_dir() -> Path:
    """The QuillVille family folder ``channels.json`` (and the history) live in.

    Dev builds honour ``QUILL_FAMILY_DIR``, and follow ``QUILL_DATA_DIR`` into a
    ``QuillVille`` folder beside the test's own data, so a test can never read
    or write a developer's real channel. A portable copy keeps it in its own
    ``data`` folder: nothing a portable copy does may land on the host.
    """
    from quill.core import paths

    if paths._DEV_BUILD:
        family = os.environ.get("QUILL_FAMILY_DIR", "").strip()
        if family:
            return Path(family).expanduser()
        if os.environ.get("QUILL_DATA_DIR", "").strip():
            return paths.app_data_dir() / "QuillVille"
    try:
        if paths.portable_bundle_root() is not None:
            return paths.app_data_dir()
    except (OSError, RuntimeError):
        pass
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "QuillVille"
    return paths.app_data_dir() / "QuillVille"


def channels_path() -> Path:
    return family_dir() / _FILE_NAME


# -- reading and writing --------------------------------------------------------


def load_channels(path: Path | None = None) -> ChannelsFile:
    """Read ``channels.json``; a missing file is everything on Stable.

    An unreadable one is renamed aside (``.unreadable``) so a person or a
    support email can still look at it, and read as everything on Stable.
    """
    target = path or channels_path()
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ChannelsFile()
    except OSError:
        return ChannelsFile()
    try:
        return ChannelsFile.from_json(json.loads(text))
    except (ValueError, TypeError):
        try:
            os.replace(target, target.with_name(target.name + ".unreadable"))
        except OSError:
            pass
        return ChannelsFile()


def save_channels(data: ChannelsFile, path: Path | None = None) -> None:
    """Write ``channels.json`` atomically (temp file, then rename)."""
    from quill.core.storage import write_json_atomic

    target = path or channels_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target, data.to_json())


def state_for(app_key: str, path: Path | None = None) -> ChannelState:
    """*app_key*'s channel state; Stable when nothing is stored."""
    return load_channels(path).state(app_key)


def update_states(changes: dict[str, ChannelState], path: Path | None = None) -> ChannelsFile:
    """Write several apps' states in one read-modify-write; returns the result."""
    data = load_channels(path)
    for app_key, state in changes.items():
        data = data.with_state(app_key, state)
    save_channels(data, path)
    return data


# -- what the channel means for an update check ---------------------------------


def includes_prereleases(state: ChannelState) -> bool:
    """Whether an update check on *state* may offer a pre-release build.

    Stable never does. Beta and Dev do -- unless the person asked to come back
    to Stable and is waiting for it to catch up, when offers stop unless they
    ticked "keep getting Beta fixes while I wait".
    """
    if state.channel == STABLE:
        return False
    if state.pending_return:
        return state.keep_beta_while_waiting
    return True


def shown_channel(state: ChannelState) -> str:
    """The channel as the Release Channel dialog and Preferences say it."""
    if state.pending_return:
        return "Stable (waiting for it to catch up with your version)"
    return channel_label(state.channel)
