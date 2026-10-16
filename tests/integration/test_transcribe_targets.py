"""QUILL Transcribe's tested-programs harness (dict.md D-4).

Types a fixed list of recorded phrases -- what the dictation controller
writes, with no microphone and no recogniser -- through the shared
:class:`~quill.ui.windows_dictation_external.ExternalDocument`, the same port
QUILL Transcribe and Quill Inkwell type through, into real programs: Notepad,
WordPad, Word, Outlook, Edge, Chrome, Firefox and VS Code. Each phrase is read
back through UI Automation (TextPattern first) *in this test only*, and the
outcome is written to a JSON results file that
``scripts/build_transcribe_compatibility.py`` turns into the table in QUILL
Transcribe's user guide. D-3 (a per-program fallback) waits on what this finds:
a program that drops or reorders synthetic keys shows up here as phrases that
did not arrive exactly.

**It types into real programs, so it is fenced in on every side:**

* Never in CI, and never unless asked: ``QUILL_TRANSCRIBE_TARGETS=1``.
* Only on a computer nobody is using: no key or mouse input for 30 seconds
  before each program opens (``QUILL_TRANSCRIBE_TARGETS_IDLE_S``), and typing
  stops the moment Windows sees input that is not the test's own. The first
  run (2026-10-15) was spoiled by a person's Ctrl presses turning typed
  letters into Notepad shortcuts; that is what this rule is for.
* It types only into a window it launched itself, in a process that did not
  exist before the launch, whose title carries a random marker this run made,
  and whose focused field is empty when the first phrase goes. Before *and*
  after every phrase it checks that window is still in front and that UI
  Automation's focus is still inside its process; when either fails it stops
  typing at once and records the run as incomplete.
* Browsers and VS Code start with a throwaway profile in a temporary folder,
  so they never touch the person's own windows, tabs, sign-ins or settings.
  Notepad is skipped when Notepad is already open (it would open the file as a
  tab in the person's window). Outlook is skipped when it is already running,
  and runs at all only with ``QUILL_TRANSCRIBE_TARGETS_OUTLOOK=1``, because it
  opens the person's mailbox.
* It closes what it opened without saving: "Don't save" for Notepad's tab,
  ``Close(SaveChanges=False)`` for Word, discard for Outlook, and for the
  throwaway-profile programs a close followed by ending only the processes
  whose command line names that profile.

A program that is not installed is skipped and recorded as *untested*, never
as unsupported. A program not run this time keeps its previous row.

Run::

    $env:QUILL_TRANSCRIBE_TARGETS = "1"
    pytest tests/integration/test_transcribe_targets.py -v -p no:xdist

``QUILL_TRANSCRIBE_TARGETS_SURVEY=1`` launches nothing: it only records which
programs are installed, and their versions, as untested rows.

Results go to ``docs/qa/transcribe-targets.json`` (or
``QUILL_TRANSCRIBE_RESULTS``); then ``python scripts/build_transcribe_compatibility.py``.
"""

from __future__ import annotations

import contextlib
import ctypes
import datetime as _dt
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]
RESULTS_PATH = Path(
    os.environ.get("QUILL_TRANSCRIBE_RESULTS") or _REPO / "docs" / "qa" / "transcribe-targets.json"
)

pytestmark = [
    pytest.mark.machine_global,
    pytest.mark.skipif(sys.platform != "win32", reason="types into Windows programs"),
    pytest.mark.skipif(
        bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")),
        reason="never in CI: it opens and types into real programs",
    ),
    pytest.mark.skipif(
        os.environ.get("QUILL_TRANSCRIBE_TARGETS") != "1",
        reason="opt in with QUILL_TRANSCRIBE_TARGETS=1: it opens and types into real programs",
    ),
]

