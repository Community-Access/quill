"""What this machine remembers about syncing: a folder, a name, and a switch.

Three fields, kept out of the main settings file on purpose. Sync is opt-in, off
for everybody who never asks for it, and the settings schema should not carry
three fields most installs will never set. It is also the file somebody is most
likely to want to delete outright to start again, and a file of its own makes
that a thing they can do.

**The recovery phrase is not here, and never will be.** It is the key. It lives
in the platform credential store (Windows Credential Manager via
``platform/windows/credential_manager.py``) exactly as every other secret in
QUILL does, and this file holds only the fact that one was saved -- so the app
can tell "not set up" apart from "set up, and the key is where keys go".

**The device name is a label, not an identity.** It appears in the commit log so
somebody reading it can tell which machine wrote what. It defaults to the
computer's own name because that is the answer people would give.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILENAME = "sync_places.json"


def default_device_name() -> str:
    """This machine, as a person would name it."""
    try:
        name = socket.gethostname().strip()
    except OSError:
        name = ""
    return name or "This computer"


@dataclass(slots=True)
class PlacesConfig:
    """Where your place goes, and whether it goes anywhere at all."""

    enabled: bool = False
    #: The folder shared between machines -- inside OneDrive, Dropbox, iCloud
    #: Drive, a network share, a stick. "" until one is chosen.
    remote_dir: str = ""
    device: str = ""
    #: Whether a recovery phrase has been stored for this machine. The phrase
    #: itself is in the credential store; this is only the fact of it, so the
    #: app can say "enter your recovery phrase" rather than failing at sync.
    has_phrase: bool = False
    #: Sync after playback stops, as well as on request. Off by default: a
    #: write to somebody's cloud folder is a real cost and should be asked for.
    sync_on_stop: bool = False

    @property
    def is_ready(self) -> bool:
        """Whether a sync could actually run right now."""
        return bool(self.enabled and self.remote_dir and self.has_phrase)

    def describe(self) -> str:
        """The settings line: where this machine stands, in one sentence."""
        if not self.enabled:
            return "Your place is not being carried between machines."
        if not self.remote_dir:
            return "Choose a folder both machines can see."
        if not self.has_phrase:
            return "Enter or make a recovery phrase for that folder."
        return f"Your place is carried through {self.remote_dir}, as {self.device}."

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "remote_dir": self.remote_dir,
            "device": self.device,
            "has_phrase": self.has_phrase,
            "sync_on_stop": self.sync_on_stop,
        }

    @classmethod
    def from_dict(cls, data: object) -> PlacesConfig:
        if not isinstance(data, dict):
            return cls(device=default_device_name())
        return cls(
            enabled=bool(data.get("enabled", False)),
            remote_dir=str(data.get("remote_dir", "")),
            device=str(data.get("device", "")) or default_device_name(),
            has_phrase=bool(data.get("has_phrase", False)),
            sync_on_stop=bool(data.get("sync_on_stop", False)),
        )


def config_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / _FILENAME


def load(data_dir: Path | str) -> PlacesConfig:
    """This machine's sync settings. A damaged file reads as "not set up"."""
    path = config_path(data_dir)
    try:
        return PlacesConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return PlacesConfig(device=default_device_name())


def save(data_dir: Path | str, config: PlacesConfig) -> None:
    """Persist, atomically, like every other list QUILL owns."""
    write_json_atomic(config_path(data_dir), config.to_dict())


#: The credential-store key the recovery phrase is filed under. One constant so
#: the writer and the reader can never drift apart.
PHRASE_CREDENTIAL = "quill:sync:places:phrase"
