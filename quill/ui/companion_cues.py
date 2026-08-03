"""Post a companion-app earcon on a real state change (#1302).

Most of the fourteen companion-app cues ride along on an announcement the app
already makes -- ``_announce(message, sound=SoundEvent.X)`` -- because the cue
belongs to the same moment as the words.

A handful do not. A stream actually reaching PLAYING, an episode download
finishing, an episode ending: these are states the apps change through
*silently* (the status bar updates, nothing is spoken), so there is no
announcement to attach to, and inventing one would put speech where the design
deliberately had none. ``post_cue`` posts just the earcon for those, through
the same player -- and therefore the same per-event disable list in
``settings.sound_events_disabled`` -- the announcement service's ``SoundSink``
uses.

Callers are responsible for firing only on a genuine transition: this module
deliberately keeps no state, so a poll loop that calls it every tick would be
a bug at the call site, not something to paper over here.
"""

from __future__ import annotations


def init_app_sound(settings: object | None = None) -> None:
    """Load the sound pack so this app's earcons have a player to reach.

    Only ``MainFrame`` ever started the sound manager, so every companion app
    installed a ``SoundSink`` that played into an uninitialised manager: the
    whole cue catalogue was inert outside QUILL itself. Never fatal -- an app
    with no sound stack simply stays quiet, exactly as it did before.
    """
    try:
        from quill.core.settings import load_settings
        from quill.ui import sound_manager

        sound_manager.init(settings if settings is not None else load_settings())
    except Exception:  # noqa: BLE001 - no sound is never a startup failure
        return


def post_cue(event: str) -> None:
    """Play the earcon for *event*; silent when this app has no sound stack.

    Never raises and never blocks: an earcon that cannot play must not take
    down the action the user just performed.
    """
    if not event:
        return
    try:
        from quill.ui.sound_manager import post_sound

        post_sound(str(event))
    except Exception:  # noqa: BLE001 - a missing sound stack is not an error
        return
