"""The document port for Dictate Anywhere: words typed into another program.

dict.md 3.9 (gap 8). The shared controller writes through a document port; in
an editor that is a text control it can read (``windows_dictation_ports``).
Here it is whatever program is in front, which Quill Inkwell can type into but
cannot read. So this port remembers only what *it* typed, since the focus last
moved, and answers from that:

* the text before the cursor, for the spacing and capital rules, is the tail
  of what was typed here;
* "scratch that" sends backspaces for the last phrase -- only while the same
  window still has the focus, because anything else would erase somebody's
  typing;
* the screen reader's echo of the typing is cut short when phrases are not
  read back (:func:`hush_unless_spoken`): only the last key survives it, so
  every phrase ended in "period";
* nothing else can be read, so ``external`` tells the controller to refuse the
  commands that need to (``anywhere.EXTERNAL_COMMANDS``).

It refuses, with a sentence, four places: a password field, a program running
as administrator when Inkwell is not (Windows blocks the typing), QUILL's own
windows, where Ctrl+F11 already dictates, and a program on the person's own
"never type here" list, matched by its file name
(:mod:`quill.core.windows_dictation.never_type`).

**One field, in every host** (D-15, 2026-10-13): :func:`locked_external_document`
wraps this port in :class:`~quill.core.windows_dictation.target_lock.LockedTarget`
with the sentences QUILL Transcribe and Quill Inkwell both say, so a focus move
pauses and holds the words in both, from one copy of the code.

The platform calls are passed in, so a test runs it against fakes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

__all__ = [
    "PAUSE_ADVICE",
    "WRITE_FAILURE",
    "ExternalDocument",
    "focus_identity",
    "foreground_problem",
    "hush_unless_spoken",
    "locked_external_document",
]

_TAIL = 80

#: What the person is told to do when dictation pauses for its field. QUILL
#: Transcribe and Quill Inkwell both have these three commands in their tray
#: menu (while paused) and their Dictation menu.
PAUSE_ADVICE = (
    "Go back and choose Resume, choose Resume in This Field to write here, or "
    "Discard Held Words. All three are in the tray menu and the Dictation menu."
)
#: Said when typing failed part-way: never "done".
WRITE_FAILURE = (
    "Dictation stopped: Windows did not take all of that phrase, so part of it "
    "may be missing. Check the field before you carry on."
)


def foreground_problem(
    *,
    app: str = "Quill Inkwell",
    key: str = "Dictate Anywhere key",
    never_type: Iterable[str] = (),
) -> str:
    """Why nothing should be typed into the window in front, or ``""``.

    *app* and *key* name the program doing the typing and the key that starts
    it, so QUILL Transcribe's refusals name QUILL Transcribe. *never_type* is
    the person's list of program file names (``windows_dictation_never_type``).
    """
    try:
        from quill.platform.windows.external_target import capture_uia_focus
        from quill.platform.windows.foreground import foreground_window_info
        from quill.platform.windows.text_target import (
            unreachable_because_elevated,
            window_handles_own_expansion,
        )
    except Exception:  # noqa: BLE001 - not Windows
        return f"{app} types into other programs on Windows only."
    import os

    window = foreground_window_info()
    if not window.hwnd:
        return "No program is in front to dictate into."
    if window.process_id == os.getpid():
        return f"Switch to the program you want to dictate into, then press the {key} there."
    from quill.core.windows_dictation.never_type import refusal

    listed = refusal(window.process_name, never_type)
    if listed:
        return listed
    if window_handles_own_expansion(window.hwnd):
        return "This is a QUILL window: press Ctrl+F11 to dictate here."
    if unreachable_because_elevated(window.hwnd):
        return (
            f"That program is running as administrator, so Windows will not let {app} type into it."
        )
    focus = capture_uia_focus()
    if focus is not None and focus.is_password:
        return "That is a password field, so nothing is typed there."
    return ""


def _where() -> Any:
    try:
        from quill.platform.windows.foreground import foreground_window_info
        from quill.platform.windows.text_target import focused_class_name

        return foreground_window_info().hwnd, focused_class_name()
    except Exception:  # noqa: BLE001 - not Windows
        return None


def focus_identity() -> Any:
    """Which field has the focus, as an identity to compare, never its text.

    The foreground window, its process, and the focused control: its UI
    Automation runtime id where UI Automation can say, else the native class of
    the focused child window. Used by QUILL Transcribe's target lock
    (:mod:`quill.core.windows_dictation.target_lock`); ``None`` off Windows.
    """
    try:
        from quill.platform.windows.external_target import capture_uia_focus
        from quill.platform.windows.foreground import foreground_window_info
        from quill.platform.windows.text_target import focused_class_name
    except Exception:  # noqa: BLE001 - not Windows
        return None
    window = foreground_window_info()
    element = capture_uia_focus()
    if element is not None and element.runtime_id:
        control: Any = ("uia", tuple(element.runtime_id))
    elif element is not None and element.native_window_handle:
        control = ("hwnd", element.native_window_handle)
    else:
        control = ("class", focused_class_name())
    return (window.hwnd, window.process_id, control)


def _type(text: str, hush: bool = False) -> bool:
    from quill.platform.windows.text_injector import send_text_checked

    return send_text_checked(text, hush_reader=hush).complete


def _backspace(count: int) -> bool:
    from quill.platform.windows.text_injector import send_backspaces_checked

    return send_backspaces_checked(count).complete


def hush_unless_spoken(preferences: Callable[[], Any]) -> Callable[[], bool]:
    """True when phrases are not read back (feedback is a tone or nothing):
    then the screen reader's echo of the typing is cut short. With the
    read-back on, the reader saying what went in is wanted, marks and all."""

    def hush() -> bool:
        from quill.core.action_feedback import resolve

        prefs = preferences()
        if getattr(prefs, "continuous", False):
            return True
        return not resolve(getattr(prefs, "phrase_feedback", "sound"), has_sound=True)[1]

    return hush


def locked_external_document(
    *,
    preferences: Callable[[], Any],
    never_type: Callable[[], Iterable[str]],
    app: str = "Quill Inkwell",
    key: str = "Dictate Anywhere key",
    hush: bool = True,
) -> Any:
    """The external document, locked to the field a session starts in.

    What QUILL Transcribe and Quill Inkwell's Dictate Anywhere both dictate
    into: a focus move pauses and holds the words (target_hold.py), and the
    same checks -- the never-type list among them -- run at every start and
    every Resume in This Field. *never_type* is read each time, so a list
    changed in the settings applies to the next phrase. *hush* off is the
    one-shot Insert Again, which reads nothing back.
    """
    from quill.core.windows_dictation.target_lock import LockedTarget

    def problem() -> str:
        return foreground_problem(app=app, key=key, never_type=tuple(never_type()))

    inner = ExternalDocument(
        problem=problem, hush=hush_unless_spoken(preferences) if hush else (lambda: False)
    )
    return LockedTarget(
        inner, where=focus_identity, advice=PAUSE_ADVICE, write_failure=WRITE_FAILURE
    )


class ExternalDocument:
    """The program in front, as far as dictation can know it."""

    #: Tells the controller this document cannot be read (voice_commands.py).
    external = True

    def __init__(
        self,
        *,
        problem: Callable[[], str] = foreground_problem,
        where: Callable[[], Any] = _where,
        type_text: Callable[..., bool] = _type,
        backspace: Callable[[int], bool] = _backspace,
        hush: Callable[[], bool] = lambda: False,
    ) -> None:
        self._problem = problem
        self._where = where
        self._type = type_text
        self._backspace = backspace
        self._hush = hush
        self._place: Any = None
        self._typed = ""

    def _follow_focus(self) -> None:
        """The focus moved: what was typed before is somebody else's text now."""
        place = self._where()
        if place != self._place:
            self._place = place
            self._typed = ""

    # -- the port ---------------------------------------------------------- #

    def unavailable_reason(self, *, writing: bool) -> str:
        del writing
        return str(self._problem())

    def context(self) -> tuple[str, str]:
        self._follow_focus()
        return self._typed[-_TAIL:], ""

    def selection(self) -> tuple[int, int]:
        return len(self._typed), len(self._typed)

    def select(self, start: int, end: int) -> None:
        del start, end  # another program's selection cannot be set from here

    def insert(self, text: str) -> tuple[int, int]:
        self._follow_focus()
        start = len(self._typed)
        if not (self._type(text, True) if self._hush() else self._type(text)):
            raise OSError("Windows did not accept all of the typing.")
        self._typed += text
        return start, len(self._typed)

    def text_between(self, start: int, end: int) -> str:
        if self._where() != self._place:
            return ""  # the focus moved: "scratch that" leaves it alone, and says so
        return self._typed[max(0, start) : end]

    def remove(self, start: int, end: int) -> None:
        if self._where() != self._place or end != len(self._typed) or start > end:
            raise OSError("The focus has moved, so nothing was taken back.")
        self._backspace(end - start)
        self._typed = self._typed[:start]

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.remove(start, end)
        return self.insert(text)

    def line_bounds(self) -> tuple[int, int]:
        return len(self._typed), len(self._typed)

    def last_position(self) -> int:
        return len(self._typed)

    def undo(self) -> bool:
        return False
