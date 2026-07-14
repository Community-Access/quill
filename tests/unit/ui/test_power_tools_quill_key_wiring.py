from __future__ import annotations

from pathlib import Path


def _main_frame_source() -> str:
    # The QUILL-key / Quick-Nav handling was extracted into the QuillKeyMixin
    # module (CQ-1); read both so these wiring contracts hold wherever the code
    # physically lives.
    ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    return "\n".join(
        (ui / name).read_text(encoding="utf-8")
        for name in ("main_frame.py", "main_frame_quill_key.py")
    )


def test_quill_key_chord_dispatch_is_data_driven() -> None:
    # Chord commands are now dispatched from the keymap, not hardcoded.
    # The state machine must contain _chord_command_for_event, not a hardcoded
    # key_code check for M or a direct paste_html_as_markdown() call.
    source = _main_frame_source()
    assert "_chord_command_for_event" in source
    assert 'key_code in (ord("M"), ord("m"))' not in source


def test_power_tools_mixin_is_wired_into_main_frame() -> None:
    source = _main_frame_source()
    assert "from quill.ui.main_frame_power_tools import PowerToolsActionsMixin" in source
    assert "PowerToolsActionsMixin" in source.split("class MainFrame(")[1].split(")")[0]


def test_paste_html_as_markdown_is_on_quill_key_m_in_keymap() -> None:
    # Verify the keymap (not the state machine) is the source of truth for M.
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP.get("power.paste_html_as_markdown") == "Ctrl+Shift+Grave, M"
    assert DEFAULT_KEYMAP.get("format.insert_markdown_tag", "") == ""


def test_prefix_message_mentions_chord_keys() -> None:
    quill_key_source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_quill_key.py"
    ).read_text(encoding="utf-8")
    assert "configured chord key" in quill_key_source
