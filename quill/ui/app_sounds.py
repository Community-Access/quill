"""Where this app's own sounds play, and the key that turns them off.

The family's one implementation of **App sounds play on** and **Alt+Shift+M**.
Every QUILL app calls these four functions and none has a copy of its own,
because a second copy is how two apps end up saying different things about the
same setting (CLAUDE.md, the QUILL Lite rule):

* :func:`apply` -- route this app's sounds to wherever its choice says, now.
  Called at launch and after anything that could change the answer.
* :func:`toggle` -- Alt+Shift+M: this app's sounds off, and back to where they
  were.
* :func:`choose` -- the chooser: Same as the app's audio (apps that have
  audio), System default, None (no sounds), or a sound card.
* :func:`own_device_changed` -- an app with audio of its own moved it; sounds
  that follow it move too.

A host says two things about itself: ``_app_sounds_id`` (its key in
``app_sounds.json``) and ``_app_sounds_name`` (what to call it out loud).
AppShellFrame sets both for every companion app; QUILL, QUILL Lite and Beacon
set them themselves. Whether the app has audio of its own, and where it plays,
is answered by app id in ``ui/media/output_device_apps.own_audio_device``.

The screen reader is never moved by any of this, and the family-wide sound
switch (Settings, Sound notifications) stays what it was: a silence for every
app at once, separate from each app's own choice.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "BUTTON_LABEL",
    "COMMAND_ID",
    "MENU_LABEL",
    "append_chooser_item",
    "append_menu_item",
    "apply",
    "choose",
    "current",
    "device_label",
    "own_device_changed",
    "preference_action",
    "sounds_on",
    "toggle",
]


#: The on/off key's command: the one QUILL has always had for its sound
#: switch, so a keymap that rebinds it rebinds it everywhere (family rule 2).
COMMAND_ID = "tools.sound_toggle"
#: The menu item, the same in every app: checked while this app's sounds are on.
MENU_LABEL = "App &Sounds"
_DEFAULT_KEY = "Alt+Shift+M"

#: The Preferences button, the same in every app. No access key: it joins
#: windows whose letters are spent, and a duplicate would advertise a key that
#: does not work (GATE-14). Tab reaches it, and Alt+Shift+M needs no window.
BUTTON_LABEL = "App Sounds Play On..."


def help_text(host: Any) -> str:
    """The button's F1 and screen-reader description, for this app."""
    from quill.core.app_sound_route import HELP_TAIL

    name = _name(host)
    if _own_device(host) is not None:
        lead = (
            f"Choose the sound card {name}'s own sounds play on. Same as its "
            "audio, where it starts, keeps them with whatever this app is "
            "playing, wherever you send it. "
        )
    else:
        lead = f"Choose the sound card {name}'s own sounds play on. "
    return lead + HELP_TAIL


#: Find a setting's key for the button, in the apps whose Preferences declare
#: their settings (core/app_settings_index).
SETTING_KEY = "app.sounds"


def preference_action(host: Any, *, key: str = "") -> Any:
    """The App Sounds Play On button for an app's Preferences window."""
    from quill.ui.app_preferences_dialog import PreferenceAction

    return PreferenceAction(BUTTON_LABEL, help_text(host), lambda: choose(host), key=key)


def _data_dir() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def _app_id(host: Any) -> str:
    return str(getattr(host, "_app_sounds_id", "") or "")


def _name(host: Any) -> str:
    return str(getattr(host, "_app_sounds_name", "") or "This app")


def _own_device(host: Any) -> str | None:
    """The host's own audio device, or None when it has no audio of its own."""
    from quill.ui.media.output_device_apps import own_audio_device

    try:
        return own_audio_device(host)
    except Exception:  # noqa: BLE001 - an engine still starting has no answer yet
        return ""


def current(host: Any) -> Any:
    """This app's saved :class:`~quill.core.app_sounds_store.AppSoundChoice`."""
    from quill.core import app_sounds_store

    return app_sounds_store.load(
        _data_dir(), _app_id(host), has_own_audio=_own_device(host) is not None
    )


def sounds_on(host: Any) -> bool:
    """Whether this app's own sounds are on (for a menu check mark)."""
    from quill.core.app_sound_route import NONE

    if not _app_id(host):
        return True
    return current(host).choice != NONE


