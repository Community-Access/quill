"""Community > Ask QUILL Radio... and Use My ChatGPT Subscription...

The wiring for Quill Radio's assistant, in the house shape: two commands, two
menu rows, and an opener per window that raises the one already open rather
than building a second. The windows themselves are
:mod:`quill.ui.radio.ask_radio_window` (the conversation) and the family's
shared :mod:`quill.ui.hosted_ai_chatgpt` (the account: sign in, model, web
search, sign out), built here on a
:class:`~quill.core.ai.chatgpt_account.ChatGptAccount` that signs in as
"QUILL Radio" and is kept, with its own refresh token, apart from the editors'.

Deliberately absent: QUILL's free AI service and Use My Own OpenAI Key. Quill
Radio's assistant works one way, on the plan the listener already pays for, and
the account window says so. Safe Mode refuses both commands, as it does every
AI command in the family.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.radio.ask_radio_window import AGENT_NAME, TITLE, AskRadioFrame

__all__ = [
    "ACCOUNT_TITLE",
    "account_for",
    "append_menu_items",
    "extra_for",
    "open_account",
    "open_ask",
    "register",
    "what_is_on",
]

ACCOUNT_TITLE = "Use My ChatGPT Subscription"
_SAFE_MODE = "Ask QUILL Radio is disabled in Safe Mode."


def register(app: Any) -> None:
    commands: Any = app.commands
    commands.try_register(
        "radio.ask_quill_radio",
        "Ask QUILL Radio...",
        lambda: open_ask(app),
        app._binding_for("radio.ask_quill_radio"),
        feature_id="core.radio",
    )
    commands.try_register(
        "radio.chatgpt_account",
        "Use My ChatGPT Subscription...",
        lambda: open_account(app),
        app._binding_for("radio.chatgpt_account"),
        feature_id="core.radio",
    )


def append_menu_items(host: Any, menu: Any, wx: Any) -> tuple[Any, ...]:
    """Two rows at the top of the Community menu. The caller pins the ids."""
    ids = []
    for label, command, handler in (
        ("Ask QUILL &Radio...", "radio.ask_quill_radio", lambda: open_ask(host)),
        (
            "Use My Chat&GPT Subscription...",
            "radio.chatgpt_account",
            lambda: open_account(host),
        ),
    ):
        item_id = wx.NewIdRef()
        menu.Append(item_id, host._menu_label(label, command))
        host.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        ids.append(item_id)
    host._keep_menu_ids(*ids)
    return tuple(ids)


# --------------------------------------------------------------------------- #
# The account, and what is on
# --------------------------------------------------------------------------- #


def account_for(host: Any) -> Any:
    """Quill Radio's ChatGPT sign-in, made once per app and kept on the host."""
    account = getattr(host, "_chatgpt_account", None)
    if account is None:
        from quill.core.ai.chatgpt_account import ChatGptAccount
        from quill.core.paths import app_data_dir

        account = ChatGptAccount(app_data_dir(), agent_name=AGENT_NAME)
        host._chatgpt_account = account
    return account


def what_is_on(host: Any) -> tuple[str, str]:
    """``(station name, now-playing text)``, each "" when unknown. Never raises."""
    station = ""
    playing = ""
    try:
        controller = getattr(host, "_radio_controller", None)
        current = controller.state.station if controller is not None else None
        station = str(getattr(current, "name", "") or "") if current is not None else ""
    except Exception:  # noqa: BLE001 - a host without a player has no station
        station = ""
    try:
        text = getattr(host, "_radio_now_playing_text", None)
        playing = str(text() or "") if callable(text) else ""
    except Exception:  # noqa: BLE001 - an unread title is not an error here
        playing = ""
    return station, playing


def _station_key(host: Any) -> str:
    try:
        controller = getattr(host, "_radio_controller", None)
        current = controller.state.station if controller is not None else None
        if current is None:
            return ""
        return str(getattr(current, "station_uuid", "") or getattr(current, "stream_url", "") or "")
    except Exception:  # noqa: BLE001 - no station, no key
        return ""


def extra_for(host: Any, needs: str) -> tuple[str, int]:
    """``(context text, how many things it names)`` for a quick question.

    Read only when a question that needs it is chosen, from what the app
    already holds -- the favorites list and the song log -- and never raises:
    a host without either answers with nothing, and the window says so.
    """
    from quill.core.radio.assistant_prompt import (
        NEEDS_FAVORITES,
        NEEDS_LISTENING,
        NEEDS_RECENT_SONGS,
        extra_context,
    )

    try:
        if needs == NEEDS_FAVORITES:
            store = getattr(host, "_radio_favorites", None)
            pairs = [
                (str(getattr(fav.station, "name", "") or ""), str(getattr(fav, "folder", "") or ""))
                for fav in (getattr(store, "favorites", []) or [])
            ]
            pairs = [(name, folder) for name, folder in pairs if name]
            return extra_context(needs, favorites=pairs), len(pairs)
        if needs in (NEEDS_RECENT_SONGS, NEEDS_LISTENING):
            from quill.ui.radio.song_history_commands import song_history

            log = song_history(host)
            if needs == NEEDS_RECENT_SONGS:
                songs = [song.display() for song in log.songs_for(_station_key(host))]
                return extra_context(needs, recent_songs=songs), len(songs)
            stations = [
                (station.station_name or station.station_key, [s.display() for s in station.songs])
                for station in log.known_stations()
            ]
            return extra_context(needs, listening=stations), len(stations)
    except Exception:  # noqa: BLE001 - nothing to attach is an answer, not a crash
        pass
    return "", 0


