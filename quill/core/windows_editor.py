"""QUILL and QUILL Lite as Windows text editors: what they register, and how Notepad is replaced.

Both editors have the same two Preferences controls -- Make <app> My Text Editor
and Open <app> instead of Notepad -- and both installers write the same keys. What
differs between them is data, so it is data: an :class:`EditorProfile` per
app, and every function here takes the profile it is working for. The family
rule is that QUILL Lite is never ahead of QUILL, and the cheapest way to keep a
capability from forking is to have only one of it.

Two different things live here, and they are kept apart on purpose.

**Registering** is polite. It tells Windows that an editor *can* open text,
Markdown, rich text and the rest: a ProgID with an open command, an entry in
each type's ``OpenWithProgids`` list, an ``Applications\\<exe>`` key, and the
``Capabilities`` + ``RegisteredApplications`` pair that puts the app in
Settings > Apps > Default apps. None of it takes anything over. Windows has not
let a program make itself the default since Windows 8 -- the choice is the
user's, made in Settings, and it is stored under a ``UserChoice`` key with a
hash only Windows can write. Nothing here ever touches ``UserChoice``.

The installers write the same keys under HKA (``quilllite.iss``, and
``installer/quill.iss`` through ``scripts/build_windows_distribution.py``); the
command writes them for the current user, pointing at whichever copy is
running, so a portable copy can register itself too.

**Replacing Notepad** is not polite, and is opt-in for that reason. Windows has
one supported hook that runs another program whenever ``notepad.exe`` starts:
the ``Debugger`` value under Image File Execution Options. It is machine-wide
(HKLM, every user), it needs administrator approval, and Windows passes the
original command line -- Notepad's own path first -- after it. Windows 11 adds
a twist: its ``notepad.exe`` key has ``UseFilter`` set and one subkey per
Notepad path, and when a subkey's ``FilterFullPath`` matches, *that* subkey's
values are used instead of the parent's. So the value is written to the parent
(for Windows 10) and to every matching subkey (for Windows 11), and only ever
removed where it is ours.

There is one hook, so only one program can own it. :func:`owner_of` names the
family editor a Debugger value belongs to, so either editor can say "QUILL Lite
opens in place of Notepad now" rather than reading out a command line.

wx-free and registry-free: every function here builds or reads data, and the
registry itself is reached through the small reader and writer protocols, so
the tests never touch a real hive.

**Not only editors.** Registering is the same polite act for any app that
opens files, so the profile is the general one (:data:`AppProfile` is its
other name): Quill Radio registers as a media player from the same plan
(:mod:`quill.core.windows_media`), with a :attr:`EditorProfile.role` of "Media
Player" and two right-click verbs of its own. Replacing Notepad stays an
editor's business -- :data:`FAMILY` names the only apps that may own that hook.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from quill.core.app_command import split_command, to_command_line

__all__ = [
    "FAMILY",
    "IFEO_KEY",
    "NOTEPAD_FLAG",
    "QUILL",
    "QUILL_LITE",
    "AppProfile",
    "ContextVerb",
    "EditorProfile",
    "NotepadState",
    "RegKey",
    "RegistryReader",
    "RegistryWriter",
    "RegValue",
    "default_apps_uri",
    "editor_argv",
    "elevated_parameters",
    "is_ours",
    "machine_registered",
    "notepad_debugger_value",
    "notepad_keys",
    "open_command",
    "owner_of",
    "read_notepad_state",
    "reg_add_arguments",
    "reg_delete_arguments",
    "registration_plan",
    "safe_for_cmd",
    "translate_notepad_argv",
    "turn_off_commands",
    "turn_on_commands",
    "verb_command",
    "write_plan",
]


@dataclass(frozen=True, slots=True)
class ContextVerb:
    """A right-click command on every supported type, whichever app owns it.

    Written under ``SystemFileAssociations\\<ext>\\shell\\<key>``, which Windows
    shows beside the default app's own verbs rather than instead of them -- so
    it is there without taking anything over. *arguments* come between the
    app and the file.
    """

    key: str
    label: str
    arguments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EditorProfile:
    """Everything that differs between two apps' registrations.

    Named for the editors it was written for; :data:`AppProfile` is the same
    class under the name that fits Quill Radio.
    """

    #: The name Windows shows: Default apps, Open With, the RegisteredApplications value.
    app_name: str
    #: The one ProgID every supported type points at.
    progid: str
    #: The executable Windows lists under ``Applications``.
    exe_name: str
    #: ``Software\\<App>\\Capabilities``, under HKCU or HKLM.
    capabilities_key: str
    #: The types the app really opens.
    extensions: tuple[str, ...]
    description: str
    #: The module that starts the app (``python -m <module>``).
    module: str
    #: A native launcher next to the runtime, when the app has one.
    launcher_name: str | None = None
    #: An icon file beside the executable; otherwise the executable's own icon.
    icon_name: str | None = None
    #: Executable stems that mean this app when they start a Debugger value.
    exe_stems: tuple[str, ...] = ()
    #: The same types in a sentence, for the dialog that explains registering.
    types_phrase: str = ""
    #: What the app is to Windows, as the command names it: Make <app> My <role>.
    role: str = "Text Editor"
    #: The type the explanation walks through choosing first.
    example_type: str = ".txt"
    #: The second word of the ProgID's name: "QUILL Document".
    document_kind: str = "Document"
    #: Right-click verbs on every supported type (none for the editors).
    verbs: tuple[ContextVerb, ...] = ()

    @property
    def document_name(self) -> str:
        return f"{self.app_name} {self.document_kind}"


#: The general name: a profile is for any app that registers to open files.
AppProfile = EditorProfile

#: The types QUILL Lite really opens (``quill.core.lite.filetypes``): plain
#: text and its usual spellings, Markdown, rich text, HTML, and CSV, which it
#: opens as the plain text it is.
_LITE_EXTENSIONS: tuple[str, ...] = (
    ".txt",
    ".text",
    ".log",
    ".md",
    ".markdown",
    ".rtf",
    ".html",
    ".htm",
    ".csv",
)

#: QUILL opens everything QUILL Lite does, and the formats ``quill/io`` reads
#: that its installer already offered in Open With before 2026-10-03:
#: reStructuredText, JSON, Word, OpenDocument and EPUB.
_QUILL_EXTENSIONS: tuple[str, ...] = (
    *_LITE_EXTENSIONS,
    ".rst",
    ".json",
    ".docx",
    ".odt",
    ".epub",
)

QUILL_LITE = EditorProfile(
    app_name="QUILL Lite",
    progid="QuillLite.Document",
    exe_name="QuillLite.exe",
    capabilities_key=r"Software\QuillLite\Capabilities",
    extensions=_LITE_EXTENSIONS,
    description=(
        "An accessible text editor for plain text, Markdown, rich text and HTML, "
        "built for screen readers."
    ),
    module="quill.apps.lite",
    launcher_name="QuillLite.exe",
    icon_name="quill-lite.ico",
    exe_stems=("quilllite",),
    types_phrase="text, Markdown, rich text, HTML and CSV files",
)

#: QUILL's installed ``quill.exe`` is a stamped ``pythonw.exe``: bare, it starts
#: QUILL, but anything after it would be read as Python's own options, so every
#: command QUILL stores says ``-m quill`` (see :func:`editor_argv`).
QUILL = EditorProfile(
    app_name="QUILL",
    progid="Quill.Document",
    exe_name="quill.exe",
    capabilities_key=r"Software\QUILL\Capabilities",
    extensions=_QUILL_EXTENSIONS,
    description=(
        "An accessible writing environment for plain text, Markdown, rich text, "
        "HTML, Word and EPUB, built for screen readers."
    ),
    module="quill",
    exe_stems=("quill",),
    types_phrase=("text, Markdown, rich text, HTML, Word, OpenDocument, EPUB, JSON and CSV files"),
)

#: Every editor that can own the Notepad hook, in the order they are named.
FAMILY: tuple[EditorProfile, ...] = (QUILL, QUILL_LITE)

_REGISTERED_APPLICATIONS = r"Software\RegisteredApplications"
_CLASSES = r"Software\Classes"

IFEO_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\notepad.exe"
NOTEPAD_FLAG = "--notepad"

#: Notepad's own switches. /P prints and /PT prints to a named printer; the
#: editor opens the file instead, and Ctrl+P prints it.
_NOTEPAD_SWITCHES = frozenset({"/a", "/w", "/p", "/pt", "/.setup"})

#: Characters cmd.exe would act on even inside the elevated command line.
_CMD_SPECIAL = frozenset('&|<>^%!"\r\n')


# ---------------------------------------------------------------------- #
# Registering an editor as a text editor
# ---------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RegValue:
    """One value. *kind* is ``"sz"`` (a string) or ``"none"`` (an empty marker)."""

    name: str
    data: str = ""
    kind: str = "sz"


@dataclass(frozen=True, slots=True)
class RegKey:
    """A key under HKEY_CURRENT_USER and the values to set in it."""

    path: str
    values: tuple[RegValue, ...] = field(default_factory=tuple)


class RegistryWriter(Protocol):
    """Sets one value, creating the key. The only way this module writes."""

    def set_value(self, path: str, name: str, data: str, kind: str) -> None: ...


class RegistryReader(Protocol):
    """Reads HKEY_LOCAL_MACHINE. Never raises; a missing key or value is None/[]."""

    def value(self, path: str, name: str) -> object | None: ...

    def subkeys(self, path: str) -> list[str]: ...


def editor_argv(profile: EditorProfile, base: Sequence[str]) -> list[str]:
    """The argv that starts *profile*'s app, from ``app_argv``'s answer *base*.

    A genuine app exe started bare is the one case that needs help: QUILL's
    ``quill.exe`` is a stamped interpreter, so ``quill.exe "%1"`` would hand
    the file to Python. ``-m <module>`` makes it unambiguous, and is what
    QUILL's installer has always written.
    """
    argv = list(base)
    if len(argv) == 1 and profile.launcher_name is None:
        argv += ["-m", profile.module]
    return argv


def open_command(launcher_argv: Sequence[str]) -> str:
    """``"<exe>" "%1"`` -- the launcher quoted, the file quoted."""
    return f'{to_command_line(launcher_argv)} "%1"'


def verb_command(launcher_argv: Sequence[str], verb: ContextVerb) -> str:
    """``"<exe>" <verb arguments> "%1"``, the command one right-click verb runs."""
    return f'{to_command_line([*launcher_argv, *verb.arguments])} "%1"'


def registration_plan(
    profile: EditorProfile, launcher_argv: Sequence[str], icon: str
) -> list[RegKey]:
    """Every key the per-user registration writes, in the order it writes them.

    *launcher_argv* starts the app (``quill.core.app_command.app_argv``);
    *icon* is a ``DefaultIcon`` string such as ``C:\\...\\quill-lite.ico``.
    """
    command = open_command(launcher_argv)
    progid = profile.progid
    application = rf"{_CLASSES}\Applications\{profile.exe_name}"
    plan = [
        RegKey(
            rf"{_CLASSES}\{progid}",
            (
                RegValue("", profile.document_name),
                RegValue("FriendlyTypeName", profile.document_name),
            ),
        ),
        RegKey(rf"{_CLASSES}\{progid}\DefaultIcon", (RegValue("", icon),)),
        RegKey(rf"{_CLASSES}\{progid}\shell\open\command", (RegValue("", command),)),
        RegKey(application, (RegValue("FriendlyAppName", profile.app_name),)),
        RegKey(rf"{application}\DefaultIcon", (RegValue("", icon),)),
        RegKey(rf"{application}\shell\open\command", (RegValue("", command),)),
        RegKey(
            rf"{application}\SupportedTypes",
            tuple(RegValue(ext) for ext in profile.extensions),
        ),
    ]
    plan += [
        RegKey(rf"{_CLASSES}\{ext}\OpenWithProgids", (RegValue(progid),))
        for ext in profile.extensions
    ]
    plan += [
        RegKey(
            profile.capabilities_key,
            (
                RegValue("ApplicationName", profile.app_name),
                RegValue("ApplicationDescription", profile.description),
                RegValue("ApplicationIcon", icon),
            ),
        ),
        RegKey(
            rf"{profile.capabilities_key}\FileAssociations",
            tuple(RegValue(ext, progid) for ext in profile.extensions),
        ),
        RegKey(
            _REGISTERED_APPLICATIONS,
            (RegValue(profile.app_name, profile.capabilities_key),),
        ),
    ]
    for verb in profile.verbs:
        for ext in profile.extensions:
            base = rf"{_CLASSES}\SystemFileAssociations\{ext}\shell\{verb.key}"
            plan.append(RegKey(base, (RegValue("", verb.label),)))
            plan.append(
                RegKey(rf"{base}\command", (RegValue("", verb_command(launcher_argv, verb)),))
            )
    return plan


def write_plan(plan: Sequence[RegKey], writer: RegistryWriter) -> int:
    """Write every value in *plan*; the number of values written."""
    count = 0
    for key in plan:
        for value in key.values:
            writer.set_value(key.path, value.name, value.data, value.kind)
            count += 1
    return count


def machine_registered(
    profile: EditorProfile, reader: RegistryReader, launcher_argv: Sequence[str]
) -> bool:
    """Whether an administrator install already registered *this* copy for everyone.

    Then the per-user keys would only be a second copy that no uninstaller
    removes, so the command opens Settings and writes nothing.
    """
    stored = reader.value(rf"{_CLASSES}\{profile.progid}\shell\open\command", "")
    listed = reader.value(_REGISTERED_APPLICATIONS, profile.app_name)
    return (
        isinstance(stored, str)
        and stored.strip().lower() == open_command(launcher_argv).lower()
        and listed == profile.capabilities_key
    )


def default_apps_uri(profile: EditorProfile, build: int, *, machine: bool = False) -> str:
    """The Settings page for the app's own defaults, where Windows has one.

    Windows 11 (build 22000 and later) opens straight to one app's list of types
    by its RegisteredApplications name -- ``registeredAppMachine`` when an
    administrator install registered it, ``registeredAppUser`` otherwise.
    Windows 10 only has the general page.
    """
    if build < 22000:
        return "ms-settings:defaultapps"
    scope = "registeredAppMachine" if machine else "registeredAppUser"
    return f"ms-settings:defaultapps?{scope}=" + profile.app_name.replace(" ", "%20")


# ---------------------------------------------------------------------- #
# Opening an editor instead of Notepad
# ---------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class NotepadState:
    """What the Notepad hook says now.

    *ours* lists the keys whose Debugger is this app's; *other* is a Debugger
    some other program set (Notepad++, say, or the other family editor), which
    is never overwritten without saying so and never removed. *other_owner* is
    that program's name when it is one of the family, so it can be said as a
    name rather than read out as a command line.
    """

    ours: tuple[str, ...] = ()
    other: str | None = None
    other_owner: str | None = None

    @property
    def on(self) -> bool:
        return bool(self.ours)


def notepad_debugger_value(launcher_argv: Sequence[str]) -> str:
    """``"<launcher>" --notepad``, the Debugger value Windows runs."""
    return to_command_line([*launcher_argv, NOTEPAD_FLAG])


def is_ours(profile: EditorProfile, value: object) -> bool:
    """Whether a Debugger value is one *profile*'s app wrote.

    By the executable that starts it, or the module after ``-m`` -- never by a
    substring, because "quill" is in both editors' names and in QUILL Lite's
    install folder.
    """
    if not isinstance(value, str) or not value.strip():
        return False
    executable, arguments = split_command(value)
    words = arguments.split()
    if NOTEPAD_FLAG not in [word.strip('"').lower() for word in words]:
        return False
    if Path(executable).stem.lower() in profile.exe_stems:
        return True
    for index, word in enumerate(words[:-1]):
        if word == "-m" and words[index + 1].strip('"') == profile.module:
            return True
    return False


def owner_of(value: object) -> str | None:
    """The family editor a Debugger value belongs to, by name; None for anything else."""
    for profile in FAMILY:
        if is_ours(profile, value):
            return profile.app_name
    return None


def notepad_keys(reader: RegistryReader) -> list[str]:
    """The parent key, then every Windows 11 filter subkey for a Notepad path."""
    keys = [IFEO_KEY]
    for name in reader.subkeys(IFEO_KEY):
        path = rf"{IFEO_KEY}\{name}"
        target = reader.value(path, "FilterFullPath")
        if isinstance(target, str) and target.lower().replace("/", "\\").endswith("\\notepad.exe"):
            keys.append(path)
    return keys


def read_notepad_state(profile: EditorProfile, reader: RegistryReader) -> NotepadState:
    ours: list[str] = []
    other: str | None = None
    for key in notepad_keys(reader):
        value = reader.value(key, "Debugger")
        if is_ours(profile, value):
            ours.append(key)
        elif isinstance(value, str) and value.strip() and other is None:
            other = value
    return NotepadState(tuple(ours), other, owner_of(other))


def reg_add_arguments(key: str, debugger: str) -> list[str]:
    """``reg.exe`` arguments that set *key*'s Debugger, in the 64-bit view."""
    return [
        "add",
        f"HKLM\\{key}",
        "/v",
        "Debugger",
        "/t",
        "REG_SZ",
        "/d",
        debugger,
        "/f",
        "/reg:64",
    ]


