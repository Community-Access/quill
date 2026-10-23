"""Speech Models: consent, metered, free space, progress, cancel, remove, use -- no network."""

from __future__ import annotations

import pytest

from tests.wx_session import patch_call_after, shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    wx.HelpProvider.Set(wx.SimpleHelpProvider())  # SetHelpText stores nothing without one
    yield app


class _NowThread:
    """threading.Thread, run at once on this thread."""

    def __init__(self, target, name: str = "", daemon: bool = True) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture
def dialog_module(monkeypatch, tmp_path):
    import quill.ui.dictation_models_dialog as module
    from quill.core.windows_dictation import model_store

    monkeypatch.setenv(model_store.DOWNLOADS_VARIABLE, str(tmp_path / "models"))
    monkeypatch.setattr(module.threading, "Thread", _NowThread)
    patch_call_after(monkeypatch, lambda fn, *args: fn(*args))
    monkeypatch.setattr("quill.core.net_metered.connection_cost", lambda: "unmetered")
    return module


def _open(module, said: list[str] | None = None, tiny: float = 0.01):
    from quill.core.windows_dictation.speed_check import SpeedCheck

    check = SpeedCheck(tiny=tiny, cores=2 if tiny > 0.1 else 12, memory_gb=8.0)
    return module.SpeechModelsDialog(
        None, (said if said is not None else []).append, run_check=lambda: check
    )


def _questions(monkeypatch, module, answer: int = None) -> list[str]:
    asked: list[str] = []

    def box(message, caption, style, parent=None, **_kw):
        asked.append(message)
        return wx.YES if answer is None else answer

    monkeypatch.setattr(module, "show_message_box", box)
    return asked


def test_the_list_reads_in_our_suggested_order_with_tiny_in_its_place(
    wx_app, dialog_module
) -> None:
    dialog = _open(dialog_module)
    try:
        rows = [dialog.models.GetString(i) for i in range(dialog.models.GetCount())]
        assert rows[0].startswith("NVIDIA Nemotron 3.5 ASR Streaming 0.6B")
        # The suggested download is Parakeet Unified since 2026-10-22.
        assert "Suggested download" in rows[1] and rows[1].startswith("NVIDIA Parakeet Unified")
        assert rows[5].startswith("Whisper tiny, Lightweight: built in")
        assert rows[4].startswith("Whisper base")
        assert all(row.endswith(".") for row in rows)
    finally:
        dialog.Destroy()


def test_details_say_sizes_languages_licence_where_and_the_speed_verdict(
    wx_app, dialog_module
) -> None:
    # Nemotron's real-speech cost is 5.8 times Moonshine tiny, so tiny at 0.3
    # seconds a second puts it past the lag limit.
    dialog = _open(dialog_module, tiny=0.3)
    try:
        text = dialog.details.GetValue()
        for part in (
            "682 MB",
            "English and Spanish",
            "OpenMDW-1.1",
            "openmdw.ai",
            "Saved in:",
            "Works best on:",
            "no graphics card",
            "FLEURS",
        ):
            assert part in text, part
        assert "may lag behind your speech on this computer" in text
        assert dialog.download.IsEnabled() and not dialog.use.IsEnabled()
        assert not dialog.cancel_download.IsEnabled()
    finally:
        dialog.Destroy()


