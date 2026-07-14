"""Source-contract test for MainFrame.generate_speech_audio (fix.md #4).

Assert the wiring in :mod:`quill.ui.main_frame` without spinning up a real wx
UI, matching the convention in test_remote_sites_dialog.py. The text assembled
from the editor must be routed through the shared markdown sanitizer before
being handed to any synthesis engine (Piper's espeak-ng phonemizer badly
mis-tokenizes raw '#'/'**'/'[text](url)' syntax).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py"


def _generate_speech_audio_source() -> str:
    src = ROOT.read_text(encoding="utf-8")
    match = re.search(
        r"    def generate_speech_audio\(self\).*?\n(?=    def [A-Za-z_]+\()", src, re.DOTALL
    )
    assert match is not None, "generate_speech_audio method not found"
    return match.group(0)


def test_generate_speech_audio_cleans_markdown_before_synthesis() -> None:
    body = _generate_speech_audio_source()
    assert "clean_markdown_text" in body
