"""Installer-facing CLI for the shared Python runtime's reference counting.

The shared-runtime installers (Inno Setup) keep the *skip-if-present* decision
in plain Pascal (reading the version marker, :mod:`quill.core.runtime_marker`),
but the *reference counting* -- which app still needs which runtime version --
is tested Python in :mod:`quill.core.runtime_refs`. Rather than reimplement
that JSON bookkeeping in Pascal, the installer runs this CLI:

    # first run of an app: record that it needs this runtime
    <runtime>\\python.exe -m quill.core.runtime_cli register radio 3.13.1

    # uninstall: drop the app's ref; exit code 10 means "runtime now unreferenced,
    # the installer may delete the shared runtime folder"
    <runtime>\\python.exe -m quill.core.runtime_cli unregister radio 3.13.1

    # optional: print the shared data dir (where components/runtime state lives)
    <runtime>\\python.exe -m quill.core.runtime_cli data-dir

    # after staging an app: repair a "start with Windows" entry an older
    # build wrote as the bare runtime exe (which runs no app). The launcher
    # directory is this app's {app} folder, so the repaired entry names the
    # launcher rather than the runtime's versioned path.
    <runtime>\\python.exe -m quill.core.runtime_cli heal-launch-entries "C:\\...\\Quill Radio"

Exit codes: 0 = success (runtime still referenced), 10 = success and the named
runtime version is now unreferenced (safe to remove), 2 = usage error. It never
raises to the installer: any unexpected failure is reported as a non-zero exit
with a message, so a broken ref file can never wedge an install/uninstall.
"""

from __future__ import annotations

import sys

_UNREFERENCED_EXIT = 10


def _data_dir():  # type: ignore[no-untyped-def]
    from quill.core.paths import app_data_dir

    return app_data_dir()


#: The per-user "start with Windows" entries this repairs. Each healer rewrites
#: only an entry that already exists -- an app the listener never asked to start
#: with Windows stays absent -- so running them all is safe from any installer.
_STARTUP_HEALERS = (
    ("quill.platform.windows.radio_startup", "heal_launch_at_startup"),
    ("quill.platform.windows.weather_startup", "heal_launch_at_startup"),
    ("quill.platform.windows.inkwell_startup", "heal_launch_at_startup"),
)


def _heal_launch_entries(launcher_dir: str) -> int:
    """Repair stale autostart entries at install time. Always exits 0.

    The app repairs its own entry at launch (:mod:`quill.platform.windows.launch_heal`),
    but that needs a launch, and the entry this repairs is exactly the one that
    prevents launches: a listener whose "start with Windows" value was the bare
    ``QuillVilleRuntime.exe`` met PyInstaller's "Unhandled exception in script"
    box at every login instead of the app, with no reason to think that opening
    the app by hand would cure it (reported 2026-09-29). The installer knows
    the entry is stale the moment it stages a newer build, so it repairs it
    there, before the next login.

    *launcher_dir* is the app's install folder. ``app_command`` reads it from
    ``QUILL_LAUNCHER_DIR`` and prefers the native launcher inside it, whose path
    survives a runtime upgrade into a new versioned folder; without it the entry
    still gets the working ``"<runtime>" -m <module>`` form.

    Never fails the install: a locked-down registry, a missing module or a
    healer that raises costs the repair, not the install.
    """
    import importlib
    import os

    if launcher_dir.strip():
        os.environ["QUILL_LAUNCHER_DIR"] = launcher_dir.strip()
    repaired = 0
    for module_name, function_name in _STARTUP_HEALERS:
        try:
            module = importlib.import_module(module_name)
            if getattr(module, function_name)():
                repaired += 1
        except Exception as exc:  # noqa: BLE001 - never wedge an install
            print(f"heal-launch-entries: {module_name} skipped ({exc})")
    print(f"heal-launch-entries: repaired {repaired}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: runtime_cli "
            "<register|unregister|is-referenced|data-dir|heal-launch-entries> ..."
        )
        return 2
    command = args[0]
    try:
        from quill.core import runtime_refs

        if command == "data-dir":
            print(str(_data_dir()))
            return 0
        if command == "register":
            if len(args) < 3:
                print("usage: runtime_cli register <app_id> <version>")
                return 2
            runtime_refs.register(_data_dir(), args[1], args[2])
            return 0
        if command == "unregister":
            if len(args) < 3:
                print("usage: runtime_cli unregister <app_id> <version>")
                return 2
            data_dir, app_id, version = _data_dir(), args[1], args[2]
            runtime_refs.unregister(data_dir, app_id)
            # Signal the installer whether the shared runtime is now orphaned.
            # By slot: a Beta slot goes when its last app goes, and an older
            # app registered as "3.13.1" still keeps the Stable slot alive.
            if runtime_refs.slot_referenced(data_dir, version):
                return 0
            return _UNREFERENCED_EXIT
        if command == "is-referenced":
            if len(args) < 2:
                print("usage: runtime_cli is-referenced <version>")
                return 2
            return 0 if runtime_refs.is_referenced(_data_dir(), args[1]) else _UNREFERENCED_EXIT
        if command == "heal-launch-entries":
            return _heal_launch_entries(args[1] if len(args) > 1 else "")
        print(f"unknown command: {command}")
        return 2
    except Exception as exc:  # noqa: BLE001 - never wedge an install/uninstall
        print(f"runtime_cli error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