def device_label(device: str) -> str:
    """What the listener calls *device*, without a slow enumeration."""
    if not device:
        return "the system default device"
    from quill.ui.audio.output_routing import cached_output_devices

    for name, description in cached_output_devices() or []:
        if name == device:
            return description or name
    try:
        from quill.platform.windows.wave_out import device_guid, list_devices

        guid = device_guid(device)
        for found in list_devices():
            if guid and found.guid == guid:
                return found.name
    except Exception:  # noqa: BLE001 - an id is still an answer
        pass
    return device


def apply(host: Any, *, preview: bool = False) -> None:
    """Route this app's sounds to wherever its choice says. Never raises.

    *preview* plays one sound on the result -- for a change the listener just
    made, never at launch.
    """
    if not _app_id(host):
        return
    from quill.core.app_sound_route import NONE, effective_device
    from quill.ui import sound_manager

    try:
        target = effective_device(current(host).choice, _own_device(host) or "")
    except Exception:  # noqa: BLE001 - an unreadable choice keeps the default
        return
    previous = getattr(host, "_app_sound_target", None)
    host._app_sound_target = target
    if previous != target:
        host._app_sounds_off_card = False

    def on_route(routed: bool) -> None:  # on whichever thread played the sound
        try:
            import wx

            wx.CallAfter(_route_changed, host, target, routed)
        except Exception:  # noqa: BLE001 - no wx is no announcement
            return

    watch = target and target != NONE
    try:
        sound_manager.set_output_device(target, on_route if watch else None)
    except Exception:  # noqa: BLE001 - routing must never cost the app its sounds
        return
    _sync_menu(host)
    if preview and target != NONE:
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.SOUND_ON)


def _save(host: Any, value: Any) -> None:
    from quill.core import app_sounds_store, family_preferences

    data_dir = _data_dir()
    app = _app_id(host)
    share_with: list[str] = []
    try:
        if family_preferences.is_sharing(data_dir, app):
            share_with = [
                other for other in family_preferences.sharing_apps(data_dir) if other != app
            ]
    except Exception:  # noqa: BLE001 - not sharing is the safe reading
        share_with = []
    app_sounds_store.save(data_dir, app, value, share_with=share_with)


def _where(host: Any, choice: str) -> str:
    from quill.core.app_sound_route import FOLLOW, effective_device

    own = _own_device(host) or ""
    where = device_label(effective_device(choice, own))
    return f"the same device as its audio, {where}" if choice == FOLLOW else where


def toggle(host: Any) -> None:
    """Alt+Shift+M: this app's sounds off, or back to where they were.

    Spoken, with QUILL's sound-off and sound-on cues on either side: the off
    cue plays where the sounds were, just before they stop, and the on cue
    plays where they now are -- so "where did they go?" is answered with "are
    they on?". Either cue can be switched off in Sound Scheme like any other.
    """
    if not _app_id(host):
        return
    from quill.core.app_sound_route import NONE, toggled
    from quill.core.app_sounds_store import AppSoundChoice

    saved = current(host)
    choice, remembered = toggled(
        saved.choice, saved.remembered, has_own_audio=_own_device(host) is not None
    )
    if choice == NONE:
        from quill.core.sound_events import SoundEvent
        from quill.ui.companion_cues import post_cue

        post_cue(SoundEvent.SOUND_OFF)  # the last sound, where they were playing
    _save(host, AppSoundChoice(choice, remembered))
    apply(host, preview=choice != NONE)
    announce = getattr(host, "_announce", None)
    if callable(announce):
        if choice == NONE:
            announce(f"{_name(host)}'s sounds off.")
        else:
            announce(f"{_name(host)}'s sounds on, playing on {_where(host, choice)}.")


