"""The low-level keyboard hook behind system-wide abbreviation expansion.

A ``WH_KEYBOARD_LL`` hook on a dedicated thread with its own message pump. The
hook procedure itself does almost nothing: it decodes the key to a character,
appends it to a bounded in-memory buffer, and -- when a word ends -- hands any
match to a worker thread. That discipline matters. Windows silently removes a
low-level hook whose procedure is slow (``LowLevelHooksTimeout``), so typing
the expansion must never happen inside the callback.

What is deliberately *not* here: any persistence, any logging of keys, and any
decision based on what was typed. See
:mod:`quill.core.expansion.ring_buffer` for the memory's limits and
:mod:`quill.core.expansion.targets` for where expansion refuses to run.

Windows-only, wx-free. The caller supplies the library and receives matches on a
worker thread; marshalling to the UI thread is the caller's job.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import queue
import threading
import time
from collections.abc import Callable

from quill.core.abbreviations import AbbreviationLibrary, resolve_expansion
from quill.core.expansion.matcher import TRIGGER_CHARS, GlobalMatch, match_buffer
from quill.core.expansion.ring_buffer import RingBuffer
from quill.core.expansion.targets import is_denied_target
from quill.core.expansion.undo import UndoPlan, UndoTracker
from quill.platform.windows.foreground import foreground_window_info
from quill.platform.windows.text_injector import INJECTION_SIGNATURE

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_WH_KEYBOARD_LL = 13
_WM_KEYDOWN = 0x0100
_WM_SYSKEYDOWN = 0x0104
_WM_QUIT = 0x0012
#: Our own message, posted to the hook thread to ask it to re-install the hook.
_WM_REFRESH_HOOK = 0x0400 + 91  # WM_APP + 91

#: How often the hook is re-installed. Windows removes a low-level hook whose
#: procedure exceeds ``LowLevelHooksTimeout`` and tells nobody -- there is no
#: API to ask whether a hook is still live. Re-installing on a slow timer means
#: the worst case is a few minutes of no expansion rather than the rest of the
#: session, and it costs one API call.
_REFRESH_SECONDS = 180.0

_VK_BACK = 0x08
_VK_TAB = 0x09
_VK_RETURN = 0x0D
_VK_SHIFT = 0x10
_VK_CONTROL = 0x11
_VK_MENU = 0x12
_VK_RMENU = 0xA5  # right Alt -- AltGr's other half
_VK_CAPITAL = 0x14
_VK_ESCAPE = 0x1B
_VK_SPACE = 0x20

#: Keys that mean "the word I was typing is no longer under the caret".
_NAVIGATION_VKS: frozenset[int] = frozenset({
    0x21,  # Page Up
    0x22,  # Page Down
    0x23,  # End
    0x24,  # Home
    0x25,  # Left
    0x26,  # Up
    0x27,  # Right
    0x28,  # Down
    0x2D,  # Insert
    0x2E,  # Delete
    *range(0x70, 0x88),  # F1-F24
})

_HIGH_BIT = 0x80


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


_HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
)


class ExpansionHook:
    """Watches typing system-wide and reports abbreviation matches.

    ``get_library`` is called for each candidate word, so edits in the manager
    take effect immediately. ``on_match`` runs on a worker thread and is
    expected to perform the injection. ``excluded_processes`` supplies the
    user's own additions to the built-in deny-list.
    """

    def __init__(
        self,
        on_match: Callable[[GlobalMatch], None],
        get_library: Callable[[], AbbreviationLibrary],
        *,
        get_clipboard_text: Callable[[], str] | None = None,
        excluded_processes: Callable[[], set[str]] | None = None,
        on_undo: Callable[[UndoPlan], None] | None = None,
        on_unreachable_window: Callable[[], None] | None = None,
    ) -> None:
        self._on_match = on_match
        self._get_library = get_library
        self._get_clipboard_text = get_clipboard_text or (lambda: "")
        self._excluded_processes = excluded_processes or (lambda: set())
        self._on_undo = on_undo
        self._on_unreachable = on_unreachable_window
        self._undo = UndoTracker()
        self._reported_windows: set[int] = set()
        self._buffer = RingBuffer()
        self._enabled = threading.Event()
        self._enabled.set()
        self._hook_handle: int | None = None
        self._hook_thread: threading.Thread | None = None
        self._hook_thread_id = 0
        self._callback: object = None  # kept alive while the hook is installed
        self._work: queue.Queue[GlobalMatch | UndoPlan | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._watchdog: threading.Thread | None = None
        self._stopping = threading.Event()
        self._last_hwnd = 0

    # -- lifecycle --------------------------------------------------------------

    def start(self) -> None:
        """Install the hook. Safe to call twice."""
        if self._hook_thread is not None:
            return
        self._worker = threading.Thread(
            target=self._run_worker, name="quill-expansion-worker", daemon=True
        )
        self._worker.start()
        self._hook_thread = threading.Thread(
            target=self._run_hook, name="quill-expansion-hook", daemon=True
        )
        self._hook_thread.start()
        self._watchdog = threading.Thread(
            target=self._run_watchdog, name="quill-expansion-watchdog", daemon=True
        )
        self._watchdog.start()

    def stop(self) -> None:
        """Uninstall the hook and stop every thread. Safe to call twice."""
        self._stopping.set()
        thread = self._hook_thread
        self._hook_thread = None
        if thread is not None and self._hook_thread_id:
            _user32.PostThreadMessageW(self._hook_thread_id, _WM_QUIT, 0, 0)
            thread.join(timeout=2.0)
        self._hook_thread_id = 0
        worker = self._worker
        self._worker = None
        if worker is not None:
            self._work.put(None)
            worker.join(timeout=2.0)
        watchdog = self._watchdog
        self._watchdog = None
        if watchdog is not None:
            watchdog.join(timeout=2.0)
        self._buffer.clear()

    def pause(self) -> None:
        """Stop expanding without uninstalling (Options > Pause expansion)."""
        self._enabled.clear()
        self._buffer.clear()

    def resume(self) -> None:
        self._buffer.clear()
        self._enabled.set()

    @property
    def active(self) -> bool:
        return self._enabled.is_set()

    @property
    def installed(self) -> bool:
        return self._hook_handle is not None

    # -- hook thread ------------------------------------------------------------

    def _run_hook(self) -> None:
        self._hook_thread_id = int(_kernel32.GetCurrentThreadId())
        callback = _HOOKPROC(self._hook_proc)
        self._callback = callback  # a dropped reference would crash the hook
        self._hook_handle = _user32.SetWindowsHookExW(
            _WH_KEYBOARD_LL, callback, _kernel32.GetModuleHandleW(None), 0
        )
        if not self._hook_handle:
            logger.error(
                "Could not install the expansion keyboard hook (error %d)",
                _kernel32.GetLastError(),
            )
            self._hook_handle = None
            return
        logger.info("System-wide expansion hook installed")
        msg = ctypes.wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == _WM_REFRESH_HOOK:
                self._reinstall_hook()
                continue
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))
        if self._hook_handle:
            _user32.UnhookWindowsHookEx(self._hook_handle)
        self._hook_handle = None
        self._callback = None
        logger.info("System-wide expansion hook removed")

    def _reinstall_hook(self) -> None:
        """Replace the hook with a fresh one, on the hook thread.

        A low-level hook must be installed from a thread with a message loop,
        which is this one. The old handle is released first; if the new call
        fails the old handle is already gone, so the failure is logged loudly
        rather than leaving a half-state nobody can see.
        """
        previous = self._hook_handle
        handle = _user32.SetWindowsHookExW(
            _WH_KEYBOARD_LL, self._callback, _kernel32.GetModuleHandleW(None), 0
        )
        if not handle:
            logger.error(
                "Could not refresh the expansion keyboard hook (error %d); keeping the old one",
                _kernel32.GetLastError(),
            )
            return
        self._hook_handle = handle
        if previous:
            _user32.UnhookWindowsHookEx(previous)

    def _run_watchdog(self) -> None:
        """Ask the hook thread to re-install the hook, forever, slowly."""
        while not self._stopping.wait(_REFRESH_SECONDS):
            if self._hook_thread_id and self._hook_handle:
                _user32.PostThreadMessageW(self._hook_thread_id, _WM_REFRESH_HOOK, 0, 0)

    def _hook_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        try:
            if n_code >= 0 and self._enabled.is_set() and w_param in (_WM_KEYDOWN, _WM_SYSKEYDOWN):
                event = ctypes.cast(l_param, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if (event.dwExtraInfo or 0) != INJECTION_SIGNATURE and self._handle_key(
                    int(event.vkCode)
                ):
                    # Swallow the trigger key. It has not reached the
                    # application yet, and letting it through would race the
                    # backspaces we are about to send -- the classic way an
                    # expander corrupts the very word it is replacing. The
                    # worker types it back after the expansion instead, so the
                    # keystroke still lands exactly where the user put it.
                    return 1
        except Exception:  # noqa: BLE001
            # A raising hook procedure would be removed by Windows, silently
            # ending expansion for the session. Losing one keystroke is better.
            logger.exception("Expansion hook callback failed")
        return int(_user32.CallNextHookEx(self._hook_handle or 0, n_code, w_param, l_param))

    def _handle_key(self, vk: int) -> bool:
        """Feed one key to the buffer. True when the key was consumed."""
        if vk in (_VK_ESCAPE,) or vk in _NAVIGATION_VKS:
            self._buffer.clear()
            self._undo.clear()
            return False
        if vk == _VK_BACK:
            self._buffer.backspace()
            self._maybe_undo()
            return False
        if vk in (_VK_SHIFT, _VK_CONTROL, _VK_MENU, _VK_CAPITAL):
            return False
        # A Ctrl or Alt combination is a command, not typing -- *unless* it is
        # AltGr, which Windows reports as Ctrl+Alt and which types real
        # characters on most European layouts (@ on Polish, € on German, ł, ą).
        # Treating that as a command wiped the buffer mid-word and made
        # expansion look broken for everyone outside a US layout.
        if (_key_down(_VK_CONTROL) or _key_down(_VK_MENU)) and not _is_altgr_char(vk):
            self._buffer.clear()
            self._undo.clear()
            return False

        window = foreground_window_info()
        if window.hwnd != self._last_hwnd:
            # Focus moved: whatever was half-typed is not under the caret now.
            self._last_hwnd = window.hwnd
            self._buffer.clear()
            self._undo.clear()
            self._note_window(window.hwnd)
        if is_denied_target(
            window.process_name,
            window.title,
            window.window_class,
            extra_processes=frozenset(self._excluded_processes()),
        ):
            self._buffer.clear()
            self._undo.clear()
            return False
        if self._window_expands_for_itself(window.hwnd):
            # QUILL's editor (and any other window that claims this) expands
            # from the document itself. Doing it here as well would fire twice
            # on one keystroke and mangle the text.
            self._buffer.clear()
            self._undo.clear()
            return False

        char = _key_to_char(vk)
        if char is None:
            self._buffer.clear()
            return False
        self._buffer.push(char)

        try:
            library = self._get_library()
        except Exception:  # noqa: BLE001
            return False
        match = match_buffer(self._buffer, library, self._get_clipboard_text())
        if match is None:
            return False
        self._buffer.clear()
        return self._queue_match(match)

    def _queue_match(self, match: GlobalMatch) -> bool:
        """Hand a match to the worker, if this really is a place to type.

        The editable check happens here rather than on every keystroke: it is
        the one moment it matters, and asking UI Automation per key would put
        COM calls on the hot path of everything the user types. Returns whether
        the trigger key should be swallowed -- which is exactly when an
        expansion is going to happen.
        """
        if not self._is_editable():
            return False
        self._work.put(match)
        return True

    def _window_expands_for_itself(self, hwnd: int) -> bool:
        try:
            from quill.platform.windows.text_target import window_handles_own_expansion

            return window_handles_own_expansion(hwnd)
        except Exception:  # noqa: BLE001
            return False

    def _is_editable(self) -> bool:
        try:
            from quill.platform.windows.text_target import is_editable_target

            return is_editable_target()
        except Exception:  # noqa: BLE001 - unknown means "go ahead"
            return True

    def _maybe_undo(self) -> None:
        """Backspace immediately after an expansion puts the abbreviation back."""
        plan = self._undo.take_undo(
            window_handle=int(_user32.GetForegroundWindow() or 0), now=time.monotonic()
        )
        if plan is not None:
            self._work.put(plan)

    def _note_window(self, hwnd: int) -> None:
        """Tell the caller once when focus lands somewhere we cannot reach.

        A normal-privilege process never sees an elevated window's keys, so
        expansion there does nothing at all. Reporting it -- once per window --
        is the difference between "this app is unsupported" and "this feature
        is broken".
        """
        if self._on_unreachable is None or not hwnd or hwnd in self._reported_windows:
            return
        try:
            from quill.platform.windows.text_target import unreachable_because_elevated

            if not unreachable_because_elevated(hwnd):
                return
        except Exception:  # noqa: BLE001
            return
        self._reported_windows.add(hwnd)
        self._on_unreachable()

    # -- manual expansion --------------------------------------------------------

    def expand_now(self) -> bool:
        """Expand the word just typed, without waiting for a trigger character.

        The global counterpart of QUILL's "Expand Abbreviation" command: it
        works mid-word, at the end of a line, and for entries whose trigger mode
        is ``manual``. Returns False when the buffer's last word matches nothing.
        """
        text = self._buffer.text()
        token = ""
        for char in reversed(text):
            if char.isspace() or char in TRIGGER_CHARS:
                break
            token = char + token
        if not token:
            return False
        try:
            library = self._get_library()
        except Exception:  # noqa: BLE001
            return False
        entry = library.find_by_trigger(token)
        if entry is None:
            return False
        resolved, cursor_offset, has_cursor = resolve_expansion(
            entry.expansion, self._get_clipboard_text()
        )
        self._buffer.clear()
        self._work.put(
            GlobalMatch(
                abbreviation=entry,
                text=resolved,
                backspace_count=len(token),
                cursor_offset=cursor_offset,
                has_cursor=has_cursor,
                trailing_space=False,
            )
        )
        return True

    def note_expansion(
        self, *, abbreviation: str, expanded_text: str, trailing_space: bool
    ) -> None:
        """Arm the undo for an expansion the caller has just performed."""
        self._undo.record(
            abbreviation=abbreviation,
            expanded_text=expanded_text,
            trailing_space=trailing_space,
            window_handle=int(_user32.GetForegroundWindow() or 0),
            now=time.monotonic(),
        )

    # -- worker thread ----------------------------------------------------------

    def _run_worker(self) -> None:
        while True:
            item = self._work.get()
            if item is None:
                return
            try:
                if isinstance(item, UndoPlan):
                    if self._on_undo is not None:
                        self._on_undo(item)
                else:
                    self._on_match(item)
            except Exception:  # noqa: BLE001
                logger.exception("Expansion failed")


def _is_altgr_char(vk: int) -> bool:
    """Whether this key, with the modifiers currently held, types a character.

    Windows reports AltGr as left-Ctrl plus right-Alt, so a naive "any Ctrl or
    Alt means a command" rule throws away real typing on every layout that uses
    AltGr -- German, Polish, Spanish, Portuguese, the Nordic layouts, and more.
    The reliable test is to ask the layout itself: if right Alt is down and the
    key still resolves to a printable character, the user is typing, not
    invoking a command.
    """
    if not _key_down(_VK_RMENU):
        return False
    char = _key_to_char(vk)
    return char is not None and char.isprintable()


def _key_down(vk: int) -> bool:
    return bool(_user32.GetKeyState(vk) & 0x8000)


def _key_to_char(vk: int) -> str | None:
    """The character *vk* produces right now, or None when it is not typing.

    Uses the foreground window's own keyboard layout, so a non-US layout
    expands the abbreviations its user actually types. A dead key (accents on
    many European layouts) returns None *and* is pushed back into the layout's
    state, so the accent the user is composing still reaches their application.
    """
    if vk == _VK_SPACE:
        return " "
    if vk == _VK_RETURN:
        return "\n"
    if vk == _VK_TAB:
        return "\t"

    layout = _foreground_keyboard_layout()
    state = (ctypes.c_ubyte * 256)()
    if not _user32.GetKeyboardState(ctypes.byref(state)):
        return None
    # GetKeyboardState reports the *hook thread's* view, which does not see the
    # modifiers of the thread actually typing; ask the system directly.
    state[_VK_SHIFT] = _HIGH_BIT if _key_down(_VK_SHIFT) else 0
    state[_VK_CAPITAL] = 0x01 if (_user32.GetKeyState(_VK_CAPITAL) & 0x0001) else 0

    scan = _user32.MapVirtualKeyExW(vk, 0, layout)  # MAPVK_VK_TO_VSC
    buf = ctypes.create_unicode_buffer(8)
    result = int(_user32.ToUnicodeEx(vk, scan, ctypes.byref(state), buf, 8, 0, layout))
    if result < 0:
        # A dead key. ToUnicodeEx has just consumed the layout's pending state,
        # so replay it to leave the composition exactly as it was.
        _user32.ToUnicodeEx(vk, scan, ctypes.byref(state), buf, 8, 0, layout)
        return None
    if result < 1:
        return None
    char = buf.value[0] if buf.value else ""
    if not char or not (char.isprintable() or char in ("\n", "\t")):
        return None
    return char


def _foreground_keyboard_layout() -> int:
    try:
        hwnd = _user32.GetForegroundWindow()
        thread_id = _user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0
        return int(_user32.GetKeyboardLayout(thread_id))
    except Exception:  # noqa: BLE001
        return 0
