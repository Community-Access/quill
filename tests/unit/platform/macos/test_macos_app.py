from __future__ import annotations

import quill.__main__ as qmain
from quill.platform.macos import macos_app


def test_macos_app_entry_delegates_to_canonical_main(monkeypatch) -> None:
    # scripts/setup_macos.py points the py2app bundle's APP at this module, so
    # the .app entry point must dispatch to the single canonical CLI entry point
    # — the same `main` behind the `quill` console script — keeping the bundle
    # and the command line on identical startup behaviour. The entry is now a
    # thin wrapper (_main) that defers the import of `main` so a failure anywhere
    # in QUILL's startup is captured rather than dropped on py2app's screen (#755).
    calls: list[bool] = []

    def fake_main() -> int:
        calls.append(True)
        return 0

    monkeypatch.setattr(qmain, "main", fake_main)
    assert macos_app._main() == 0
    assert calls == [True]


def test_macos_app_entry_logs_and_survives_startup_failure(monkeypatch, tmp_path) -> None:
    # A failure in QUILL's own startup writes the real traceback to the user Logs
    # dir and returns non-zero, instead of raising into py2app's opaque error
    # screen (#755). The native alert is stubbed so the test pops no UI.
    def boom() -> int:
        raise RuntimeError("kaboom-startup")

    monkeypatch.setattr(qmain, "main", boom)
    monkeypatch.setattr(macos_app, "_show_native_error", lambda *_a, **_k: None)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Path.home() on Windows CI

    assert macos_app._main() == 1
    log = tmp_path / "Library" / "Logs" / "Quill" / "startup-error.log"
    assert log.is_file()
    assert "kaboom-startup" in log.read_text(encoding="utf-8")