def test_nothing_downloads_without_a_yes_that_names_source_size_licence_and_place(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.windows_dictation import model_store

    started: list[str] = []
    monkeypatch.setattr(model_store, "download", lambda model, **_kw: started.append(model.id))
    monkeypatch.setattr(model_store, "free_space_problem", lambda _m: "")
    asked = _questions(monkeypatch, dialog_module, answer=wx.NO)
    dialog = _open(dialog_module)
    try:
        dialog._on_download(None)
        assert started == []
        question = asked[-1]
        for part in (
            "Hugging Face",
            "682 MB",
            "OpenMDW-1.1",
            "never sent anywhere",
            str(model_store.model_folder(dialog.selected())),
        ):
            assert part in question, part
    finally:
        dialog.Destroy()


def test_a_metered_connection_is_asked_about_first(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr("quill.core.net_metered.connection_cost", lambda: "metered")
    monkeypatch.setattr(model_store, "free_space_problem", lambda _m: "")
    started: list[str] = []
    monkeypatch.setattr(model_store, "download", lambda model, **_kw: started.append(model.id))
    asked = _questions(monkeypatch, dialog_module, answer=wx.NO)
    dialog = _open(dialog_module)
    try:
        dialog._on_download(None)
        assert len(asked) == 1 and "metered" in asked[0]
        assert started == []
    finally:
        dialog.Destroy()


def test_too_little_space_stops_before_asking(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(
        model_store, "free_space_problem", lambda _m: "There is not enough free space."
    )
    asked = _questions(monkeypatch, dialog_module)
    dialog = _open(dialog_module)
    try:
        dialog._on_download(None)
        assert asked == ["There is not enough free space."]
    finally:
        dialog.Destroy()


def test_a_download_reports_progress_by_quarters_and_its_end(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "free_space_problem", lambda _m: "")
    _questions(monkeypatch, dialog_module)

    def download(model, *, progress, should_cancel):
        for step in (0.1, 0.3, 0.31, 0.6, 0.9):
            progress(step, "")
        assert not should_cancel()

    monkeypatch.setattr(model_store, "download", download)
    said: list[str] = []
    dialog = _open(dialog_module, said)
    try:
        dialog._on_download(None)
        assert said[0].startswith("Downloading NVIDIA Nemotron")
        assert said[1:4] == ["30 percent.", "60 percent.", "90 percent."]
        assert "is downloaded" in said[-1]
        assert dialog.gauge.GetValue() == 100
    finally:
        dialog.Destroy()


def test_cancel_stops_the_download_and_says_it_carries_on(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.release_assets import DownloadCancelled
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "free_space_problem", lambda _m: "")
    _questions(monkeypatch, dialog_module)

    def download(model, *, progress, should_cancel):
        dialog._cancel.set()
        assert should_cancel()
        raise DownloadCancelled("Download cancelled.")

    monkeypatch.setattr(model_store, "download", download)
    said: list[str] = []
    dialog = _open(dialog_module, said)
    try:
        dialog._on_download(None)
        assert "stopped" in said[-1] and "carries on" in said[-1]
        assert dialog.download.IsEnabled()
    finally:
        dialog.Destroy()


def test_a_failed_download_is_its_sentence(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "free_space_problem", lambda _m: "")
    _questions(monkeypatch, dialog_module)

    def download(model, **_kw):
        raise model_store.ModelDownloadError("It did not match its checksum, so it was deleted.")

    monkeypatch.setattr(model_store, "download", download)
    said: list[str] = []
    dialog = _open(dialog_module, said)
    try:
        dialog._on_download(None)
        assert said[-1] == "It did not match its checksum, so it was deleted."
        assert dialog.progress.GetValue() == said[-1]
    finally:
        dialog.Destroy()


def test_remove_asks_then_frees_the_space(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    removed: list[str] = []
    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    monkeypatch.setattr(model_store, "remove", removed.append)
    asked = _questions(monkeypatch, dialog_module)
    said: list[str] = []
    dialog = _open(dialog_module, said)
    try:
        assert dialog.remove.IsEnabled() and dialog.use.IsEnabled()
        dialog._on_remove(None)
        assert "frees 682 MB" in asked[-1]
        assert removed == ["nemotron"]
        assert said[-1] == "NVIDIA Nemotron 3.5 ASR Streaming 0.6B removed."
        assert dialog.progress.GetValue().endswith("682 MB freed.")
        assert dialog.FindFocus() is dialog.models  # not the now-disabled Remove
    finally:
        dialog.Destroy()


def test_use_for_dictation_hands_back_the_model(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    dialog = _open(dialog_module)
    ended: list[int] = []
    monkeypatch.setattr(dialog, "EndModal", ended.append)
    try:
        dialog.models.SetSelection(3)  # Whisper small
        dialog._show_details()
        dialog._on_use(None)
        assert dialog.chosen == "whisper_small" and ended == [wx.ID_OK]
    finally:
        dialog.Destroy()


def test_every_control_has_inline_help(wx_app, dialog_module) -> None:
    dialog = _open(dialog_module)
    try:
        for control in (
            dialog.models,
            dialog.details,
            dialog.progress,
            dialog.gauge,
            dialog.download,
            dialog.cancel_download,
            dialog.remove,
            dialog.use,
            dialog.switch_recommended,
        ):
            assert control.GetHelpText(), control.GetName()
    finally:
        dialog.Destroy()


def test_dictation_settings_lists_a_downloaded_model_and_opens_speech_models(
    wx_app, monkeypatch
) -> None:
    """One dialog serves QUILL and QUILL Lite, so this is the engine list in both."""
    from quill.core.windows_dictation import model_store
    from quill.core.windows_dictation.model_catalog import downloadable
    from quill.ui import dictation_models_dialog
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    monkeypatch.setattr(model_store, "installed_models", lambda: [downloadable("whisper_small")])

    class _Settings:
        windows_dictation_engine = "moonshine"

    said: list[str] = []
    dialog = WindowsDictationDialog(None, _Settings(), said.append)
    try:
        labels = [dialog.engine.GetString(i) for i in range(dialog.engine.GetCount())]
        assert "Whisper small (downloaded), High accuracy" in labels
        assert dialog.speech_models.GetHelpText()
        monkeypatch.setattr(
            dictation_models_dialog, "open_speech_models", lambda *_a, **_k: "whisper_small"
        )
        dialog._on_speech_models(None)
        assert dialog.engine.GetStringSelection() == "Whisper small (downloaded), High accuracy"
        # Focus returns to the Speech Models button, not the engine list.
        assert said[-1] == "Speech engine: Whisper small. Press OK to keep it."
        settings = _Settings()
        dialog.apply(settings)
        assert settings.windows_dictation_engine == "whisper_small"
    finally:
        dialog.Destroy()


def test_both_editors_open_the_shared_settings_window() -> None:
    from quill.apps.lite_window_dictation import DocumentDictationMixin
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
    from quill.ui.windows_dictation_commands import WindowsDictationMixin

    for editor in (DocumentDictationMixin, WindowsDictationCommandsMixin):
        assert issubclass(editor, WindowsDictationMixin)
        assert editor.cmd_dictation_settings is WindowsDictationMixin.cmd_dictation_settings


def test_speech_models_is_findable_and_has_its_own_access_key(wx_app) -> None:
    from quill.ui.preferences_search import _targets, find_settings
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    class _Settings:
        pass

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        found = find_settings(_targets(dialog), "speech models")
        assert any(target.control is dialog.speech_models for target in found)
        keys = [
            child.GetLabel().split("&")[1][:1].lower()
            for child in dialog.GetChildren()
            if "&" in child.GetLabel().replace("&&", "")
        ]
        assert keys.count("b") == 1 and len(keys) == len(set(keys))
    finally:
        dialog.Destroy()


def test_the_recommendation_is_text_to_read_with_its_reasons(wx_app, dialog_module) -> None:
    """D-22: the advice is read-only text, every row names its tier, and nothing
    is chosen for the person."""
    dialog = _open(dialog_module)
    try:
        advice = dialog.advice.GetValue()
        # Parakeet Unified: the fewest mistakes on real recordings (3.2 percent)
        # at a Lightweight cost.
        assert advice.startswith("Recommended for this computer: NVIDIA Parakeet Unified")
        assert "Measured on one computer with real recordings" in advice
        assert dialog.advice.GetHelpText() and dialog.priority.GetHelpText()
        assert dialog.show_recommended.GetHelpText()
        rows = [dialog.models.GetString(i) for i in range(dialog.models.GetCount())]
        # Nemotron got 5.3 percent wrong on real speech at a cost of 5.8: Balanced.
        assert rows[0].startswith("NVIDIA Nemotron 3.5 ASR Streaming 0.6B, Balanced:")
        assert "Tier: Balanced:" in dialog.details.GetValue()
        assert dialog.chosen is None
    finally:
        dialog.Destroy()


def test_what_matters_most_changes_the_advice_and_says_so(wx_app, dialog_module) -> None:
    said: list[str] = []
    dialog = _open(dialog_module, said)
    try:
        dialog.priority.SetSelection(1)  # the quickest response
        dialog._on_priority(None)
        assert dialog.advice.GetValue().startswith(
            "Recommended for this computer: Moonshine (built in)"
        )
        assert said[-1] == "Recommended: Moonshine (built in)."
        assert not dialog.show_recommended.IsEnabled()  # Moonshine has no row here
    finally:
        dialog.Destroy()


def test_show_recommended_moves_to_its_row_and_chooses_nothing(wx_app, dialog_module) -> None:
    dialog = _open(dialog_module)
    try:
        dialog.models.SetSelection(0)  # Nemotron, not the recommendation
        dialog._on_show_recommended(None)
        assert dialog.selected().id == "parakeet_unified"
        assert dialog.chosen is None
    finally:
        dialog.Destroy()


def test_spanish_advice_follows_the_dictation_language(wx_app, dialog_module) -> None:
    from quill.core.windows_dictation.speed_check import SpeedCheck

    check = SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8)
    dialog = dialog_module.SpeechModelsDialog(None, None, run_check=lambda: check, language="es")
    try:
        # Spanish is ranked by real Spanish speech: Parakeet TDT v3, 5.9 percent.
        assert "NVIDIA Parakeet TDT 0.6B v3" in dialog.advice.GetValue()
        dialog._on_show_recommended(None)
        assert dialog.selected().id == "parakeet"
    finally:
        dialog.Destroy()


def test_dictation_settings_shows_the_recommendation(wx_app, monkeypatch) -> None:
    """QUILL and QUILL Lite's Speech engine list gets the same line as Transcribe's
    Choose Model, and it follows the dictation language."""
    from quill.core.windows_dictation.model_advice import recommend
    from quill.core.windows_dictation.speed_check import SpeedCheck
    from quill.ui import windows_dictation_dialog
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    check = SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8)
    monkeypatch.setattr(
        windows_dictation_dialog, "for_this_computer", lambda language: recommend(check, language)
    )

    class _Settings:
        windows_dictation_engine = "moonshine"

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        assert dialog.advice.GetValue().startswith(
            "NVIDIA Parakeet Unified 0.6B, Lightweight: keeps up"
        )
        assert dialog.advice.GetHelpText()
        dialog.speech_language.SetSelection(1)  # Spanish
        dialog._on_speech_language(None)
        assert dialog.advice.GetValue().startswith("NVIDIA Parakeet TDT 0.6B v3, Lightweight:")
    finally:
        dialog.Destroy()


# -- Switch to Recommended Model, and the offer after a switch (2026-10-23) ----


def test_switch_to_recommended_chooses_it_when_it_is_here(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    dialog = _open(dialog_module)
    ended: list[int] = []
    monkeypatch.setattr(dialog, "EndModal", ended.append)
    try:
        assert dialog.switch_recommended.IsEnabled()
        dialog._on_switch_recommended(None)
        assert dialog.chosen == "parakeet_unified" and ended == [wx.ID_OK]
    finally:
        dialog.Destroy()


def test_switch_to_recommended_never_downloads_it(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: False)
    monkeypatch.setattr(model_store, "download", lambda *a, **k: pytest.fail("downloaded"))
    told = _questions(monkeypatch, dialog_module, wx.OK)
    dialog = _open(dialog_module)
    ended: list[int] = []
    monkeypatch.setattr(dialog, "EndModal", ended.append)
    try:
        dialog.models.SetSelection(0)
        dialog._on_switch_recommended(None)
        assert told[-1].startswith("NVIDIA Parakeet Unified 0.6B is not on this computer yet.")
        assert dialog.selected().id == "parakeet_unified"  # taken to its row
        assert dialog.chosen is None and ended == []
    finally:
        dialog.Destroy()


def test_switch_to_a_built_in_recommendation_needs_nothing_downloaded(
    wx_app, dialog_module, monkeypatch
) -> None:
    dialog = _open(dialog_module)
    ended: list[int] = []
    monkeypatch.setattr(dialog, "EndModal", ended.append)
    try:
        dialog.priority.SetSelection(1)  # the quickest response: Moonshine, built in
        dialog._on_priority(None)
        dialog._on_switch_recommended(None)
        assert dialog.chosen == "moonshine" and ended == [wx.ID_OK]
    finally:
        dialog.Destroy()


def test_after_a_switch_the_old_files_are_offered_no_by_default(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.windows_dictation import model_store

    styles: list[int] = []
    asked: list[str] = []

    def box(message, caption, style, parent=None, **_kw):
        asked.append(message)
        styles.append(style)
        return wx.YES

    removed: list[str] = []
    said: list[str] = []
    monkeypatch.setattr(dialog_module, "show_message_box", box)
    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    monkeypatch.setattr(model_store, "remove", removed.append)
    assert dialog_module.offer_to_remove_replaced(None, "whisper_small", "parakeet", said.append)
    # It leads with the switch: it is heard straight after another window closed.
    assert asked[-1].startswith(
        "Now using NVIDIA Parakeet TDT 0.6B v3. Delete Whisper small to free 375 MB?"
    )
    assert "will need it downloaded again" in asked[-1]
    assert styles[-1] & wx.NO_DEFAULT
    assert removed == ["whisper_small"]
    assert said == ["Whisper small deleted. 375 MB freed."]


def test_no_keeps_the_old_files(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    monkeypatch.setattr(model_store, "remove", lambda _id: pytest.fail("deleted"))
    _questions(monkeypatch, dialog_module, wx.NO)
    said: list[str] = []
    assert not dialog_module.offer_to_remove_replaced(
        None, "whisper_small", "parakeet", said.append
    )
    assert said == []


@pytest.mark.parametrize(
    ("old", "new", "here"),
    [
        ("moonshine", "parakeet", True),  # built in: nothing to delete
        ("parakeet", "parakeet", True),  # no switch
        ("whisper_small", "parakeet", False),  # not on this computer
        ("", "parakeet", True),
    ],
)
def test_nothing_is_asked_without_files_to_free(
    wx_app, dialog_module, monkeypatch, old: str, new: str, here: bool
) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: here)
    asked = _questions(monkeypatch, dialog_module)
    assert not dialog_module.offer_to_remove_replaced(None, old, new, lambda _s: None)
    assert asked == []


def test_a_model_in_use_is_kept_and_says_why(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    def busy(_id):
        raise model_store.ModelDownloadError("It could not be deleted; dictation is using it.")

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    monkeypatch.setattr(model_store, "remove", busy)
    asked = _questions(monkeypatch, dialog_module)
    said: list[str] = []
    assert not dialog_module.offer_to_remove_replaced(
        None, "whisper_small", "parakeet", said.append
    )
    assert asked[-1].startswith("Whisper small could not be deleted;")
    assert said == []


def test_never_asked_while_dictation_may_hold_the_old_model(
    wx_app, dialog_module, monkeypatch
) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    asked = _questions(monkeypatch, dialog_module)
    assert not dialog_module.will_offer("whisper_small", "parakeet", in_use=True)
    assert not dialog_module.offer_to_remove_replaced(
        None, "whisper_small", "parakeet", lambda _s: None, in_use=True
    )
    assert asked == []


def test_switch_waits_for_a_running_download(wx_app, dialog_module, monkeypatch) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _m: True)
    told = _questions(monkeypatch, dialog_module, wx.OK)
    dialog = _open(dialog_module)
    try:
        dialog._busy = dialog._rows[0]
        dialog._on_switch_recommended(None)
        assert told[-1].startswith("A model is downloading.")
        assert dialog.chosen is None
    finally:
        dialog._busy = None
        dialog.Destroy()
