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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: runtime_cli <register|unregister|is-referenced|data-dir> ...")
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
            if runtime_refs.is_referenced(data_dir, version):
                return 0
            return _UNREFERENCED_EXIT
        if command == "is-referenced":
            if len(args) < 2:
                print("usage: runtime_cli is-referenced <version>")
                return 2
            return 0 if runtime_refs.is_referenced(_data_dir(), args[1]) else _UNREFERENCED_EXIT
        print(f"unknown command: {command}")
        return 2
    except Exception as exc:  # noqa: BLE001 - never wedge an install/uninstall
        print(f"runtime_cli error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