#: What the controller writes for a short dictation session, phrase by phrase,
#: spacing included: the controller puts the space before a phrase, never
#: after. Ordinary words, the punctuation dictation produces, digits, an
#: apostrophe, quotes, brackets and one new line -- the characters a program
#: is most likely to drop, reorder or treat as a shortcut.
PHRASES: tuple[str, ...] = (
    "Hello everyone.",
    " This is a test of dictation into another program.",
    " Commas, full stops and question marks?",
    " Yes!",
    " Numbers like 42 and 3.5 arrive intact.",
    " Don't lose the apostrophe.",
    ' She said "quoted words" here.',
    " Brackets (like these) stay put.",
    " A colon: and a semicolon; too.",
    "\nA new line starts here.",
    " The quick brown fox jumps over the lazy dog.",
    " Last phrase, then stop.",
)

#: How long a phrase may take to show up in UI Automation.
_SETTLE_S = 3.0
_LAUNCH_S = 90.0
#: How long nobody may have touched the keyboard or mouse before a program is
#: opened. Somebody else's keys mix with the test's -- a Ctrl held down turns
#: typed letters into the program's shortcuts -- and spoil the measurement.
IDLE_S = float(os.environ.get("QUILL_TRANSCRIBE_TARGETS_IDLE_S") or 30)

# --------------------------------------------------------------------------- #
# Windows plumbing (test-only)
# --------------------------------------------------------------------------- #

_user32: Any = None
if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetAncestor.restype = wintypes.HWND
    _user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
_WM_CLOSE = 0x0010
_GA_ROOT = 2
_VK_CONTROL = 0x11
_VK_W = 0x57


class _LastInput(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def _tick() -> int:
    return int(ctypes.windll.kernel32.GetTickCount())


def _last_input_tick() -> int:
    """When Windows last saw a key or the mouse, anyone's, as a tick count."""
    info = _LastInput(ctypes.sizeof(_LastInput), 0)
    _user32.GetLastInputInfo(ctypes.byref(info))
    return int(info.dwTime)


def _idle_seconds() -> float:
    return max(0, _tick() - _last_input_tick()) / 1000


def _window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
    return int(pid.value)


def _window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(wintypes.HWND(hwnd), buf, 512)
    return buf.value


def _top_windows() -> list[int]:
    found: list[int] = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd: Any, _lparam: Any) -> bool:
        if _user32.IsWindowVisible(hwnd):
            found.append(int(hwnd))
        return True

    _user32.EnumWindows(proc(visit), 0)
    return found


def _pids_named(image: str) -> set[int]:
    import psutil

    wanted = image.casefold()
    pids: set[int] = set()
    for proc in psutil.process_iter(["name"]):
        with contextlib.suppress(Exception):
            if (proc.info["name"] or "").casefold() == wanted:
                pids.add(proc.pid)
    return pids


def _family(pid: int) -> set[int]:
    """*pid* and every process it started: all of them are this run's."""
    import psutil

    with contextlib.suppress(Exception):
        return {pid, *(child.pid for child in psutil.Process(pid).children(recursive=True))}
    return {pid}


def _process_name(pid: int) -> str:
    """A process's file name, for saying what took the focus (never a title)."""
    import psutil

    with contextlib.suppress(Exception):
        return str(psutil.Process(pid).name())
    return "an unknown process" if pid else "no process"


def _file_version(pid: int) -> str:
    import psutil

    try:
        exe = psutil.Process(pid).exe()
    except Exception:  # noqa: BLE001
        return ""
    return _path_version(exe)


