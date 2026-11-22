"""Scribe for Documents in the family's other apps (PRD 8.3 to 8.8).

QUILL and QUILL Lite are editors, with :mod:`quill.ui.main_frame_scribe` and
:mod:`quill.apps.lite_window_scribe`. Quill Media Player, Quill Converter,
QUILL Studio, QUILL Cast, Quill Beacon and QUILL Social are not, and every
one of them needs the same few things, written here once:

* :class:`AppScribeHost` -- an app's side of
  :class:`quill.ui.scribe_controller.ScribeHost`: its name, the window a
  dialog belongs to, its own announcement service, and where a result opens.
  **A result that opens in another app never opens by itself**
  (``scribe_opens_on_its_own = False``): the other app coming to the front
  would cut the one result sentence off, so the sentence ends "Open it from
  Scribe Conversions." and Open Result and Next Steps open it on the person's
  command (accessibility review, 2026-11-21). The Media Player, whose results
  open in itself, says otherwise.
* :class:`AppScribeMixin` -- the shared commands on an
  :class:`~quill.ui.app_shell.AppShellFrame` app, through
  :class:`~quill.ui.scribe_entry.ScribeEntryPoints` (there is no document in
  front, so Convert This Document is not offered).
* :data:`COMMON_ROWS` and :func:`append_scribe_submenu` -- the Scribe for
  Documents submenu every app has: Scribe Conversions, My Scribe Documents,
  Scribe Status, Repeat Last Scribe Message and Options (which holds Sign In,
  Sign Out and the account). **The same keys in every app**, so a person who
  knows one knows them all: these apps show a key on every menu row, and a
  once-in-a-while command gets a key, not a short one (rule 9) -- Alt+Shift
  with F6 to F11, free in every one of these six apps, and never
  Ctrl+Alt+Shift with a letter, which AltGr+Shift would type on many keyboards
  in a text field (the Ctrl+Alt+Shift F-row is spoken for: ``app_keymaps``).
  **Not the editors' keys:** in QUILL and QUILL Lite, Alt+Shift+F6 to F11 are
  editor commands (Dictation Settings, Spelling for This Word, Extend
  Selection...), and their Scribe rows have no default key; the guides say so.
  The app's own entry point is on :data:`ENTRY_KEY` wherever it sits.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.ui.scribe_entry import ScribeEntryPoints, send_to_player

#: The app's own Scribe command (Listen, Convert Documents, Narration, Convert
#: Linked Document, Add My Scribe Documents as Places).
ENTRY_KEY = "Alt+Shift+F6"

#: (command id, label, handler on the app, key): the submenu, in order.
COMMON_ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("scribe.conversions", "Scribe &Conversions", "scribe_conversions", "Alt+Shift+F7"),
    ("scribe.my_documents", "&My Scribe Documents", "scribe_my_documents", "Alt+Shift+F8"),
    ("scribe.status", "Scribe &Status", "scribe_status", "Alt+Shift+F9"),
    ("scribe.repeat", "&Repeat Last Scribe Message", "scribe_repeat", "Alt+Shift+F10"),
    ("scribe.options", "Scribe for Documents &Options...", "scribe_options", "Alt+Shift+F11"),
)

#: What an editor opens, of Scribe's formats.
_EDITOR_FORMATS = ("docx", "html", "epub", "brf")


# -- opening a result in another app ----------------------------------------


def _lite_launcher() -> list[str] | None:
    """How to start QUILL Lite: its installed launcher, or the module from source."""
    from quill.core.runtime_apps import RUNTIME_APPS, installed_launcher

    lite = next((app for app in RUNTIME_APPS if app.ref_id == "quilllite"), None)
    if lite is None:
        return None
    found = installed_launcher(lite)
    if found is not None:
        return [str(found)]
    if not getattr(sys, "frozen", False):
        return [sys.executable, "-m", "quill.apps.lite"]
    return None


def editor_name() -> str:
    """The editor a document opens in: QUILL, else QUILL Lite, else ``""`` (8.6)."""
    from quill.core.app_launcher import build_launch_argv

    if build_launch_argv("quill") is not None:
        return "QUILL"
    return "QUILL Lite" if _lite_launcher() is not None else ""


def open_in_editor(path: Path) -> str:
    """Open *path* in QUILL, or in QUILL Lite when QUILL is not installed.
    Returns the editor's name, or ``""`` when neither could be started."""
    from quill.core.app_launcher import launch_app

    if launch_app("quill", extra_args=(str(path),)):
        return "QUILL"
    argv = _lite_launcher()
    if argv is None:
        return ""
    try:
        subprocess.Popen([*argv, str(path)], close_fds=True)  # noqa: S603 - our own launcher
    except OSError:
        return ""
    return "QUILL Lite"


def open_elsewhere(format_id: str, path: Path) -> str:
    """Section 9, from an app that is not an editor: Word, HTML, EPUB and BRF in
    the editor, MP3 and DAISY in Media Player. Returns what to say, or ``""``."""
    from quill.core.scribe.results import default_action, opened_phrase

    action = default_action(format_id)
    if action in ("editor", "braille"):
        where = open_in_editor(path)
        return opened_phrase(format_id, where) if where else ""
    if action == "player" and send_to_player(format_id, path):
        return opened_phrase(format_id, "Media Player")
    return ""


