"""Audio Studio filters the optional-components picker to the audio workflow.

The shared picker (``main_frame_speech_downloads``) shows the full catalog for
QUILL (the editor) but, for a companion app that declares
``_optional_component_allowlist``, only the components in that set. Studio's
allowlist is the speech engines, the voices, and the audio pack -- never the
document/editor-only extras (Pandoc, PDF/OCR, braille, MathCAT, Node, Git, gh,
spell-check dictionaries), which do not exist in the standalone Studio.
"""

from __future__ import annotations

from quill.apps.studio import StudioAppFrame
from quill.core.optional_components import gather_optional_components


def _filtered_for_studio() -> set[str]:
    allow = StudioAppFrame._optional_component_allowlist
    return {c.component_id for c in gather_optional_components() if c.component_id in allow}


def test_studio_allowlist_ids_all_exist_in_catalog() -> None:
    # A typo'd id in the allowlist would silently hide a component forever;
    # every id must correspond to a real catalog entry (on this platform).
    catalog = {c.component_id for c in gather_optional_components()}
    # dectalk is Windows-only; allow it to be absent off-Windows.
    import sys

    allow = set(StudioAppFrame._optional_component_allowlist)
    if not sys.platform.startswith("win"):
        allow.discard("dectalk")
    assert allow <= catalog, f"stale allowlist ids: {allow - catalog}"


def test_studio_shows_audio_components_not_document_ones() -> None:
    shown = _filtered_for_studio()
    # Speech engines, voices, and the audio pack are present.
    assert {"whispercpp", "kokoro", "piper", "espeak", "audio_extras"} <= shown
    # Document/editor-only extras are filtered out.
    for hidden in ("pandoc", "pdf_ocr", "braille", "mathcat", "node", "git", "gh"):
        assert hidden not in shown
    # No spell-check dictionaries (dynamic spell-<lang> ids) leak in.
    assert not any(cid.startswith("spell-") for cid in shown)


def test_quill_default_sees_everything() -> None:
    # With no allowlist (the editor's case), nothing is filtered.
    everything = {c.component_id for c in gather_optional_components()}
    assert "pandoc" in everything and "whispercpp" in everything
