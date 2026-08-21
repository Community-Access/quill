"""Opening the sync window, storing the phrase, and running a sync off the UI thread.

Plain functions taking the host frame, so QUILL, Quill Cast and Quill Radio each
reach the same window and the same code path.

Two things live here rather than in the dialog:

* **The recovery phrase goes to the platform credential store**, exactly like
  every other secret QUILL holds. The settings file records only that one was
  saved, so the app can tell "not set up" from "set up, and the key is where
  keys go". On a platform with no credential store, the phrase is not written
  anywhere and the window says so -- an unencrypted key on disk would be worse
  than asking somebody to type eight words.
* **Sync runs on the task manager.** It reads a folder that may be a network
  share or a cloud folder that has gone to sleep, and doing that on the UI
  thread is how an app stops responding while somebody is listening to it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.sync import places, places_config

_LOG = logging.getLogger(__name__)


def _data_dir(host: Any) -> Path:
    return app_data_dir()


def load_config(host: Any) -> places_config.PlacesConfig:
    return places_config.load(_data_dir(host))


def save_phrase(phrase: str) -> bool:
    """Store the recovery phrase where secrets go. False when it could not be."""
    try:
        from quill.platform.windows.credential_manager import (
            credential_manager_available,
            save_generic_credential,
        )
    except ImportError:
        return False
    if not credential_manager_available():
        return False
    try:
        save_generic_credential(places_config.PHRASE_CREDENTIAL, phrase)
    except OSError as error:  # pragma: no cover - platform dependent
        _LOG.debug("could not store the sync recovery phrase: %s", error)
        return False
    return True


def load_phrase() -> str:
    """The stored recovery phrase, or "" when there is none."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential
    except ImportError:
        return ""
    try:
        stored = load_generic_credential(places_config.PHRASE_CREDENTIAL)
    except OSError:  # pragma: no cover - platform dependent
        return ""
    return str(getattr(stored, "secret", "") or "") if stored is not None else ""


def sync_once(config: places_config.PlacesConfig, phrase: str) -> str:
    """One sync, start to finish, as a sentence. Never raises.

    The vault is opened (or created) first, so a mistyped phrase is caught
    before anything is read or written and the answer is "that phrase does not
    match this folder" rather than a decryption failure part-way through.
    """
    from quill.core.sync import vault_file

    if not config.remote_dir:
        return "Choose a folder both machines can see first."

    said: list[str] = []
    if config.encrypted:
        try:
            vault = vault_file.load_or_create(config.remote_dir, phrase).key
        except vault_file.VaultError as error:
            return str(error)
        except OSError as error:
            return f"That folder could not be used: {error}"
        said.append(
            places.sync_places(
                data_dir=app_data_dir(),
                remote_dir=config.remote_dir,
                vault=vault,
                device=config.device or places_config.default_device_name(),
            ).summary()
        )
    if config.interchange and config.device_id:
        # The plain half runs after the encrypted one, over the same folder in
        # its own subfolder, so a machine with both on writes what it knows
        # once the other QUILL machines have already been merged in.
        from quill.core.sync.places_interchange import sync_interchange

        said.append(
            sync_interchange(
                data_dir=app_data_dir(),
                remote_dir=config.remote_dir,
                device_id=config.device_id,
                device_label=config.device or places_config.default_device_name(),
                include_labels=config.include_labels,
            ).summary()
        )
    if not said:
        return "Nothing is switched on to sync."
    return " ".join(said)


def open_sync_places(host: Any) -> None:
    """The command: open the setup window, wired to this host."""
    from quill.ui.sync_places_dialog import SyncPlacesDialog

    config = load_config(host)

    def _save(new_config: places_config.PlacesConfig, phrase: str) -> None:
        stored = save_phrase(phrase) if phrase else False
        new_config.has_phrase = stored
        places_config.save(_data_dir(host), new_config)
        announce = getattr(host, "_announce", None)
        if callable(announce):
            if phrase and not stored:
                announce(
                    "Your settings were saved, but this computer has no secure "
                    "place to keep the recovery phrase, so you will be asked for "
                    "it each time."
                )
            else:
                announce(new_config.describe())

    SyncPlacesDialog(
        getattr(host, "frame", None) or getattr(host, "dialog", None) or host,
        config=config,
        phrase=load_phrase(),
        on_save=_save,
        sync_now=lambda cfg, phrase: sync_once(cfg, phrase),
        announce=getattr(host, "_announce", None),
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
    ).show()


def sync_in_background(host: Any) -> bool:
    """Run a sync without a window -- the "when playback stops" path.

    Silent unless something is worth saying: a sync that moved nothing must not
    announce itself, because this fires every time playback stops and a message
    every time is a message nobody hears.
    """
    config = load_config(host)
    if not config.sync_on_stop:
        return False
    if not config.is_ready and not config.interchange_ready:
        return False
    phrase = load_phrase()
    if config.encrypted and not phrase:
        return False
    task_manager = getattr(host, "_task_manager", None)
    announce = getattr(host, "_announce", None)

    def _work(**_kwargs: object) -> str:
        return sync_once(config, phrase)

    def _done(_op: str, said: str) -> None:
        if callable(announce) and said and "already up to date" not in said:
            announce(said)

    if task_manager is None:
        return False
    task_manager.submit("sync-places", _work, on_success=_done, on_failure=lambda _op, _e: None)
    return True


def sync_at_launch(host: Any) -> bool:
    """Read the shared folder once, at launch, off the UI thread.

    **Launch and an explicit Sync Now are the only two moments a read happens.**
    Not on a timer, not on a window gaining focus, not on a file-change
    notification. The reason is what a pulled position does: if a read lands
    mid-session and finds that another device moved you to 52 minutes in the
    episode you are listening to at 40, every available behaviour is bad.
    Moving the playhead under somebody is unacceptable, and it is worse for a
    screen reader user, who gets no visual cue that anything happened; queuing
    it silently is confusing; asking mid-episode is an interruption nobody
    wants. At launch nothing is playing, so there is nothing to disturb, and
    the whole problem goes away rather than being managed.

    The practical cost is that a change made elsewhere while Cast is already
    open does not appear until the next launch or the next Sync Now. That is
    the right trade: "your place is right when you sit down" is the promise,
    and it is kept.

    Silent unless something actually came back.
    """
    config = load_config(host)
    if not config.enabled:
        return False
    if not config.is_ready and not config.interchange_ready:
        return False
    phrase = load_phrase()
    if config.encrypted and not phrase:
        return False
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        return False
    announce = getattr(host, "_announce", None)

    def _work(**_kwargs: object) -> str:
        return sync_once(config, phrase)

    def _done(_op: str, said: str) -> None:
        # A launch that found nothing says nothing: an announcement every time
        # the app opens is the one that teaches people to ignore it, and it
        # would land on top of the screen reader reading the new window.
        if callable(announce) and said and "already up to date" not in said:
            announce(said)

    task_manager.submit(
        "sync-places-launch", _work, on_success=_done, on_failure=lambda _op, _e: None
    )
    return True