def reg_delete_arguments(key: str) -> list[str]:
    """``reg.exe`` arguments that remove *key*'s Debugger value, and nothing else."""
    return ["delete", f"HKLM\\{key}", "/v", "Debugger", "/f", "/reg:64"]


def turn_on_commands(reader: RegistryReader, launcher_argv: Sequence[str]) -> list[list[str]]:
    debugger = notepad_debugger_value(launcher_argv)
    return [reg_add_arguments(key, debugger) for key in notepad_keys(reader)]


def turn_off_commands(profile: EditorProfile, reader: RegistryReader) -> list[list[str]]:
    """Removes only *profile*'s own values, so another program's is left alone."""
    return [reg_delete_arguments(key) for key in read_notepad_state(profile, reader).ours]


def safe_for_cmd(commands: Sequence[Sequence[str]]) -> bool:
    """Whether every argument can pass through ``cmd.exe /c`` unchanged.

    The embedded quotes in the Debugger value are the one exception, and
    :func:`elevated_parameters` escapes those itself. A launcher path with
    ``&`` or ``%`` in it is refused rather than guessed at.
    """
    for arguments in commands:
        for argument in arguments:
            bare = argument.replace('"', "")
            if any(char in _CMD_SPECIAL for char in bare):
                return False
    return True


