from __future__ import annotations

from pathlib import Path

from quill.__main__ import _launch_arguments


def test_launch_arguments_parse_safe_mode_and_paths(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello", encoding="utf-8")

    paths, safe_mode, reset_profile = _launch_arguments([
        "--safe-mode",
        str(file_path),
        "--ignored",
    ])

    assert safe_mode is True
    assert reset_profile is False
    assert paths == [file_path.resolve()]


def test_launch_arguments_parse_reset_profile() -> None:
    paths, safe_mode, reset_profile = _launch_arguments(["--reset-profile"])

    assert paths == []
    assert safe_mode is False
    assert reset_profile is True


def test_convert_action_launches_converter_app(monkeypatch) -> None:
    # The Explorer "Convert with Quill" verb runs `-m quill --action convert "%1"`;
    # main() must hand the file to the standalone converter app and exit early,
    # never bootstrapping the full editor.
    import quill.__main__ as m

    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        "quill.core.app_launcher.launch_app",
        lambda key, *, extra_args=(): calls.append((key, extra_args)) or True,
    )
    monkeypatch.setattr(m.sys, "argv", ["quill", "--action", "convert", "song.mp3"])
    assert m.main() == 0
    assert calls == [("converter", ("song.mp3",))]