def choose(host: Any) -> None:
    """Ask where this app's sounds should play, and move them there now."""
    if not _app_id(host):
        return
    import wx

    from quill.core import app_sound_route
    from quill.core.app_sounds_store import AppSoundChoice
    from quill.ui import modal_stack
    from quill.ui.audio.output_routing import list_output_devices

    saved = current(host)
    own = _own_device(host)
    labels, values, index = app_sound_route.choices(
        _devices(list_output_devices), saved.choice, own_device=own, own_audio_name="its audio"
    )
    parent = getattr(host, "frame", None) or host
    with wx.SingleChoiceDialog(
        modal_stack.parent_window(parent),
        f"Where should {_name(host)}'s own sounds play?",
        "App Sounds",
        labels,
    ) as dialog:
        dialog.SetSelection(index)
        if dialog.ShowModal() != wx.ID_OK:
            return
        chosen = values[dialog.GetSelection()]
    announce = getattr(host, "_announce", None) or (lambda _text: None)
    if chosen == saved.choice:
        announce("App sounds unchanged.")
        return
    remembered = saved.choice if chosen == app_sound_route.NONE else None
    _save(host, AppSoundChoice(chosen, remembered))
    apply(host, preview=True)
    if chosen == app_sound_route.NONE:
        announce(f"{_name(host)}'s sounds off. Alt+Shift+M turns them back on.")
    else:
        announce(f"{_name(host)}'s sounds play on {_where(host, chosen)}.")


def _devices(lister: Any) -> list[tuple[str, str]]:
    try:
        return list(lister())
    except Exception:  # noqa: BLE001 - no list is still a chooser
        return []


def own_device_changed(host: Any) -> bool:
    """The host's own audio moved. True when its sounds followed it.

    The caller can then say so in the sentence it was already going to speak,
    rather than this adding a second one.
    """
    from quill.core.app_sound_route import FOLLOW

    if not _app_id(host) or _own_device(host) is None:
        return False
    if current(host).choice != FOLLOW:
        return False
    apply(host, preview=True)
    return True


def append_menu_item(host: Any, menu: Any, *, label: str = MENU_LABEL) -> Any:
    """Add the App Sounds check item (Alt+Shift+M) to *menu*, wired and checked.

    *label* lets a menu whose S is taken pick another access letter. The key
    comes from the app's keymap when it binds the command, so a listener who
    rebinds it sees the new key here too.
    """
    import wx

    binder = getattr(host, "_menu_label", None)
    text = binder(label, COMMAND_ID) if callable(binder) else label
    if "\t" not in text:  # no key in this app's keymap: the family default
        text = f"{label}\t{_DEFAULT_KEY}"
    item_id = wx.NewIdRef()
    host._app_sounds_menu_id = item_id
    menu.AppendCheckItem(item_id, text)
    menu.Check(item_id, sounds_on(host))
    frame = getattr(host, "frame", None) or host
    frame.Bind(wx.EVT_MENU, lambda _event: toggle(host), id=item_id)
    return item_id


def append_chooser_item(host: Any, menu: Any, key: str) -> Any:
    """Add "App Sounds Play On..." to *menu*, for an app with no Preferences.

    Every other app has the chooser as a button in Preferences; Weather and
    Transcribe keep their settings in menus, so it goes there, with a key of
    its own because every menu item shows one (CLAUDE.md, menu accelerators).
    """
    import wx

    item_id = wx.NewIdRef()
    menu.Append(item_id, f"App Sounds Play &On...\t{key}")
    frame = getattr(host, "frame", None) or host
    frame.Bind(wx.EVT_MENU, lambda _event: choose(host), id=item_id)
    return item_id


def _sync_menu(host: Any) -> None:
    """Keep the App Sounds check mark in step, wherever the change came from."""
    item_id = getattr(host, "_app_sounds_menu_id", None)
    if item_id is None:
        return
    try:
        frame = getattr(host, "frame", None) or host
        menu_bar = frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(item_id), sounds_on(host))
    except Exception:  # noqa: BLE001 - a menu mid-rebuild is not an error
        return


def _route_changed(host: Any, target: str, routed: bool) -> None:
    """One sentence when sounds leave their card, one when they return."""
    if getattr(host, "_app_sound_target", None) != target:
        return  # an answer about a card the setting has since moved away from
    announce = getattr(host, "_announce", None)
    if not callable(announce):
        return
    if not routed:
        if getattr(host, "_app_sounds_off_card", False):
            return
        host._app_sounds_off_card = True
        announce(
            f"{_name(host)}'s sounds cannot reach {device_label(target)}, so they "
            "are playing on the system default device until it is back."
        )
    elif getattr(host, "_app_sounds_off_card", False):
        host._app_sounds_off_card = False
        announce(f"{_name(host)}'s sounds are back on {device_label(target)}.")