def _submit_for(host: Any) -> Callable[..., None]:
    """A ``submit(name, work, on_done, on_error)`` on the host's task manager.

    Callbacks land on the UI thread. Without a task manager (a test host), the
    family's plain thread helper does the same job.
    """

    def submit(name: str, work: Callable[..., Any], *, on_done: Any, on_error: Any) -> None:
        wx = host._wx

        def done(_op: str, result: Any) -> None:
            wx.CallAfter(on_done, result)

        def failed(_op: str, error: BaseException) -> None:
            from quill.ui.hosted_ai_service import _sentence

            wx.CallAfter(on_error, _sentence(error))

        tasks = getattr(host, "_task_manager", None)
        if tasks is not None:
            tasks.submit(name, work, on_success=done, on_failure=failed)
            return
        from quill.ui.update_download import thread_submit

        thread_submit(name, work, on_success=done, on_failure=failed)

    return submit


# --------------------------------------------------------------------------- #
# The two windows
# --------------------------------------------------------------------------- #


def _refuse_in_safe_mode(host: Any) -> bool:
    if not getattr(host, "_safe_mode", False):
        return False
    host._announce(_SAFE_MODE)
    return True


def open_ask(host: Any) -> Any:
    """Open the conversation, or raise it; with no sign-in, open the account window."""
    if _refuse_in_safe_mode(host):
        return None
    windows = getattr(host, "_windows", None)
    if windows is not None:
        already = windows.activate_title(TITLE)
        if already is not None:
            return already
    account = account_for(host)
    if not account.signed_in:
        host._announce(
            "Ask QUILL Radio uses your ChatGPT subscription. Choose Continue with "
            "ChatGPT to sign QUILL Radio in first."
        )
        return open_account(host)
    frame = AskRadioFrame(
        host.frame,
        account=account,
        announce=host._announce,
        what_is_on=lambda: what_is_on(host),
        submit=_submit_for(host),
        open_account=lambda: open_account(host),
        extra_for=lambda needs: extra_for(host, needs),
    )
    host._ask_radio_frame = frame

    def forget(event: Any) -> None:
        host._ask_radio_frame = None
        event.Skip()

    frame.Bind(host._wx.EVT_CLOSE, forget)
    _show(host, frame, TITLE, "&Ask")
    return frame


def open_account(host: Any) -> Any:
    """Open the shared ChatGPT account window as QUILL Radio, or raise it."""
    if _refuse_in_safe_mode(host):
        return None
    windows = getattr(host, "_windows", None)
    if windows is not None:
        already = windows.activate_title(ACCOUNT_TITLE)
        if already is not None:
            return already
    from quill.ui.hosted_ai_chatgpt import ChatGptFrame

    account = account_for(host)

    def changed() -> None:
        # A conversation window left open reads the account live on each send;
        # only its What-it-knows line needs to hear about a new model or the
        # web-search switch, and it must not be raised to be told.
        open_ask_window = getattr(host, "_ask_radio_frame", None)
        if open_ask_window:
            open_ask_window.refresh_context()

    frame = ChatGptFrame(host.frame, account, host._announce, on_change=changed)
    _show(host, frame, ACCOUNT_TITLE, "&Account")
    return frame


def _show(host: Any, frame: Any, title: str, menu_title: str) -> None:
    """Make *frame* a peer window: menu bar, Window menu, transport keys, exit cue."""
    wx = host._wx
    windows = getattr(host, "_windows", None)
    if windows is not None:
        menu_bar = wx.MenuBar()
        own = wx.Menu()
        close_id = wx.NewIdRef()
        own.Append(close_id, "&Close\tCtrl+W")
        frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
        menu_bar.Append(own, menu_title)
        windows.install(frame, menu_bar)
        frame.SetMenuBar(menu_bar)
        host._keep_menu_ids(close_id)
        try:
            from quill.ui.radio import transport_keys

            transport_keys.install(frame, host, wx=wx, extra_entries=windows.accelerator_entries())
        except Exception:  # noqa: BLE001 - the transport is a convenience here
            pass
        windows.register(frame, title)

        def on_close(event: Any) -> None:
            from quill.ui.dialog_contract import announce_surface_exit

            previous = windows.previous_key(frame)
            windows.unregister(frame)
            announce_surface_exit(title, host._announce)
            event.Skip()
            if previous:
                wx.CallAfter(windows.activate, previous)

        frame.Bind(wx.EVT_CLOSE, on_close)
    from quill.ui.dialog_contract import show_modeless_surface

    show_modeless_surface(frame, title, announce=host._announce)
