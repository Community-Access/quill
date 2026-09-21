"""Every focusable control on a wizard page reaches a screen reader named.

A ``wx.Choice`` or ``wx.SpinCtrl`` has no label of its own, and these pages do
name theirs -- "Engine", "Voice", "Rate (WPM)", "Casting rules" -- with
``SetName``. The catch is that ``SetName`` sets the internal
``FindWindowByName`` key and does **not** reliably reach MSAA/UIA. The nightly
UIA run found six focusable controls on the Voices page reporting an empty UIA
``Name``: a spin control's Edit and Spinner, and two Choice controls with their
inner Text. A screen reader arriving at one of those has nothing to say but
"combo box", and the person cannot tell the voice picker from the engine picker
without tabbing out to read the label.

``publish_accessible_names`` states each authored name to the accessibility
layer, and the wizard runs it once per page. This is the gate, and it runs
against the **real wizard** -- every page, built the way the application builds
them -- because the helper working on a synthetic panel would prove nothing
about the hundred real constructions it has to cover.

Why here and not in the UIA suite: that suite is informational, nightly, and
needs a desktop session, so a regression there is found late by somebody
reading a log. This finds it in the fast suite, in seconds, on the pull request
that caused it.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.audio_studio.pages_base import (  # noqa: E402
    _UNLABELLED_CONTROLS,
    _WX_DEFAULT_NAMES,
    publish_accessible_names,
)
from quill.ui.audio_studio.request import BatchSpeechRequest  # noqa: E402
from quill.ui.audio_studio.wizard import AudioStudioWizard  # noqa: E402

_VOICES = {
    "kokoro": [("Liam", "am_liam"), ("Heart", "af_heart")],
    "sapi5": [("David", "David"), ("Zira", "Zira")],
}


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _defaults(tmp_path: Path) -> BatchSpeechRequest:
    return BatchSpeechRequest(
        source_folder=tmp_path,
        recursive=False,
        extensions=(".docx", ".html", ".htm"),
        engine="kokoro",
        voice="am_liam",
        rate=190,
        speed=1.1,
        output_format="mp3",
        sound_enabled=True,
        sound_volume=80,
        article_gap_ms=1200,
        sentence_gap_ms=250,
        tail_padding_ms=300,
        speak_headings=True,
        skip_existing=False,
    )


def _wizard(tmp_path: Path):
    frame = wx.Frame(None)
    dialog = AudioStudioWizard(
        frame,
        defaults=_defaults(tmp_path),
        engine_options=[("Windows (SAPI 5)", "sapi5"), ("Kokoro (neural, offline)", "kokoro")],
        engine_available={"sapi5": True, "kokoro": True},
        voices_for=lambda engine: _VOICES.get(engine, []),
        on_preview=lambda engine, voice: None,
    )
    return frame, dialog


def _controls(dialog):
    for page in dialog._all_pages:  # noqa: SLF001 - the gate is about all of them
        for child in page.GetChildren():
            if isinstance(child, _UNLABELLED_CONTROLS):
                yield page, child


def test_every_unlabelled_control_states_its_name_to_the_reader(wx_app, tmp_path) -> None:
    """A name only wx can see is a name the person never hears."""
    frame, dialog = _wizard(tmp_path)
    try:
        complaints: list[str] = []
        for page, child in _controls(dialog):
            name = (child.GetName() or "").strip()
            if name.lower() in _WX_DEFAULT_NAMES:
                complaints.append(
                    f"{page.GetName()}: {type(child).__name__} has no name at all "
                    f"(still wx's default {name!r}) -- give it one with SetName"
                )
            elif getattr(child, "_a11y_helper", None) is None:
                complaints.append(
                    f"{page.GetName()}: {type(child).__name__} {name!r} is named for wx "
                    "but not for the accessibility layer"
                )
        assert not complaints, (
            "wizard controls a screen reader would announce by role alone:\n  "
            + "\n  ".join(complaints)
        )
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_publishing_is_idempotent_and_did_real_work(wx_app, tmp_path) -> None:
    """A pass that publishes nothing would let the gate above pass vacuously."""
    frame, dialog = _wizard(tmp_path)
    try:
        published = [child for _, child in _controls(dialog) if hasattr(child, "_a11y_helper")]
        assert len(published) >= 20, f"only {len(published)} controls carry an accessible name"
        assert all(
            publish_accessible_names(page)  # noqa: SLF001
            == 0
            for page in dialog._all_pages  # noqa: SLF001
        ), "the publish pass is not idempotent; it found work on a second run"
    finally:
        dialog.Destroy()
        frame.Destroy()


def test_publishing_never_invents_a_name(wx_app, tmp_path) -> None:
    """The authored name survives verbatim; nothing is derived from a neighbour.

    An earlier draft of the helper read the preceding ``wx.StaticText``. That
    would have renamed the casting pattern field -- authored as "Casting
    pattern (title glob or #number)" -- to the whole three-sentence paragraph
    above it, which a reader then says in full on every visit. Names come from
    the control, or not at all.
    """
    frame, dialog = _wizard(tmp_path)
    try:
        for _page, child in _controls(dialog):
            helper = getattr(child, "_a11y_helper", None)
            if helper is None:
                continue
            _status, spoken = helper.GetName(0)
            assert spoken == child.GetName(), (
                f"{type(child).__name__} says {spoken!r} but is named {child.GetName()!r}"
            )
            assert len(spoken) <= 80, f"an accessible name grew into a sentence: {spoken!r}"
    finally:
        dialog.Destroy()
        frame.Destroy()
