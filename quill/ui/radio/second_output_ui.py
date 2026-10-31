"""The second player: a background station or a mirror on another device.

Todo P3 "Radio extras" 3 and 4 (xradio2 4.6 and 4.7). What the second player
does when the main one changes is decided in
:mod:`quill.core.radio.second_output`; this module owns the second libmpv
instance, the two Audio-menu commands and the device question.

* **Background Station on Another Device...** (Alt+Shift+B) asks for a
  favourite, a device and a level, then plays it there underneath everything
  else. It pauses when the main player pauses and scales with the main volume;
  Stop and changing station on the main player leave it alone.
* **Mirror to Another Device...** (Alt+Shift+D) plays whatever the main player
  plays on a second device too, following it in everything.
* Choosing either again while it runs offers to turn it off, which is the one
  way it stops. Off by default; nothing is remembered across a restart, so a
  background station never starts by itself.

Needs the mpv engine (it is the one that can address a device); without it the
command says so and does nothing.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from quill.core.radio import second_output as rule
from quill.core.radio.models import is_retired_somafm_station

logger = logging.getLogger(__name__)

__all__ = [
    "BACKGROUND_COMMAND",
    "MIRROR_COMMAND",
    "SecondOutput",
    "append_menu_items",
    "follow",
    "register",
    "toggle_background",
    "toggle_mirror",
]

BACKGROUND_COMMAND = "radio.background_station"
MIRROR_COMMAND = "radio.mirror_output"

#: The levels offered for a background station, as a share of the main volume.
_LEVELS = (20, 30, 40, 50, 60, 80, 100)

EngineFactory = Callable[[Any, str], Any]


class SecondOutput:
    """One extra player on one extra device. Built when first used."""

    def __init__(self, parent: Any, *, engine_factory: EngineFactory | None = None) -> None:
        self._parent = parent
        self._factory = engine_factory or _mpv_engine
        self._engine: Any = None
        self.mode = rule.OFF
        self.device = ""
        self.device_label = ""
        self.station: Any = None
        self.own_volume = rule.DEFAULT_BACKGROUND_VOLUME
        self.playing_url = ""
        self.paused = False

    @property
    def active(self) -> bool:
        return self.mode != rule.OFF

    def _ensure_engine(self) -> Any:
        if self._engine is None:
            self._engine = self._factory(self._parent, self.device)
        return self._engine

    def start(
        self,
        mode: str,
        *,
        device: str,
        device_label: str,
        state: Any,
        station: Any = None,
        own_volume: int = rule.DEFAULT_BACKGROUND_VOLUME,
    ) -> None:
        self.stop()
        if mode == rule.BACKGROUND and station is not None and is_retired_somafm_station(
            stream_url=getattr(station, "stream_url", ""),
            homepage=getattr(station, "homepage", ""),
            source=getattr(station, "source", ""),
        ):
            return
        self.mode = mode
        self.device = device
        self.device_label = device_label
        self.station = station
        self.own_volume = own_volume
        engine = self._ensure_engine()
        engine.set_audio_device(device)
        if mode == rule.BACKGROUND and station is not None:
            engine.set_volume(
                rule.scaled_volume(own_volume, state.volume_percent, main_muted=state.muted)
            )
            if engine.load(station.stream_url):
                self.playing_url = station.stream_url
        self.follow(state)

    def follow(self, state: Any) -> None:
        """Apply what the main player just did."""
        if not self.active:
            return
        station = getattr(state, "station", None)
        step = rule.follow(
            self.mode,
            main_state=getattr(getattr(state, "state", None), "name", ""),
            main_url=str(getattr(station, "stream_url", "") or ""),
            main_volume=int(getattr(state, "volume_percent", 100)),
            main_muted=bool(getattr(state, "muted", False)),
            own_volume=self.own_volume,
            playing_url=self.playing_url,
            paused=self.paused,
        )
        self._apply(step)

    def _apply(self, step: rule.Step) -> None:
        engine = self._ensure_engine()
        if step.volume is not None:
            engine.set_volume(step.volume)
        if step.close:
            engine.close()
            self.playing_url = ""
            self.paused = False
            return
        if step.load:
            if engine.load(step.load):
                self.playing_url = step.load
                self.paused = False
            return
        if step.pause:
            engine.pause()
            self.paused = True
        elif step.resume:
            engine.play()
            self.paused = False

    def stop(self) -> None:
        """Turn the second player off."""
        if self._engine is not None:
            try:
                self._engine.close()
            except Exception:  # noqa: BLE001 - stopping must never fail loudly
                logger.debug("second output close failed", exc_info=True)
        self.mode = rule.OFF
        self.playing_url = ""
        self.paused = False
        self.station = None

    def shutdown(self) -> None:
        self.stop()
        if self._engine is not None and hasattr(self._engine, "terminate"):
            try:
                self._engine.terminate()
            except Exception:  # noqa: BLE001 - shutdown must never block
                pass
        self._engine = None


def _mpv_engine(parent: Any, device: str) -> Any:
    from quill.ui.radio.mpv_radio_engine import MpvRadioEngine

    return MpvRadioEngine(
        parent,
        on_loaded=lambda _ms: None,
        on_finished=lambda: None,
        on_error=lambda _message: None,
        audio_device=device,
    )


# -- the app side ----------------------------------------------------------------


def register(app: Any) -> None:
    app.commands.try_register(
        BACKGROUND_COMMAND,
        "Background Station on Another Device...",
        lambda: toggle_background(app),
        feature_id="core.radio",
    )
    app.commands.try_register(
        MIRROR_COMMAND,
        "Mirror to Another Device...",
        lambda: toggle_mirror(app),
        feature_id="core.radio",
    )


def append_menu_items(app: Any, menu: Any, wx: Any) -> None:
    """The two rows, on the Audio menu; ids pinned here."""
    ids = []
    for label, command, handler in (
        ("&Background Station on Another Device...", BACKGROUND_COMMAND, toggle_background),
        ("Mirror to Another &Device...", MIRROR_COMMAND, toggle_mirror),
    ):
        item_id = wx.NewIdRef()
        menu.Append(item_id, app._menu_label(label, command))
        app.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(app), id=item_id)
        ids.append(item_id)
    app._keep_menu_ids(*ids)


def follow(app: Any, state: Any) -> None:
    """The main player changed; the second one, if there is one, follows."""
    second = getattr(app, "_second_output", None)
    if second is None:
        return
    try:
        second.follow(state)
    except Exception:  # noqa: BLE001 - the main player must never pay for the second
        logger.debug("second output could not follow", exc_info=True)


def shutdown(app: Any) -> None:
    second = getattr(app, "_second_output", None)
    if second is not None:
        second.shutdown()


def _second(app: Any) -> SecondOutput:
    second = getattr(app, "_second_output", None)
    if second is None:
        second = SecondOutput(
            app.frame, engine_factory=getattr(app, "_second_engine_factory", None)
        )
        app._second_output = second
    return second


def _offer_off(app: Any, second: SecondOutput, ask_yes_no: Callable[[str], bool]) -> bool:
    """Something already runs: offer to turn it off. Returns True when handled."""
    if not second.active:
        return False
    what = (
        f"The background station {second.station.display_name if second.station else ''}"
        if second.mode == rule.BACKGROUND
        else "Mirroring"
    ).strip()
    if ask_yes_no(f"{what} is playing on {second.device_label}. Turn it off?"):
        second.stop()
        app._announce(f"{what} turned off.")
    return True


def _available(app: Any) -> bool:
    from quill.ui.radio.mpv_radio_engine import mpv_output_device_available

    if getattr(app, "_second_engine_factory", None) is not None or mpv_output_device_available():
        return True
    app._announce(
        "A second device needs the mpv playback engine, which is not available in this "
        "copy of Quill Radio."
    )
    return False


def _choose_device(app: Any, choose: Callable[[str, list[str]], int | None]) -> tuple[str, str]:
    """Ask which device; ``("", "")`` on Cancel. The main device is not offered."""
    from quill.ui.audio.output_routing import list_output_devices

    main = str(getattr(app._radio_history, "output_device", "") or "")
    devices = [(name, label) for name, label in list_output_devices() if name != main]
    if not devices:
        app._announce("There is no other output device to send it to.")
        return "", ""
    index = choose("Send it to which device?", [label for _name, label in devices])
    if index is None:
        return "", ""
    return devices[index]


def toggle_background(
    app: Any,
    *,
    choose: Callable[[str, list[str]], int | None] | None = None,
    ask_yes_no: Callable[[str], bool] | None = None,
) -> None:
    """Background Station on Another Device..., or turn the running one off."""
    choose = choose or _choose_with_dialog(app)
    ask_yes_no = ask_yes_no or _ask_with_dialog(app)
    second = _second(app)
    if _offer_off(app, second, ask_yes_no) or not _available(app):
        return
    favorites = list(app._radio_favorites.favorites)
    if not favorites:
        app._announce("Add a favorite first: the background station is one of your favorites.")
        return
    pick = choose("Play which favorite in the background?", [f.display_label for f in favorites])
    if pick is None:
        return
    device, device_label = _choose_device(app, choose)
    if not device:
        return
    levels = [f"{level} percent of the main volume" for level in _LEVELS]
    level = choose("How loud, compared with the main player?", levels)
    if level is None:
        return
    favorite = favorites[pick]
    if is_retired_somafm_station(
        stream_url=favorite.station.stream_url,
        homepage=favorite.station.homepage,
        source=favorite.station.source,
    ):
        app._announce(
            "SomaFM streams are not available in QUILL under SomaFM's current terms. "
            "Choose another favorite."
        )
        return
    second.start(
        rule.BACKGROUND,
        device=device,
        device_label=device_label,
        state=app._radio_controller.state,
        station=favorite.station,
        own_volume=_LEVELS[level],
    )
    app._announce(
        f"{favorite.display_label} is playing in the background on {device_label}. "
        "It pauses with the main player and keeps playing through Stop."
    )


def toggle_mirror(
    app: Any,
    *,
    choose: Callable[[str, list[str]], int | None] | None = None,
    ask_yes_no: Callable[[str], bool] | None = None,
) -> None:
    """Mirror to Another Device..., or turn mirroring off."""
    choose = choose or _choose_with_dialog(app)
    ask_yes_no = ask_yes_no or _ask_with_dialog(app)
    second = _second(app)
    if _offer_off(app, second, ask_yes_no) or not _available(app):
        return
    device, device_label = _choose_device(app, choose)
    if not device:
        return
    second.start(
        rule.MIRROR, device=device, device_label=device_label, state=app._radio_controller.state
    )
    app._announce(f"Mirroring to {device_label}. It follows the main player.")


def _choose_with_dialog(app: Any) -> Callable[[str, list[str]], int | None]:
    def choose(prompt: str, labels: list[str]) -> int | None:
        import wx

        from quill.ui import modal_stack

        with wx.SingleChoiceDialog(
            modal_stack.parent_window(app), prompt, "Another Device", labels
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return int(dialog.GetSelection())

    return choose


def _ask_with_dialog(app: Any) -> Callable[[str], bool]:
    def ask(question: str) -> bool:
        import wx

        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
            question, "Another Device", wx.ICON_QUESTION | wx.YES_NO, app.frame
        )
        return bool(answer == wx.YES)

    return ask
