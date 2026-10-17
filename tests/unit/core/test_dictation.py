from __future__ import annotations

from quill.core.dictation import (
    DictationController,
    DictationSettings,
)


def test_stop_returns_joined_segments_and_resets_state() -> None:
    controller = DictationController()
    controller._segments = ["first", " ", "second"]  # type: ignore[attr-defined]
    result = controller.stop()
    assert result == "first second"
    assert controller.state == "idle"


def test_default_engine_is_windows() -> None:
    # Only the OS dictation panel is functional today; the default reflects that
    # rather than promising an offline recognizer that is not wired up (S0).
    assert DictationSettings().engine == "windows"


def test_nothing_in_the_app_imports_the_deprecated_shim() -> None:
    """The legacy Win+H shim is deprecated (QUILL 1.1) and goes in QUILL 1.2.

    Its two callers were pointed at the voice typing route on 2026-10-17; a new
    import would make the removal break something, so none may come back.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "quill"
    found = []
    for path in root.rglob("*.py"):
        if path.name == "dictation.py" and path.parent.name == "core":
            continue
        text = path.read_text(encoding="utf-8")
        if "quill.core.dictation" not in text and "from quill.core import" not in text:
            continue  # cannot import it; parsing every module would take seconds
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "quill.core.dictation":
                found.append(str(path.relative_to(root)))
            elif isinstance(node, ast.ImportFrom) and node.module == "quill.core":
                if any(alias.name == "dictation" for alias in node.names):
                    found.append(str(path.relative_to(root)))
            elif isinstance(node, ast.Import):
                if any(alias.name == "quill.core.dictation" for alias in node.names):
                    found.append(str(path.relative_to(root)))
    assert found == []