def elevated_parameters(commands: Sequence[Sequence[str]], reg_exe: str) -> str:
    """``cmd.exe`` parameters that run every ``reg.exe`` command under one prompt.

    One administrator prompt for the whole change, rather than one per key.
    ``&`` rather than ``&&``: each key is independent, and the state is read
    back afterwards either way.
    """
    lines = [f'"{reg_exe}" {subprocess.list2cmdline(list(arguments))}' for arguments in commands]
    # /s with one outer pair of quotes: cmd strips exactly those two and runs
    # the rest as written, whatever quotes the commands themselves carry.
    return '/d /s /c "' + " & ".join(lines) + '"'


def translate_notepad_argv(
    argv: list[str],
    *,
    exists: Callable[[str], bool] = os.path.exists,
) -> list[str]:
    """Turn a launch Windows made *as* Notepad into the editor's own arguments.

    Both editors call this first thing. Anything not starting with
    ``--notepad`` is returned unchanged. Otherwise Windows has passed Notepad's
    path and then Notepad's own command line, which names **one** file, often
    unquoted -- Explorer's own ``.txt`` command is ``notepad.exe %1`` -- so
    ``C:\\My Notes\\a.txt`` arrives as two words. The words are joined back into
    one path unless they are each a file that exists. Notepad's switches (/A,
    /W, /P, /PT) are dropped; a file named with /P is opened rather than
    printed.

    No file means a blank plain text document (``--plain``, which both editors
    accept), which is what Notepad gives. Paths come back absolute, so none can
    be mistaken for a switch.
    """
    if not argv or argv[0] != NOTEPAD_FLAG:
        return argv
    rest = argv[2:]  # the flag, then the path Windows started as Notepad
    while rest and rest[0].lower() in _NOTEPAD_SWITCHES:
        switch = rest.pop(0).lower()
        if switch == "/pt":
            rest = rest[:1]  # the file; the printer, driver and port follow it
    words = [word.strip('"') for word in rest if word.strip('"')]
    if not words:
        return ["--plain"]
    joined = " ".join(words)
    if len(words) > 1 and not exists(joined) and all(exists(word) for word in words):
        chosen = words
    else:
        chosen = [joined]
    return [str(Path(name).absolute()) for name in chosen]
