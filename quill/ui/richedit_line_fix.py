r"""Make the braille fix and a correct final empty line coexist.

``SES_EMULATESYSEDIT`` -- the #616/#813 braille fix, on by default -- asks
RICHEDIT50W to behave like the classic EDIT control. It buys braille output from
cell 1 and selection dots 7-8, and it costs one thing: with the flag on, the
control answers the *caret's line* wrongly whenever the caret sits at the very
end of a document that ends in a paragraph mark. Type "This is a test.", press
Enter, and the control says the caret is on line 0, "This is a test." -- so a
screen reader speaks that line instead of saying "blank", on every empty line at
the end of every document.

Measured on RICHEDIT50W (Riched20 10.0.26100), text ``"This is a test.\r"``,
caret at 16:

===========================  ==============  =============
question                     flag off        flag on
===========================  ==============  =============
``EM_GETLINECOUNT``          2               2
``EM_LINEINDEX`` (line 1)    16              16
``EM_EXLINEFROMCHAR`` (16)   1               **0**
``EM_LINEFROMCHAR`` (-1)     1               **0**
``EM_LINEINDEX`` (-1)        16              **0**
``EM_LINELENGTH`` (16)       0               **15**
===========================  ==============  =============

That is the whole of it, and note what is *not* wrong: the line count is right,
line 1 exists, ``EM_LINEINDEX`` for an explicit line is right, ``EM_GETLINE``
returns the empty string for it, and interior empty lines are answered correctly
(``"alpha\n\nbeta"`` reports line 1 for the caret on the middle blank). Only the
character-to-line mapping past the start of the final line is wrong, and it
contradicts the control's own answers -- line 1 starts at 16, yet character 16 is
said to be on line 0.

Because the control already knows every fact needed to compute the right answer,
this module installs a ``comctl32`` window subclass that supplies it: every
character index at or after the last line's start is on the last line, which is
true of any document and therefore never disagrees with a control that is already
answering correctly. The correction is what a screen reader sees, because a
subclass sits in the window procedure and a cross-process ``SendMessage`` is
dispatched through it -- verified from a second process, which is a screen
reader's situation exactly.

Two constraints found the same way and worth writing down, because they rule out
the simpler fixes somebody will reach for first:

* ``SES_EMULATESYSEDIT`` is **set-once**. ``EM_SETEDITSTYLE`` is ignored once the
  control holds text -- it cannot be turned on later and, more surprisingly, it
  cannot be turned off again either. So the flag cannot be lifted around a screen
  reader's question, and the preference genuinely needs the editor rebuilt
  (Preferences already says so).
* There is no caret position that reports correctly, so nothing can be fixed by
  moving the caret; and wx-level arithmetic cannot help either, because a screen
  reader asks the window, not wx.

Install is best-effort and never fatal: off Windows, or if anything at all fails,
the editor is exactly what it was.

**Sitting in a window procedure is the sharp edge here**, and getting it wrong
does not misreport a line -- it ends the process, with whatever was unsaved in
it. ``DefSubclassProc`` was observed faulting under this module in the nightly
UIA suite (an out-of-process client driving the editor, which is a screen
reader's situation exactly), and it presented as a robot failing to find the
main window rather than as a crash.

Four rules came out of that, in the order they were learned:

* The subclass comes off at ``WM_NCDESTROY``, in the procedure itself -- the
  documented place, and the only moment after which no further message can
  arrive. Detaching from a wx destroy event, which this module used to do, runs
  while the HWND is still alive and still being sent messages.
* A detached callback is **retired, never freed**. ``RemoveWindowSubclass``
  unhooks the trampoline; it does not promise nobody is *inside* it, and a
  cross-process ``SendMessage`` blocks in the window procedure. See
  :data:`_RETIRED`.
* The registry entry is dropped **only when removal actually succeeded**.
  A window that still carries the subclass must stay recorded, or the next
  install adds a second entry under the same id with a different procedure
  pointer: two links in one chain, one of them retired.
* And the call into the chain is **guarded**. The first three rules made the
  fault rarer -- four occurrences in a run became one -- and rarer is not
  fixed; one crash loses the document just as thoroughly. So a fault is caught,
  logged with the message number that caused it, and answered by detaching from
  that control. The correction is lost for it, which is a line number; the
  alternative was the editor. This module's contract has always been
  best-effort and never fatal, and that contract now covers the call where
  every observed crash actually happened.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Any

_log = logging.getLogger(__name__)

_WM_USER = 0x0400
_WM_NCDESTROY = 0x0082
_EM_GETSEL = 0x00B0
_EM_GETLINECOUNT = 0x00BA
_EM_LINEINDEX = 0x00BB
_EM_LINELENGTH = 0x00C1
_EM_LINEFROMCHAR = 0x00C9
_EM_EXLINEFROMCHAR = _WM_USER + 54
_EM_GETTEXTLENGTHEX = _WM_USER + 95

# EM_GETTEXTLENGTHEX flags (richedit.h). NUMCHARS|PRECISE is the only length that
# can be trusted here: WM_GETTEXTLENGTH is allowed to over-count, because it has
# to allow for the CR the control stores becoming CRLF for a caller who asks for
# the text.
_GTL_PRECISE = 0x02
_GTL_NUMCHARS = 0x08
_CP_UNICODE = 1200

#: Our subclass slot on the window. Any constant will do; this one is "QL".
_SUBCLASS_ID = 0x514C

#: The four questions this module answers; everything else goes straight through.
_WATCHED = frozenset({_EM_EXLINEFROMCHAR, _EM_LINEFROMCHAR, _EM_LINEINDEX, _EM_LINELENGTH})


class _GetTextLengthEx(ctypes.Structure):
    _fields_ = [("flags", wintypes.DWORD), ("codepage", wintypes.UINT)]


_AVAILABLE = sys.platform == "win32"
_user32: Any = None
_comctl32: Any = None
_SUBCLASSPROC: Any = None

if _AVAILABLE:  # pragma: no cover - exercised on Windows only
    try:
        _user32 = ctypes.WinDLL("user32", use_last_error=True)
        _comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
        _SUBCLASSPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong,
            wintypes.HWND,
            ctypes.c_uint,
            ctypes.c_longlong,
            ctypes.c_longlong,
            ctypes.c_uint,
            ctypes.c_ulonglong,
        )
        _comctl32.SetWindowSubclass.restype = wintypes.BOOL
        _comctl32.SetWindowSubclass.argtypes = [
            wintypes.HWND,
            _SUBCLASSPROC,
            ctypes.c_uint,
            ctypes.c_ulonglong,
        ]
        _comctl32.RemoveWindowSubclass.restype = wintypes.BOOL
        _comctl32.RemoveWindowSubclass.argtypes = [
            wintypes.HWND,
            _SUBCLASSPROC,
            ctypes.c_uint,
        ]
        _comctl32.DefSubclassProc.restype = ctypes.c_longlong
        _comctl32.DefSubclassProc.argtypes = [
            wintypes.HWND,
            ctypes.c_uint,
            ctypes.c_longlong,
            ctypes.c_longlong,
        ]
        _user32.IsWindow.restype = wintypes.BOOL
        _user32.IsWindow.argtypes = [wintypes.HWND]
    except Exception:  # noqa: BLE001 - no corrector is better than no editor
        _AVAILABLE = False

#: hwnd -> the live ``_SUBCLASSPROC``. A callback that is garbage collected while
#: the window still points at it takes the process down, so the reference lives
#: here for exactly as long as the subclass is installed.
_INSTALLED: dict[int, Any] = {}

#: Callbacks that have been detached and are never freed.
#:
#: ``RemoveWindowSubclass`` unhooks the trampoline; it does not promise nobody is
#: *inside* it. A cross-process ``SendMessage`` -- which is a screen reader's
#: situation, and the whole reason this module subclasses at all -- blocks in the
#: window procedure, so a message can be sitting in our frame at the instant the
#: subclass comes off. Dropping the last reference there frees the trampoline
#: under the caller and the process dies with an access violation inside
#: ``DefSubclassProc``.
#:
#: That is not hypothetical: it is what took QUILL down mid-run in the nightly
#: UIA suite, over and over ("access violation reading 0xFFFFFFFFFFFFFFFF"),
#: which read as a robot failure rather than as a crash.
#:
#: The cost of never freeing is a few dozen bytes per editor ever opened, for the
#: life of the process. The cost of freeing it at the wrong moment is the
#: document the user had not saved.
_RETIRED: list[Any] = []


#: Windows we have stopped correcting because the chain faulted under us. Kept
#: so the fault is reported once per control rather than on every keystroke, and
#: so a reinstall cannot put us back into a chain that has already misbehaved.
_FAULTED: set[int] = set()


def _fault_detach(hwnd: Any) -> None:
    """Come off a window whose subclass chain has faulted, and stay off.

    Best-effort twice over: the detach itself may fault, and if it does there is
    nothing further to try -- the control keeps whatever behaviour it has and
    the editor keeps running, which is the only outcome that matters here.
    """
    try:
        key = int(hwnd) if hwnd else 0
    except (TypeError, ValueError):  # pragma: no cover - a handle we cannot read
        return
    _FAULTED.add(key)
    try:
        remove_final_line_fix(key)
    except Exception:  # noqa: BLE001 - a failed detach must not raise into the loop
        _INSTALLED.pop(key, None)


def _default(hwnd: Any, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    """Ask the control itself, below our correction."""
    return int(_comctl32.DefSubclassProc(hwnd, msg, wparam, lparam))


def _caret(hwnd: Any) -> int:
    """The caret (the selection's active end), from the control."""
    start = wintypes.DWORD()
    end = wintypes.DWORD()
    _default(hwnd, _EM_GETSEL, ctypes.addressof(start), ctypes.addressof(end))
    return int(end.value)


def _text_length(hwnd: Any) -> int:
    """The document's length in characters."""
    request = _GetTextLengthEx(_GTL_NUMCHARS | _GTL_PRECISE, _CP_UNICODE)
    return int(_default(hwnd, _EM_GETTEXTLENGTHEX, ctypes.addressof(request), 0))


def _correction(hwnd: Any, msg: int, wparam: int, lparam: int) -> int | None:
    """The right answer for one of the four questions, or ``None`` to pass it on.

    Every character index at or after the last line's start is on the last line.
    That is true of any Rich Edit, which is why this can be applied without first
    sniffing for the bug: a control that is answering correctly already agrees.
    """
    lines = _default(hwnd, _EM_GETLINECOUNT)
    if lines <= 1:
        return None
    last = lines - 1
    last_start = _default(hwnd, _EM_LINEINDEX, last)
    if last_start < 0:
        return None
    if msg == _EM_EXLINEFROMCHAR:
        position = lparam if lparam >= 0 else _caret(hwnd)
        return last if position >= last_start else None
    if msg == _EM_LINEFROMCHAR:
        position = wparam if wparam >= 0 else _caret(hwnd)
        return last if position >= last_start else None
    if msg == _EM_LINEINDEX:
        # Only the "line the caret is on" form (-1) is ever wrong.
        if wparam < 0 and _caret(hwnd) >= last_start:
            return last_start
        return None
    if msg == _EM_LINELENGTH and wparam >= last_start:
        return max(0, _text_length(hwnd) - last_start)
    return None


def install_final_line_fix(surface: Any) -> bool:
    """Correct the caret line for ``surface``; return whether the subclass took.

    Call this only when ``SES_EMULATESYSEDIT`` has been applied -- with the flag
    off the control is already right, and there is no reason to sit in the message
    loop of a control that has nothing wrong with it. Safe to call twice; the
    second call is a no-op.
    """
    if not _AVAILABLE:
        return False
    try:
        hwnd = int(surface.GetHandle())
    except Exception:  # noqa: BLE001 - no handle yet, nothing to subclass
        return False
    if not hwnd or hwnd in _FAULTED:
        return False
    if hwnd in _INSTALLED:
        # A live window we are already on. A *dead* one whose handle Windows has
        # since recycled is a different matter: the entry is stale, and refusing
        # to install would leave the new editor uncorrected forever with no sign
        # of why. Ask the OS which it is rather than assuming.
        if _user32 is not None and not _user32.IsWindow(ctypes.c_void_p(hwnd)):
            _RETIRED.append(_INSTALLED.pop(hwnd))
        else:
            return False

    def _proc(hwnd_: Any, msg: int, wparam: int, lparam: int, _id: int, _data: int) -> int:
        if msg == _WM_NCDESTROY:
            # The documented place to come off, and the only safe one: the
            # window is going for good and no further message can reach us
            # after this one returns. Detaching from a wx destroy event instead
            # (which is what this module used to do) runs while the HWND is
            # still alive and still being sent messages.
            remove_final_line_fix(hwnd_)
        elif msg in _WATCHED:
            try:
                answer = _correction(hwnd_, msg, wparam, lparam)
            except Exception:  # noqa: BLE001 - never take the message loop down
                answer = None
            if answer is not None:
                return answer
        try:
            return int(_comctl32.DefSubclassProc(hwnd_, msg, wparam, lparam))
        except OSError as exc:
            # The subclass chain faulted underneath us. ctypes turns the
            # structured exception into an OSError, which is the only reason
            # this is catchable at all -- and catching it is the difference
            # between "the final empty line stops being corrected" and "the
            # editor is gone, with whatever was unsaved in it".
            #
            # This module's contract is best-effort and never fatal. It was
            # honoured for `_correction` and not for the call below, which is
            # where every observed crash actually happened.
            _log.warning(
                "RichEdit subclass faulted on message 0x%04X for hwnd %s (%s); "
                "detaching and leaving the control uncorrected",
                msg,
                hwnd_,
                exc,
            )
            _fault_detach(hwnd_)
            return 0

    callback = _SUBCLASSPROC(_proc)
    try:
        took = bool(_comctl32.SetWindowSubclass(ctypes.c_void_p(hwnd), callback, _SUBCLASS_ID, 0))
    except Exception:  # noqa: BLE001 - best-effort, as everywhere in this module
        return False
    if not took:
        return False
    _INSTALLED[hwnd] = callback
    return True


def remove_final_line_fix(hwnd: int) -> bool:
    """Uninstall the correction for ``hwnd`` (idempotent).

    Order matters, and the old order was the bug. This used to ``pop`` the
    callback out of :data:`_INSTALLED` and *then* call
    ``RemoveWindowSubclass`` -- so if that call failed or raised, the only
    strong reference was already gone and Python freed a trampoline the window
    still pointed at. The next message into it was an access violation.

    Now the subclass comes off first, and the callback is retired rather than
    released even on success: see :data:`_RETIRED` for why a successful removal
    still does not mean nobody is inside it.
    """
    key = int(hwnd) if hwnd else 0
    callback = _INSTALLED.get(key)
    if callback is None or not _AVAILABLE:
        return False
    # Retire first, always. From here the trampoline can never be collected,
    # whatever happens to the removal below.
    _RETIRED.append(callback)
    try:
        took = bool(_comctl32.RemoveWindowSubclass(ctypes.c_void_p(key), callback, _SUBCLASS_ID))
    except Exception:  # noqa: BLE001 - the window is going away regardless
        return False
    if took:
        # Only on success. A window that still carries our subclass must stay in
        # the registry, or the next install would add a *second* entry under the
        # same id with a different procedure pointer -- two links in one chain,
        # one of them retired, which is its own way to fault.
        _INSTALLED.pop(key, None)
    return took


def is_installed(hwnd: int) -> bool:
    """Whether the correction is currently on ``hwnd``."""
    return int(hwnd) in _INSTALLED
