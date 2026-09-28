"""Which apps the shared QuillVille Runtime can start, and which are installed.

The runtime is not an app: every QuillVille app is ``QuillVilleRuntime.exe -m
<module>``, started by the app's own launcher (``QuillRadio.exe`` and friends).
But Windows does not always go through the launcher. Pin a running app to the
taskbar and Windows pins the *process* it sees -- the runtime -- with no
arguments at all. Press that pin and the runtime starts with no app to run.

Until 3.0.1 that crashed; 3.0.1 explained itself in a message box instead, and
a listener who had pinned Quill Radio the way they always had heard "this is not
an app" in place of their radio (reported 2026-09-27). The runtime now answers
the question instead of reporting it: it knows which apps are installed on it
(:mod:`quill.core.runtime_refs`, written by each app's installer), so with one
app it starts that app, and with several it asks which.

The table here is the runtime's own copy of the app list. It must agree with
``scripts/build_native_launcher.py``'s ``PRODUCTS`` -- the same ids the
installers register under (``#define AppRefId``) -- and
``tests/unit/core/test_runtime_apps.py`` fails if it drifts.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "RUNTIME_APPS",
    "RuntimeApp",
    "app_for_module",
    "claim_taskbar_identity",
    "installed_apps",
]


@dataclass(frozen=True, slots=True)
class RuntimeApp:
    """One app that runs on the shared runtime."""

    #: The id its installer registers in runtime_refs (``#define AppRefId``).
    ref_id: str
    #: What ``-m`` starts.
    module: str
    #: What a person calls it.
    display: str
    #: The AppUserModelID its launcher and its shortcuts carry.
    app_user_model_id: str
    #: Whether its installer's shortcuts carry :attr:`app_user_model_id`
    #: (Inno ``AppUserModelID:`` on its [Icons] entries). Only then may the
    #: running app claim that id: Windows then pins the *shortcut*, which goes
    #: through the app's launcher, instead of the bare runtime. Claiming it
    #: without the shortcut would split the app's taskbar button in two.
    shortcuts_carry_id: bool = False

    @property
    def launcher_exe(self) -> str:
        """The native launcher's file name: ``QuillRadio.exe``.

        The launcher is named after the app's AppUserModelID
        (``scripts/build_native_launcher.py``: ``CommunityAccess.<name>``).
        """
        return self.app_user_model_id.rsplit(".", 1)[-1] + ".exe"


#: Every app the shared runtime can start, in the order a chooser lists them.
RUNTIME_APPS: tuple[RuntimeApp, ...] = (
    RuntimeApp("radio", "quill.apps.radio", "Quill Radio", "CommunityAccess.QuillRadio", True),
    RuntimeApp("quilllite", "quill.apps.lite", "QUILL Lite", "CommunityAccess.QuillLite"),
    RuntimeApp("weather", "quill.apps.weather", "Quill Weather", "CommunityAccess.QuillWeather"),
    RuntimeApp("cast", "quill.apps.podcasts", "QUILL Cast", "CommunityAccess.QuillCast"),
    RuntimeApp(
        "converter", "quill.apps.converter", "Quill Converter", "CommunityAccess.QuillConverter"
    ),
    RuntimeApp(
        "studio", "quill.apps.studio", "QUILL Audio Studio", "CommunityAccess.QuillAudioStudio"
    ),
    RuntimeApp("inkwell", "quill.apps.inkwell", "Quill Inkwell", "CommunityAccess.QuillInkwell"),
    RuntimeApp("beacon", "quill.apps.beacon", "Quill Beacon", "CommunityAccess.QuillBeacon"),
    RuntimeApp("social", "quill_social", "QUILL Social", "CommunityAccess.QuillSocial"),
)


def app_for_module(module: str) -> RuntimeApp | None:
    """The app *module* starts, or ``None`` for anything else."""
    return next((app for app in RUNTIME_APPS if app.module == module), None)


def installed_apps(data_dir: Path) -> list[RuntimeApp]:
    """The known apps registered on any runtime version, in chooser order.

    Read from ``runtime.state.json`` (:mod:`quill.core.runtime_refs`). An id this
    runtime does not know -- an app newer than the runtime -- is left out rather
    than guessed at, and an unreadable file is simply no apps: the caller then
    says what it said before, which is never worse than a wrong app.
    """
    from quill.core import runtime_refs

    try:
        registered = {app for apps in runtime_refs.all_refs(data_dir).values() for app in apps}
    except Exception:  # noqa: BLE001 - no answer is "no apps", never a crash
        return []
    return [app for app in RUNTIME_APPS if app.ref_id in registered]


def claim_taskbar_identity(module: str) -> bool:
    """Give this process the app's AppUserModelID, where its shortcuts carry it.

    What makes a taskbar pin of the running app a pin of its *Start menu
    shortcut* -- through ``QuillRadio.exe`` -- rather than of the runtime with no
    arguments. Windows only; best effort; True when the id was set.
    """
    import sys

    app = app_for_module(module)
    if app is None or not app.shortcuts_carry_id or sys.platform != "win32":
        return False
    try:
        import ctypes

        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            ctypes.c_wchar_p(app.app_user_model_id)
        )
    except Exception:  # noqa: BLE001 - grouping is cosmetic; never cost the launch
        return False
    return bool(result == 0)