def elsewhere_steps(
    job: Any,
    ready: dict[str, Path],
    announce: Callable[[str], None],
    *,
    editor: bool = True,
    player: bool = True,
) -> list[tuple[str, Callable[[], None]]]:
    """Next Steps that open a result in another app: Open in QUILL (Word),
    Send to Media Player (MP3 audio). Each says so when it could not."""
    from quill.core.scribe.model import format_label

    steps: list[tuple[str, Callable[[], None]]] = []
    name = editor_name() if editor else ""
    if name:
        for format_id in _EDITOR_FORMATS:
            if format_id in ready:

                def to_editor(path: Path = ready[format_id]) -> None:
                    if not open_in_editor(path):
                        announce(f"QUILL could not be opened. {path.name} is saved in its folder.")

                steps.append((f"Open in {name} ({format_label(format_id)})", to_editor))
    if player:
        for format_id in ("mp3", "daisy"):
            if format_id in ready:

                def to_player(f: str = format_id, path: Path = ready[format_id]) -> None:
                    if not send_to_player(f, path):
                        announce(
                            f"Media Player could not be opened. {job.display_name} is "
                            "saved in its folder."
                        )

                steps.append((f"Send to Media Player ({format_label(format_id)})", to_player))
    return steps


# -- the host ------------------------------------------------------------------


class AppScribeHost:
    """One app's side of :class:`quill.ui.scribe_controller.ScribeHost`."""

    #: Results open in other apps: never by themselves (see the module notes).
    scribe_opens_on_its_own = False

    def __init__(self, owner: Any, app_name: str) -> None:
        self._owner = owner
        self.app_name = app_name

    def scribe_parent(self) -> Any:
        import wx

        return wx.GetActiveWindow() or getattr(self._owner, "frame", None) or self._owner

    def scribe_announce(self, text: str) -> None:
        self._owner._announce(text)

    def scribe_in_front(self) -> bool:
        import wx

        return wx.GetActiveWindow() is not None

    def scribe_ai_off(self) -> bool:
        return False

    def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
        return open_elsewhere(format_id, path)

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        return elsewhere_steps(job, ready, self.scribe_announce)


# -- the menu ------------------------------------------------------------------


def append_scribe_submenu(
    owner: Any,
    menu: Any,
    wx: Any,
    *,
    title: str = "Scribe for &Documents",
    first: tuple[str, Callable[[], None]] | None = None,
    position: int | None = None,
) -> list[Any]:
    """Append the Scribe for Documents submenu to *menu*; return its ids.

    *first* is an app row that belongs in the submenu itself (Beacon's Add My
    Scribe Documents as Places), on :data:`ENTRY_KEY`. Each row runs the
    owner's ``scribe_*`` command of the same name. *position* inserts the
    submenu there instead of at the end.
    """
    submenu = wx.Menu()
    ids: list[Any] = []

    frame = getattr(owner, "frame", None) or owner  # Beacon and Social are the frame

    def add(label: str, handler: Callable[[], None]) -> None:
        item_id = wx.NewIdRef()
        submenu.Append(item_id, label)
        frame.Bind(wx.EVT_MENU, lambda _e: handler(), id=item_id)
        ids.append(item_id)

    if first is not None:
        add(f"{first[0]}\t{ENTRY_KEY}", first[1])
        submenu.AppendSeparator()
    for _command_id, label, handler, key in COMMON_ROWS:
        add(f"{label}\t{key}", lambda h=handler: getattr(owner, h)())
    if position is None:
        menu.AppendSubMenu(submenu, title)
    else:
        menu.Insert(position, wx.ID_ANY, title, submenu)
    owner._scribe_menu_ready()
    return ids


class AppScribeMixin(ScribeEntryPoints):
    """The shared Scribe commands on an app window (an ``AppShellFrame``)."""

    #: The app's name in every sentence ("Quill Media Player").
    scribe_app_name = "QUILL"

    def _scribe_make_host(self) -> Any:
        return AppScribeHost(self, self.scribe_app_name)

    def _scribe(self) -> Any:
        from quill.ui.scribe_controller import controller_for

        host = self.__dict__.get("_scribe_host")
        if host is None:
            host = self._scribe_make_host()
            self.__dict__["_scribe_host"] = host
        return controller_for(host)

    def _scribe_frame(self) -> Any:
        return self.frame  # type: ignore[attr-defined]

    def _scribe_modal(self, dialog: Any, title: str) -> int:
        return int(self._show_modal_dialog(dialog, title))  # type: ignore[attr-defined]

    def _scribe_say(self, text: str) -> None:
        self._announce(text)  # type: ignore[attr-defined]

    def _scribe_document(self) -> tuple[Path | None, bool, str] | None:
        return None  # no document in front: these apps have none

    def _scribe_save_document(self) -> None:
        return None

    def _scribe_menu_ready(self) -> None:
        """Once, after startup's own messages: pick up jobs left running (7.4)."""
        if self.__dict__.get("_scribe_started"):
            return
        self.__dict__["_scribe_started"] = True
        import wx

        wx.CallLater(5000, self._scribe_start)

    def _scribe_start(self) -> None:
        try:
            self._scribe().start_if_jobs_waiting()
        except RuntimeError:  # the window closed before the five seconds were up
            pass

    def _scribe_pick(self, *, multiple: bool) -> list[Path]:
        """The family's picker: only the 23 types Scribe takes (3.1)."""
        import wx

        from quill.core.scribe.inputs import input_wildcard

        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | (wx.FD_MULTIPLE if multiple else 0)
        title = f"Choose a Document for {PRODUCT_NAME}"
        dialog = wx.FileDialog(self._scribe_frame(), title, wildcard=input_wildcard(), style=style)
        try:
            if self._scribe_modal(dialog, title) != wx.ID_OK:
                return []
            return [Path(p) for p in dialog.GetPaths()] if multiple else [Path(dialog.GetPath())]
        finally:
            dialog.Destroy()


__all__ = [
    "COMMON_ROWS",
    "ENTRY_KEY",
    "AppScribeHost",
    "AppScribeMixin",
    "append_scribe_submenu",
    "editor_name",
    "elsewhere_steps",
    "open_elsewhere",
    "open_in_editor",
]
