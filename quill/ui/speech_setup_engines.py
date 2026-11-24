"""The dictation engine rows of Speech Setup, pure and wx-free.

Moved out of :mod:`quill.ui.speech_setup_dialog` (GATE-11) unchanged; that
module imports it back, so ``speech_setup_dialog.build_engine_descriptors``
still works.
"""

from __future__ import annotations


def build_engine_descriptors(
    all_providers: list,
    *,
    whispercpp_ok: bool,
    faster_whisper_ok: bool,
    engine_scope: str = "all",
) -> list[dict]:
    """Describe every dictation engine as a radio row (installed or not).

    Whisper.cpp is always present (bundled). Faster Whisper appears whether or
    not it is installed: a not-installed row carries an ``install_action`` so
    selecting it installs the engine. Any other registered provider (e.g. a
    cloud Quillin) is appended as an already-installed engine. Vosk never
    appears: it is registered only as the podcast chapter engine
    (``service.CHAPTER_ONLY_PROVIDER_IDS``) and is no dictation choice.
    Pure and wx-free so it is unit-testable.

    ``engine_scope`` narrows the list for the Dictation (Offline)/Dictation
    (Online) tab split: "offline" is just the two local engines above;
    "online" is just the other registered (cloud) providers; "all" (default)
    is both, preserving the original single-tab behavior.
    """
    by_id: dict[str, object] = {}
    for provider in all_providers:
        pid = str(getattr(provider, "id", "") or "")
        if pid:
            by_id[pid] = provider
    descriptors: list[dict] = []
    if engine_scope in ("all", "offline"):
        descriptors += [
            {
                "label": "Whisper (built in)",
                "provider": by_id.get("whispercpp"),
                "installed": whispercpp_ok,
                "install_action": None,
            },
            {
                "label": "Faster Whisper (faster, GPU-capable)",
                "provider": by_id.get("fasterwhisper"),
                "installed": faster_whisper_ok,
                "install_action": "engine",
            },
        ]
    if engine_scope in ("all", "online"):
        from quill.core.speech.service import CHAPTER_ONLY_PROVIDER_IDS

        known = {"whispercpp", "fasterwhisper", *CHAPTER_ONLY_PROVIDER_IDS}
        for pid, provider in by_id.items():
            if pid not in known:
                descriptors.append({
                    "label": str(getattr(provider, "display_name", pid)),
                    "provider": provider,
                    "installed": True,
                    "install_action": None,
                })
    return descriptors