def _path_version(exe: str) -> str:
    with contextlib.suppress(Exception):
        import win32api

        info = win32api.GetFileVersionInfo(exe, "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    return ""


def _wait_for_window(
    image: str, before: set[int], marker: str, timeout: float = _LAUNCH_S
) -> tuple[int, int]:
    """The new window this run launched: its process is new, its title has *marker*."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        fresh = _pids_named(image) - before
        if fresh:
            for hwnd in _top_windows():
                pid = _window_pid(hwnd)
                if pid in fresh and marker in _window_title(hwnd):
                    return hwnd, pid
        time.sleep(0.25)
    raise _Skip(f"no new {image} window titled with this run's marker appeared")


def _bring_to_front(hwnd: int) -> bool:
    from quill.platform.windows.foreground import force_foreground_window

    for _ in range(20):
        if int(_user32.GetForegroundWindow() or 0) == hwnd:
            return True
        with contextlib.suppress(Exception):
            force_foreground_window(hwnd)
        time.sleep(0.25)
    return int(_user32.GetForegroundWindow() or 0) == hwnd


def _key_inputs(*pairs: tuple[int, bool]) -> None:
    from quill.platform.windows import text_injector as ti

    inputs = [ti._key(vk=vk, flags=0 if down else 0x0002) for vk, down in pairs]
    array = (ti._INPUT * len(inputs))(*inputs)
    _user32.SendInput(len(inputs), array, ctypes.sizeof(ti._INPUT))


# UI Automation ------------------------------------------------------------- #

_UIA_INVOKE = 10000
_UIA_VALUE = 10002
_UIA_TEXT = 10014
_UIA_LEGACY = 10018
_UIA_BUTTON = 50000
_UIA_DOCUMENT = 50030
_UIA_CONTROL_TYPE_PROP = 30003


def _uia() -> tuple[Any, Any]:
    import comtypes.client

    module = comtypes.client.GetModule("UIAutomationCore.dll")
    automation = comtypes.client.CreateObject(
        "{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=module.IUIAutomation
    )
    return automation, module


def _focused() -> tuple[Any, int]:
    automation, _ = _uia()
    element = automation.GetFocusedElement()
    return element, int(element.CurrentProcessId) if element is not None else 0


def _read_text(element: Any) -> tuple[str, str]:
    """The field's whole text, and which UI Automation pattern gave it."""
    _, module = _uia()
    with contextlib.suppress(Exception):
        pattern = element.GetCurrentPattern(_UIA_TEXT)
        if pattern is not None:
            text = pattern.QueryInterface(module.IUIAutomationTextPattern)
            return str(text.DocumentRange.GetText(-1) or ""), "TextPattern"
    with contextlib.suppress(Exception):
        pattern = element.GetCurrentPattern(_UIA_VALUE)
        if pattern is not None:
            value = pattern.QueryInterface(module.IUIAutomationValuePattern)
            return str(value.CurrentValue or ""), "ValuePattern"
    with contextlib.suppress(Exception):
        pattern = element.GetCurrentPattern(_UIA_LEGACY)
        if pattern is not None:
            legacy = pattern.QueryInterface(module.IUIAutomationLegacyIAccessiblePattern)
            return str(legacy.CurrentValue or ""), "LegacyIAccessible"
    return "", ""


def _invoke_button(hwnd: int, matches: Callable[[str], bool]) -> bool:
    automation, module = _uia()
    root = automation.ElementFromHandle(wintypes.HWND(hwnd))
    condition = automation.CreatePropertyCondition(_UIA_CONTROL_TYPE_PROP, _UIA_BUTTON)
    buttons = root.FindAll(4, condition)  # TreeScope_Descendants
    for index in range(buttons.Length):
        button = buttons.GetElement(index)
        name = str(button.CurrentName or "")
        if matches(name):
            pattern = button.GetCurrentPattern(_UIA_INVOKE)
            pattern.QueryInterface(module.IUIAutomationInvokePattern).Invoke()
            return True
    return False


def normalize(text: str) -> str:
    """What counts as the same text: line ends, and a program's own AutoFormat.

    Word turns straight quotes curly and every program has its own line end;
    neither is a lost key, so neither counts against a program.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    for curly, straight in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(curly, straight)
    return text.rstrip("\n")


# --------------------------------------------------------------------------- #
# Sessions and targets
# --------------------------------------------------------------------------- #


class _Skip(Exception):  # noqa: N818 - control flow inside this test only
    """Could not set the program up safely: skip it, typing nothing."""


@dataclass
class Session:
    hwnd: int
    pid: int
    marker: str
    version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    #: The tick by which every key this run sent had landed. Input Windows saw
    #: after it is somebody else's: the computer is in use, so typing stops.
    own_tick: int = 0

    def guard(self) -> str:
        """Why typing now could reach something this run did not open, or ``""``."""
        if self.own_tick and _last_input_tick() > self.own_tick:
            return "someone else used the keyboard or mouse during the run"
        hwnd = int(_user32.GetForegroundWindow() or 0)
        if hwnd != self.hwnd or _window_pid(hwnd) != self.pid:
            return f"another window came to the front ({_process_name(_window_pid(hwnd))})"
        if self.marker not in _window_title(hwnd):
            return "the window in front is no longer this run's document"
        try:
            element, pid = _focused()
        except Exception:  # noqa: BLE001
            return "UI Automation could not say where the focus is"
        if element is None or pid not in _family(self.pid):
            return f"the focus is outside the program this run opened (in {_process_name(pid)})"
        with contextlib.suppress(Exception):
            if element.CurrentIsPassword:
                return "the focus is on a password field"
        return ""


@dataclass(frozen=True)
class Target:
    key: str
    program: str
    find: Callable[[], str]  # the program's path, or "" when not installed
    open: Callable[[str, Path, str], Session]  # (path, workdir, marker)
    close: Callable[[Session], None]
    not_installed_note: str = ""


def _app_path(exe: str) -> str:
    import winreg

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        with contextlib.suppress(OSError):
            key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
            with winreg.OpenKey(hive, key) as handle:
                value = str(winreg.QueryValue(handle, None) or "").strip('"')
                if value and Path(value).is_file():
                    return value
    return shutil.which(exe) or ""


def _first_file(*candidates: str) -> str:
    for candidate in candidates:
        path = os.path.expandvars(candidate)
        if path and Path(path).is_file():
            return path
    return ""


def _wait_gone(pids: set[int], timeout: float) -> set[int]:
    import psutil

    deadline = time.monotonic() + timeout
    alive = set(pids)
    while alive and time.monotonic() < deadline:
        alive = {pid for pid in alive if psutil.pid_exists(pid)}
        time.sleep(0.25)
    return alive


def _end_processes_naming(token: str, image: str) -> None:
    """End only processes of *image* whose command line names *token* (our profile)."""
    import psutil

    for proc in psutil.process_iter(["name", "cmdline"]):
        with contextlib.suppress(Exception):
            if (proc.info["name"] or "").casefold() != image.casefold():
                continue
            if any(token in part for part in proc.info["cmdline"] or ()):
                proc.kill()


# Notepad ------------------------------------------------------------------- #


def _open_notepad(path: str, work: Path, marker: str) -> Session:
    if _pids_named("notepad.exe"):
        raise _Skip("Notepad is already open; it would open the file in that window")
    document = work / f"{marker}.txt"
    document.write_text("", encoding="utf-8")
    before = _pids_named("notepad.exe")
    subprocess.Popen([path, str(document)])  # noqa: S603 - Notepad, our own file
    hwnd, pid = _wait_for_window("notepad.exe", before, marker)
    return Session(hwnd, pid, marker, _file_version(pid), {"file": document})


def _close_notepad(session: Session) -> None:
    # Close this run's tab with Ctrl+W, saying Don't save, then the window.
    # Notepad's session restore keeps the person's own tabs that it reopened;
    # closing the window with this run's tab still in it would keep that tab
    # too, so the tab goes first, and the result says when it could not.
    session.own_tick = 0  # closing is still safe after somebody touched a key
    for _ in range(3):
        if session.marker not in _window_title(session.hwnd):
            break
        if not _bring_to_front(session.hwnd) or session.guard():
            time.sleep(1)
            continue
        _key_inputs((_VK_CONTROL, True), (_VK_W, True), (_VK_W, False), (_VK_CONTROL, False))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and session.marker in _window_title(session.hwnd):
            with contextlib.suppress(Exception):
                _invoke_button(session.hwnd, _is_dont_save)
            time.sleep(0.25)
    session.extra["tab_kept_by_notepad"] = session.marker in _window_title(session.hwnd)
    _user32.PostMessageW(wintypes.HWND(session.hwnd), _WM_CLOSE, 0, 0)
    left = _wait_gone({session.pid}, 15)
    session.extra["left_open"] = bool(left)
    with contextlib.suppress(OSError):
        session.extra["file"].unlink()


def _is_dont_save(name: str) -> bool:
    plain = name.replace("’", "'").casefold()
    return plain.startswith(("don't save", "do not save", "dont save"))


# WordPad (removed from Windows 11 24H2; tested where it still exists) ------ #


def _open_wordpad(path: str, work: Path, marker: str) -> Session:
    document = work / f"{marker}.rtf"
    document.write_text(r"{\rtf1\ansi }", encoding="ascii")
    before = _pids_named("wordpad.exe")
    subprocess.Popen([path, str(document)])  # noqa: S603
    hwnd, pid = _wait_for_window("wordpad.exe", before, marker)
    return Session(hwnd, pid, marker, _file_version(pid), {"file": document})


def _close_wordpad(session: Session) -> None:
    _user32.PostMessageW(wintypes.HWND(session.hwnd), _WM_CLOSE, 0, 0)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with contextlib.suppress(Exception):
            front = int(_user32.GetForegroundWindow() or 0)
            if _invoke_button(session.hwnd, _is_dont_save) or (
                front and _window_pid(front) == session.pid and _invoke_button(front, _is_dont_save)
            ):
                break
        time.sleep(0.25)
    session.extra["left_open"] = bool(_wait_gone({session.pid}, 15))
    with contextlib.suppress(OSError):
        session.extra["file"].unlink()


# Word and Outlook, through their own automation, each in a new instance ---- #


def _open_word(path: str, work: Path, marker: str) -> Session:
    del path, work
    import win32com.client

    before = _pids_named("winword.exe")
    app = win32com.client.DispatchEx("Word.Application")  # always a new instance
    app.Visible = True
    doc = app.Documents.Add()
    window = doc.ActiveWindow
    window.Caption = marker
    hwnd = int(_user32.GetAncestor(wintypes.HWND(int(window.Hwnd)), _GA_ROOT) or 0)
    pid = _window_pid(hwnd)
    session = Session(hwnd, pid, marker, _file_version(pid), {"app": app, "doc": doc})
    if pid in before:
        _close_word(session)
        raise _Skip("Word did not start a new instance")
    with contextlib.suppress(Exception):
        window.Activate()
    return session


def _close_word(session: Session) -> None:
    with contextlib.suppress(Exception):
        session.extra["doc"].Close(SaveChanges=0)  # wdDoNotSaveChanges
    with contextlib.suppress(Exception):
        session.extra["app"].Quit(SaveChanges=0)
    session.extra.pop("doc", None)
    session.extra.pop("app", None)
    session.extra["left_open"] = bool(_wait_gone({session.pid}, 20))


def _open_outlook(path: str, work: Path, marker: str) -> Session:
    del path, work
    if os.environ.get("QUILL_TRANSCRIBE_TARGETS_OUTLOOK") != "1":
        raise _Skip(
            "Outlook opens your mailbox: set QUILL_TRANSCRIBE_TARGETS_OUTLOOK=1 to include it"
        )
    if _pids_named("outlook.exe"):
        raise _Skip("Outlook is already running; the harness types only into a program it started")
    import win32com.client

    app = win32com.client.DispatchEx("Outlook.Application")
    mail = app.CreateItem(0)  # olMailItem; never addressed, never sent
    mail.Subject = marker
    mail.Display(False)
    before: set[int] = set()
    hwnd, pid = _wait_for_window("outlook.exe", before, marker)
    session = Session(hwnd, pid, marker, _file_version(pid), {"app": app, "mail": mail})
    automation, _ = _uia()
    root = automation.ElementFromHandle(wintypes.HWND(hwnd))
    body = root.FindFirst(
        4, automation.CreatePropertyCondition(_UIA_CONTROL_TYPE_PROP, _UIA_DOCUMENT)
    )
    if body is None:
        _close_outlook(session)
        raise _Skip("could not find the message body")
    body.SetFocus()
    return session


def _close_outlook(session: Session) -> None:
    with contextlib.suppress(Exception):
        session.extra["mail"].Close(1)  # olDiscard
    with contextlib.suppress(Exception):
        session.extra["app"].Quit()
    session.extra.pop("mail", None)
    session.extra.pop("app", None)
    session.extra["left_open"] = bool(_wait_gone({session.pid}, 30))


# Browsers and VS Code: a throwaway profile each ---------------------------- #


def _page(work: Path, marker: str) -> Path:
    page = work / f"{marker}.html"
    page.write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{marker}</title></head><body>"
        "<label for='t'>Dictation target</label>"
        "<textarea id='t' rows='20' cols='80' autofocus spellcheck='false'></textarea>"
        "<script>document.getElementById('t').focus()</script>"
        "</body></html>",
        encoding="utf-8",
    )
    return page


def _chromium_opener(image: str, *extra: str) -> Callable[[str, Path, str], Session]:
    def opener(path: str, work: Path, marker: str) -> Session:
        profile = work / f"profile-{marker}"
        profile.mkdir()
        page = _page(work, marker)
        before = _pids_named(image)
        subprocess.Popen(  # noqa: S603 - the installed browser, a local file
            [
                path,
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-sync",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-features=Translate",
                *extra,
                "--new-window",
                page.as_uri(),
            ]
        )
        hwnd, pid = _wait_for_window(image, before, marker)
        return Session(
            hwnd, pid, marker, _file_version(pid), {"token": str(profile), "image": image}
        )

    return opener


def _open_firefox(path: str, work: Path, marker: str) -> Session:
    profile = work / f"profile-{marker}"
    profile.mkdir()
    (profile / "user.js").write_text(
        "\n".join(
            f'user_pref("{name}", {value});'
            for name, value in (
                ("browser.shell.checkDefaultBrowser", "false"),
                ("browser.startup.homepage_override.mstone", '"ignore"'),
                ("browser.aboutwelcome.enabled", "false"),
                ("datareporting.policy.dataSubmissionEnabled", "false"),
                ("datareporting.policy.firstRunURL", '""'),
                ("toolkit.telemetry.reportingpolicy.firstRun", "false"),
                ("trailhead.firstrun.didSeeAboutWelcome", "true"),
                ("app.update.auto", "false"),
                ("browser.startup.page", "0"),
            )
        ),
        encoding="utf-8",
    )
    page = _page(work, marker)
    before = _pids_named("firefox.exe")
    subprocess.Popen(  # noqa: S603
        [path, "-no-remote", "-new-instance", "-profile", str(profile), page.as_uri()]
    )
    hwnd, pid = _wait_for_window("firefox.exe", before, marker)
    return Session(
        hwnd, pid, marker, _file_version(pid), {"token": str(profile), "image": "firefox.exe"}
    )


def _open_vscode(path: str, work: Path, marker: str) -> Session:
    profile = work / f"profile-{marker}"
    (profile / "User").mkdir(parents=True)
    (profile / "User" / "settings.json").write_text(
        json.dumps({
            # The editor's text, whole, to UI Automation: what a screen
            # reader user has on, and what lets this test read it back.
            "editor.accessibilitySupport": "on",
            "workbench.startupEditor": "none",
            "telemetry.telemetryLevel": "off",
            "update.mode": "none",
            "security.workspace.trust.enabled": False,
        }),
        encoding="utf-8",
    )
    document = work / f"{marker}.txt"
    document.write_text("", encoding="utf-8")
    before = _pids_named("code.exe")
    subprocess.Popen(  # noqa: S603
        [
            path,
            f"--user-data-dir={profile}",
            f"--extensions-dir={work / f'ext-{marker}'}",
            "--disable-extensions",
            "--skip-welcome",
            "--skip-release-notes",
            "--disable-workspace-trust",
            "--new-window",
            str(document),
        ]
    )
    hwnd, pid = _wait_for_window("code.exe", before, marker)
    time.sleep(2.0)  # the editor takes the focus a moment after the window shows
    return Session(
        hwnd, pid, marker, _file_version(pid), {"token": str(profile), "image": "code.exe"}
    )


def _close_profiled(session: Session) -> None:
    # A throwaway profile: nothing in it is kept, so nothing is saved anywhere
    # the person would see. Close politely, then end only this profile's processes.
    _user32.PostMessageW(wintypes.HWND(session.hwnd), _WM_CLOSE, 0, 0)
    family = _family(session.pid)
    if _wait_gone(family, 10):
        _end_processes_naming(session.extra["token"], session.extra["image"])
    session.extra["left_open"] = bool(_wait_gone(family, 10))


TARGETS: tuple[Target, ...] = (
    Target(
        "notepad",
        "Notepad",
        lambda: _first_file(r"%SystemRoot%\System32\notepad.exe"),
        _open_notepad,
        _close_notepad,
    ),
    Target(
        "wordpad",
        "WordPad",
        lambda: _first_file(r"%ProgramFiles%\Windows NT\Accessories\wordpad.exe"),
        _open_wordpad,
        _close_wordpad,
        "WordPad was removed from Windows 11 in version 24H2.",
    ),
    Target("word", "Microsoft Word", lambda: _app_path("winword.exe"), _open_word, _close_word),
    Target(
        "outlook",
        "Microsoft Outlook",
        lambda: _app_path("outlook.exe"),
        _open_outlook,
        _close_outlook,
    ),
    Target(
        "edge",
        "Microsoft Edge",
        lambda: _app_path("msedge.exe"),
        _chromium_opener("msedge.exe", "--inprivate"),
        _close_profiled,
    ),
    Target(
        "chrome",
        "Google Chrome",
        lambda: _app_path("chrome.exe"),
        _chromium_opener("chrome.exe"),
        _close_profiled,
    ),
    Target(
        "firefox",
        "Mozilla Firefox",
        lambda: (
            _app_path("firefox.exe") or _first_file(r"%ProgramFiles%\Mozilla Firefox\firefox.exe")
        ),
        _open_firefox,
        _close_profiled,
    ),
    Target(
        "vscode",
        "Visual Studio Code",
        lambda: _first_file(
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%ProgramFiles%\Microsoft VS Code\Code.exe",
        ),
        _open_vscode,
        _close_profiled,
    ),
)

# --------------------------------------------------------------------------- #
# Typing through the shared port
# --------------------------------------------------------------------------- #


class _GuardTripped(Exception):  # noqa: N818
    pass


def _external_document(session: Session) -> Any:
    """The shared ExternalDocument, its typing fenced to this run's window."""
    from quill.ui import windows_dictation_external as external

    def typing(text: str, hush: bool = False) -> bool:
        reason = session.guard()
        if reason:
            raise _GuardTripped(reason)
        return bool(external._type(text, hush))

    class _Prefs:
        phrase_feedback = "sound"  # QUILL Transcribe's default: a tone, no read-back
        continuous = False

    return external.ExternalDocument(
        problem=session.guard,
        type_text=typing,
        backspace=lambda count: False,  # this harness never takes anything back
        hush=external.hush_unless_spoken(lambda: _Prefs()),
    )


def _read_field(session: Session) -> tuple[str, str]:
    element, pid = _focused()
    if element is None or pid not in _family(session.pid):
        raise _GuardTripped("the focus is outside the program this run opened")
    return _read_text(element)


def _dictate(session: Session) -> dict[str, Any]:
    """Type every phrase; count the ones that arrived exactly."""
    document = _external_document(session)
    reason = document.unavailable_reason(writing=True)
    if reason:
        raise _Skip(f"not typing: {reason}")
    start, verified_by = _read_field(session)
    if not verified_by:
        raise _Skip("UI Automation cannot read this field, so nothing would be verified")
    if normalize(start):
        raise _Skip("the field was not empty, so it is not this run's document")
    exact = 0
    sent = 0
    mismatches: list[dict[str, str]] = []
    incomplete = ""
    for phrase in PHRASES:
        try:
            before = normalize(_read_field(session)[0])
            try:
                document.insert(phrase)
                session.own_tick = _tick() + 250  # our own keys may land this late
            except OSError:
                sent += 1
                mismatches.append({"sent": phrase, "arrived": "(Windows did not take all of it)"})
                continue
            sent += 1
            tripped = session.guard()
            if tripped:
                raise _GuardTripped(tripped)
            wanted = normalize(before + phrase)
            now = before
            deadline = time.monotonic() + _SETTLE_S
            while time.monotonic() < deadline:
                now = normalize(_read_field(session)[0])
                if now == wanted:
                    break
                time.sleep(0.1)
            tripped = session.guard()  # somebody else's keys would spoil this phrase's count
            if tripped:
                raise _GuardTripped(tripped)
        except _GuardTripped as stop:
            incomplete = str(stop)
            break
        if now == wanted:
            exact += 1
        else:
            arrived = now[len(before) :] if now.startswith(before) else now
            mismatches.append({"sent": phrase, "arrived": arrived[-200:]})
    return {
        "phrases_sent": sent,
        "phrases_exact": exact,
        "verified_by": verified_by,
        "mismatches": mismatches,
        "incomplete": incomplete,
    }


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #

_RUN: dict[str, dict[str, Any]] = {}


def _today() -> str:
    return _dt.date.today().isoformat()


def merge_results(previous: dict[str, Any], run: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """This run's rows over the previous file's; a program not run keeps its row.

    A program skipped for safety (already running, not opted in) keeps a
    previous *tested* row rather than losing it to a skip.
    """
    rows = {row["key"]: row for row in previous.get("programs", [])}
    for key, row in run.items():
        old = rows.get(key)
        if row["status"] == "skipped" and old and old.get("status") == "tested":
            continue
        rows[key] = row
    ordered = [rows[t.key] for t in TARGETS if t.key in rows]
    for target in TARGETS:
        if target.key not in rows:
            ordered.append({
                "key": target.key,
                "program": target.program,
                "status": "untested",
                "reason": "not run yet",
            })
    return {"schema": 1, "phrases": list(PHRASES), "programs": ordered}


@pytest.fixture(scope="module", autouse=True)
def _write_results() -> Iterator[None]:
    yield
    if not _RUN:
        return
    previous: dict[str, Any] = {}
    if RESULTS_PATH.is_file():
        with contextlib.suppress(ValueError):
            previous = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    merged = merge_results(previous, _RUN)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8", newline="\n")


@pytest.mark.parametrize("target", TARGETS, ids=[t.key for t in TARGETS])
def test_dictating_into(target: Target, tmp_path: Path) -> None:
    row: dict[str, Any] = {"key": target.key, "program": target.program, "date": _today()}
    path = target.find()
    if not path:
        row.update(status="untested", reason=target.not_installed_note or "not installed")
        _RUN[target.key] = row
        pytest.skip(f"{target.program} is not installed")
    if os.environ.get("QUILL_TRANSCRIBE_TARGETS_SURVEY") == "1":
        row.update(
            status="skipped",
            version=_path_version(path),
            reason="installed on the test computer, not run yet",
        )
        _RUN[target.key] = row
        pytest.skip(f"{target.program}: survey only")
    marker = f"QUILL-TT-{secrets.token_hex(4)}"
    session: Session | None = None
    try:
        idle = _idle_seconds()
        if idle < IDLE_S:
            raise _Skip(
                f"the computer is in use (a key or the mouse {idle:.0f} seconds ago); "
                f"it needs {IDLE_S:.0f} seconds without input"
            )
        session = target.open(path, tmp_path, marker)
        row["version"] = session.version
        if not _bring_to_front(session.hwnd):
            raise _Skip("could not bring the window this run opened to the front")
        time.sleep(0.5)
        session.own_tick = _tick()
        reason = session.guard()
        if reason:
            raise _Skip(reason)
        row.update(status="tested", **_dictate(session))
    except _Skip as skip:
        row.update(status="skipped", reason=str(skip))
    finally:
        if session is not None:
            target.close(session)
            if session.extra.get("left_open"):
                row["left_open"] = True
            if session.extra.get("tab_kept_by_notepad"):
                row["tab_kept_by_notepad"] = True
    _RUN[target.key] = row
    if row["status"] == "skipped":
        pytest.skip(f"{target.program}: {row['reason']}")
    assert not row.get("incomplete"), f"typing stopped early: {row['incomplete']}"
    assert not row.get("left_open"), f"{target.program} did not close"


def test_the_matrix_meets_the_95_percent_bar() -> None:
    """dict.md D-4: at least 95 percent of phrases arrive exactly, across the matrix."""
    tested = [row for row in _RUN.values() if row.get("status") == "tested"]
    if not tested:
        pytest.skip("no program was tested in this run")
    sent = sum(row["phrases_sent"] for row in tested)
    exact = sum(row["phrases_exact"] for row in tested)
    assert sent and exact / sent >= 0.95, {r["key"]: r.get("mismatches") for r in tested}
