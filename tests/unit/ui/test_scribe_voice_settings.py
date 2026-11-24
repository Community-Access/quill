"""Convert with Scribe's Language, Dialect, Voice and Play Sample (2026-11-23).

Jeff, testing the QUILL Lite portable: "I just see Scribe default and the play
button does nothing", "shouldn't we detect the language of the operating
system and attempt to set it by default and fill the voices?" and "put
language or dialect before voice". So: a starting dialect from the
document's language or Windows' (a saved choice wins, and a suggestion never
becomes the account's default); a Voice list that has every dialect's voices
when Dialect is Scribe's default; Play Sample answering every press, once,
through QUILL Lite's voice as well as QUILL's; and Language and Dialect before
Voice and Play Sample in Tab order and on screen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe.model import ScribeSettings

pytestmark = pytest.mark.usefixtures("wx_session_app")

LISTS: dict[str, Any] = {
    "languages": [("English", "en"), ("French", "fr")],
    "dialects": {
        "en": [("English (United States)", "en-US"), ("English (United Kingdom)", "en-GB")],
        "fr": [("French (France)", "fr-FR")],
    },
    "voices": {
        "en-US": [("Jenny", "en-US-JennyNeural", True), ("Guy", "en-US-GuyNeural", False)],
        "en-GB": [("Sonia", "en-GB-SoniaNeural", True)],
        "fr-FR": [("Denise", "fr-FR-DeniseNeural", True)],
    },
    "tables": [("UEB Grade 2", "en-ueb-g2")],
}


class Host:
    app_name = "QUILL"

    def __init__(self) -> None:
        self.said: list[str] = []

    def scribe_announce(self, text: str) -> None:
        self.said.append(text)


class Controller:
    def __init__(self, host: Any = None, lists: Any = LISTS) -> None:
        self.host = host or Host()
        self._choice_lists = lists
        self.samples: list[str] = []
        self.fail_next = False

    def _background(self, work: Any, done: Any, failed: Any = None) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            (failed or (lambda _e: None))(error)
            return
        done(result)

    def client(self) -> Any:
        outer = self

        class Client:
            def voice_sample(self, short: str) -> bytes:
                outer.samples.append(short)
                return b"ID3"

            def languages(self) -> Any:
                if outer.fail_next:
                    raise OSError("offline")
                return LISTS["languages"]

            def dialects(self) -> Any:
                return LISTS["dialects"]

            def voices(self) -> Any:
                return LISTS["voices"]

            def braille_tables(self) -> Any:
                return LISTS["tables"]

        return Client()


@pytest.fixture
def later(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """wx.CallLater, run by hand: Play Sample answers a moment after the press."""
    import wx

    calls: list[Any] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: calls.append((fn, a)))
    return calls


def _run(calls: list[Any]) -> None:
    while calls:
        fn, args = calls.pop(0)
        fn(*args)


@pytest.fixture
def make(monkeypatch: pytest.MonkeyPatch) -> Any:
    import wx

    from quill.ui import scribe_convert_settings as scs

    monkeypatch.setattr(scs, "os_language_tags", lambda: ["en-GB"])
    frames: list[Any] = []

    def build(
        settings: ScribeSettings | None = None,
        *,
        hints: list[str] | None = None,
        controller: Any = None,
    ) -> Any:
        frame = wx.Frame(None)
        frames.append(frame)
        panel = wx.Panel(frame)
        sizer = wx.BoxSizer(wx.VERTICAL)
        groups = scs.SettingsGroups(
            panel,
            sizer,
            controller or Controller(),
            settings or ScribeSettings(language="en"),
            ai_off=False,
            app_name="QUILL",
            language_hints=hints,
        )
        panel.SetSizer(sizer)
        return groups

    yield build
    for frame in frames:
        frame.Destroy()


def _strings(control: Any) -> list[str]:
    return list(control.GetStrings())


def _pick(control: Any, text: str, handler: Any) -> None:
    control.SetSelection(_strings(control).index(text))
    handler()


# ------------------------------------------------------------- the dialect


def test_the_documents_language_chooses_the_dialect(make: Any) -> None:
    groups = make(hints=["en-US"])  # Windows says en-GB; the document wins
    assert groups.dialect.GetStringSelection() == "English (United States)"
    assert _strings(groups.voice) == ["Scribe's default", "Jenny", "Guy, no sample"]
    assert groups.suggested()


def test_without_a_document_language_windows_chooses(make: Any) -> None:
    groups = make()
    assert groups.dialect.GetStringSelection() == "English (United Kingdom)"
    assert _strings(groups.voice) == ["Scribe's default", "Sonia"]


def test_a_region_scribe_lacks_falls_back_to_its_language(
    make: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_convert_settings as scs

    monkeypatch.setattr(scs, "os_language_tags", lambda: ["en-IE"])
    groups = make()
    assert groups.dialect.GetStringSelection() == "English (United States)"  # Scribe's first


def test_no_hint_in_the_language_leaves_scribes_default_with_every_voice(
    make: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_convert_settings as scs

    monkeypatch.setattr(scs, "os_language_tags", lambda: ["de-DE"])
    groups = make()
    assert groups.dialect.GetStringSelection() == "Scribe's default"
    assert not groups.suggested()
    assert _strings(groups.voice) == [
        "Scribe's default",
        "Jenny, English (United States)",
        "Guy, English (United States), no sample",
        "Sonia, English (United Kingdom)",
    ]


def test_a_saved_dialect_wins_over_the_suggestion(make: Any) -> None:
    saved = ScribeSettings(
        language="en", dialects={"en": "en-US"}, voices={"en-US": "en-US-GuyNeural"}
    )
    groups = make(saved, hints=["en-GB"])
    assert groups.dialect.GetStringSelection() == "English (United States)"
    assert groups.voice.GetStringSelection() == "Guy, no sample"
    assert not groups.suggested()


def test_detect_still_fills_the_dialect_and_voices(make: Any) -> None:
    groups = make(ScribeSettings(language=""), hints=["fr-FR"])
    assert groups.language.GetStringSelection() == "Detect automatically"
    assert groups.dialect.GetStringSelection() == "French (France)"
    assert _strings(groups.voice) == ["Scribe's default", "Denise"]
    chosen = groups.settings()
    assert chosen.language == "" and chosen.dialects == {"fr": "fr-FR"}


def test_a_suggestion_is_for_this_document_only(make: Any) -> None:
    groups = make()
    assert groups.settings().dialects == {"en": "en-GB"}  # sent with this document
    assert groups.remembered().dialects == {}  # not remembered: suggested afresh
    _pick(groups.dialect, "English (United Kingdom)", groups.dialect_chosen)
    assert not groups.suggested()  # chosen now, even though it is the same one
    assert groups.remembered().dialects == {"en": "en-GB"}


# ------------------------------------------------------------ the voices


def test_choosing_from_every_dialect_chooses_its_dialect(
    make: Any, monkeypatch: pytest.MonkeyPatch, later: list[Any]
) -> None:
    from quill.ui import scribe_convert_settings as scs

    monkeypatch.setattr(scs, "os_language_tags", lambda: [])
    groups = make()
    _pick(groups.voice, "Sonia, English (United Kingdom)", groups.voice_chosen)
    assert groups.dialect.GetStringSelection() == "English (United Kingdom)"
    assert groups.voice.GetStringSelection() == "Sonia, English (United Kingdom)"  # not refilled
    chosen = groups.settings()
    assert chosen.dialects == {"en": "en-GB"} and chosen.voices == {"en-GB": "en-GB-SoniaNeural"}
    _run(later)
    assert groups._controller.host.said == []  # the voice's name already said its dialect


def test_changing_the_dialect_keeps_a_voice_it_still_has(make: Any) -> None:
    groups = make(hints=["en-US"])
    _pick(groups.voice, "Jenny", groups.voice_chosen)
    _pick(groups.dialect, "Scribe's default", groups.dialect_chosen)
    assert groups.voice.GetStringSelection() == "Jenny, English (United States)"
    _pick(groups.dialect, "English (United Kingdom)", groups.dialect_chosen)
    assert groups.voice.GetStringSelection() == "Scribe's default"


def test_a_failed_load_says_so_in_the_list_and_retry_loads(make: Any, later: list[Any]) -> None:
    controller = Controller(lists=None)
    controller.fail_next = True
    groups = make(controller=controller)
    assert _strings(groups.voice) == ["Voices could not be loaded"]
    assert groups.retry.IsShown()
    groups.toggle_sample()
    _run(later)
    assert controller.host.said == ["The voices could not be loaded. Use Retry Loading, Alt+Y."]
    controller.fail_next = False
    groups.load()  # what Retry Loading does
    assert "Jenny" in _strings(groups.voice) or "Sonia" in _strings(groups.voice)
    assert not groups.retry.IsShown()


# ------------------------------------------------------------ Play Sample


def test_play_sample_with_no_voice_says_to_choose_one(make: Any, later: list[Any]) -> None:
    groups = make()
    groups.toggle_sample()
    assert groups._controller.host.said == []  # not inside the key press
    _run(later)
    assert groups._controller.host.said == ["Choose a voice to hear a sample."]


def test_play_sample_for_a_voice_without_one_names_it(make: Any, later: list[Any]) -> None:
    groups = make(hints=["en-US"])
    _pick(groups.voice, "Guy, no sample", groups.voice_chosen)
    groups.toggle_sample()
    _run(later)
    assert groups._controller.host.said == ["Guy has no sample."]
    assert groups._controller.samples == []


def test_play_sample_plays_and_becomes_stop_sample(
    make: Any, later: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_sample_player

    class Player:
        playing = False

        def play(self, data: bytes) -> bool:
            Player.playing = True
            return True

        def is_playing(self) -> bool:
            return Player.playing

        def stop(self) -> None:
            Player.playing = False

    monkeypatch.setattr(scribe_sample_player, "SamplePlayer", Player)
    groups = make(hints=["en-US"])
    _pick(groups.voice, "Jenny", groups.voice_chosen)
    groups.toggle_sample()
    assert groups._controller.samples == ["en-US-JennyNeural"]
    assert groups.sample.GetLabel() == "&Stop Sample" and groups.sample_playing()
    groups.toggle_sample()  # Stop Sample (Escape calls stop_sample too)
    assert groups.sample.GetLabel() == "Play &Sample" and not groups.sample_playing()
    later.clear()
    assert groups._controller.host.said == []  # the button's own name says it


def test_a_sample_that_cannot_be_fetched_says_so_once(make: Any, later: list[Any]) -> None:
    controller = Controller()

    def broken(work: Any, done: Any, failed: Any = None) -> None:
        failed(OSError("404"))

    groups = make(hints=["en-US"], controller=controller)
    _pick(groups.voice, "Jenny", groups.voice_chosen)
    controller._background = broken
    groups.toggle_sample()
    _run(later)
    assert controller.host.said == ["The sample could not be played."]


def test_quill_lite_speaks_play_samples_answer(make: Any, later: list[Any]) -> None:
    """Through LiteScribeHost, the document window's own _announce and the
    app's ScreenReaderVoice to the engine: the whole path Jeff heard nothing on."""
    from quill.apps.lite_voice import ScreenReaderVoice
    from quill.apps.lite_window import DocumentFrame
    from quill.apps.lite_window_scribe import LiteScribeHost

    spoken: list[tuple[str, bool]] = []

    class Engine:
        def announce(self, text: str, *, force_speech: bool = False) -> None:
            spoken.append((text, force_speech))

        def braille(self, _text: str) -> str:
            return ""

    voice = ScreenReaderVoice()
    voice._engine = Engine()
    voice._reader_running = lambda: True  # type: ignore[method-assign]

    class App:
        pass

    app = App()
    app.voice = voice  # type: ignore[attr-defined]

    class Window:
        _announce = DocumentFrame._announce
        status: list[str] = []

        def __init__(self) -> None:
            self.app = app

        def _set_status_message(self, text: str) -> None:
            self.status.append(text)

    window = Window()
    app.frames = [window]  # type: ignore[attr-defined]
    app.active_frame = window  # type: ignore[attr-defined]
    groups = make(controller=Controller(host=LiteScribeHost(app)))
    groups.toggle_sample()
    _run(later)
    assert spoken == [("Choose a voice to hear a sample.", True)]
    assert window.status == ["Choose a voice to hear a sample."]


# ------------------------------------------------------------- the order


def _sizer_windows(sizer: Any) -> list[Any]:
    found: list[Any] = []
    for item in sizer.GetChildren():
        if item.IsWindow():
            found.append(item.GetWindow())
        elif item.IsSizer():
            found.extend(_sizer_windows(item.GetSizer()))
    return found


def _assert_language_dialect_voice(groups: Any) -> None:
    box = groups.boxes["language"]
    tab = list(box.GetStaticBox().GetChildren())  # creation order, after any MoveAfterInTabOrder
    shown = _sizer_windows(box)  # what is on screen, top to bottom
    for order in (tab, shown):
        positions = [
            order.index(control)
            for control in (groups.language, groups.dialect, groups.voice, groups.sample)
        ]
        assert positions == sorted(positions), positions
        # Each list's label right before it, so the reader names the list.
        for control in (groups.language, groups.dialect, groups.voice):
            assert order.index(control._quill_label) == order.index(control) - 1


def test_language_and_dialect_come_before_voice_everywhere(make: Any) -> None:
    groups = make()
    _assert_language_dialect_voice(groups)
    groups._failed()  # Retry Loading appears
    _assert_language_dialect_voice(groups)
    groups.load()  # and goes
    _assert_language_dialect_voice(groups)
    groups.show_for(["docx"])  # the group hidden
    groups.show_for(["mp3"])  # and shown again
    _assert_language_dialect_voice(groups)
    groups.fix_upload_settings("Notes")  # a document already uploaded: Language hidden
    _assert_language_dialect_voice(groups)


def test_the_convert_dialog_keeps_the_order_and_a_suggestion_off_the_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_convert_settings as scs
    from quill.ui.scribe_convert_dialog import ScribeConvertDialog

    monkeypatch.setattr(scs, "os_language_tags", lambda: ["en-GB"])
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    from quill.core.scribe.options import ScribeOptions

    controller = Controller()
    controller.app_name = "QUILL"  # type: ignore[attr-defined]
    source = tmp_path / "Notes.html"
    source.write_text('<html lang="en-US"><body>Hi</body></html>')
    dialog = ScribeConvertDialog(
        None, controller, paths=[source], formats=["mp3"], options=ScribeOptions()
    )
    try:
        groups = dialog.groups
        _assert_language_dialect_voice(groups)
        assert groups.dialect.GetStringSelection() == "English (United States)"  # the page's lang
        choice = dialog.result()
        assert choice.settings.dialects == {"en": "en-US"}
        assert choice.suggested_dialect and choice.remembered.dialects == {}
    finally:
        dialog.Destroy()


def test_a_suggested_dialect_never_reaches_the_accounts_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ticking "Also save as my Scribe account defaults" sends what the person
    chose; a dialect only suggested is left out (it is for this document)."""
    from quill.core import scribe
    from quill.core.scribe import queue as q
    from quill.ui.scribe_controller import ScribeController
    from quill.ui.scribe_convert_dialog import ConvertChoice

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(scribe, "CLIENT_ID", "test-client")
    host = Host()
    controller = ScribeController(host)  # type: ignore[arg-type]
    controller._queue = q.FamilyQueue(tmp_path / "data" / "scribe")
    monkeypatch.setattr(controller, "ensure_service", lambda: None)
    source = tmp_path / "Notes.pdf"
    source.write_bytes(b"%PDF-1.4 fake")
    sent = ScribeSettings(language="en", dialects={"en": "en-GB"})
    for suggested, ticked, leave_out, remembered in (
        (True, True, ["notify_when_complete", "dialects"], {}),
        (False, True, ["notify_when_complete"], {}),  # the account holds it now
        (True, False, ["notify_when_complete", "dialects"], {}),  # suggested afresh next time
        (False, False, ["notify_when_complete"], {"en": "en-GB"}),  # this app's last choice
    ):
        choice = ConvertChoice(
            formats=["mp3"],
            settings=sent,
            save_as_defaults=ticked,
            remembered=ScribeSettings(language="en") if suggested else sent,
            suggested_dialect=suggested,
        )
        job = controller.queue_choice(choice, paths=[source])[0]
        assert job.settings["dialects"] == {"en": "en-GB"}  # this document gets it either way
        assert job.defaults_leave_out == leave_out
        assert controller.options().last_settings["QUILL"].get("dialects", {}) == remembered


def test_arrowing_through_every_dialects_voices_follows_each_dialect(
    make: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed list chooses each voice as the arrow keys pass it."""
    from quill.ui import scribe_convert_settings as scs

    monkeypatch.setattr(scs, "os_language_tags", lambda: [])
    groups = make()
    _pick(groups.voice, "Jenny, English (United States)", groups.voice_chosen)
    _pick(groups.voice, "Sonia, English (United Kingdom)", groups.voice_chosen)
    assert groups.dialect.GetStringSelection() == "English (United Kingdom)"
    assert groups.settings().voices == {"en-GB": "en-GB-SoniaNeural"}
    _pick(groups.voice, "Scribe's default", groups.voice_chosen)
    assert groups.dialect.GetStringSelection() == "Scribe's default"


def test_two_quick_presses_say_one_answer(make: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    timers: list[Any] = []

    class Timer:
        def __init__(self, _ms: int, fn: Any, *args: Any) -> None:
            self.fn, self.args, self.running = fn, args, True
            timers.append(self)

        def IsRunning(self) -> bool:  # noqa: N802 - wx's name
            return self.running

        def Stop(self) -> None:  # noqa: N802 - wx's name
            self.running = False

    monkeypatch.setattr(wx, "CallLater", Timer)
    groups = make()
    groups.toggle_sample()
    groups.toggle_sample()
    for timer in timers:
        if timer.running:
            timer.fn(*timer.args)
    assert groups._controller.host.said == ["Choose a voice to hear a sample."]


def test_a_press_while_the_sample_downloads_starts_no_second_download(
    make: Any, later: list[Any]
) -> None:
    controller = Controller()
    pending: list[Any] = []
    controller._background = lambda work, done, failed=None: pending.append((work, done))
    groups = make(hints=["en-US"], controller=controller)
    _pick(groups.voice, "Jenny", groups.voice_chosen)
    groups.toggle_sample()
    groups.toggle_sample()
    _run(later)
    assert len(pending) == 1
    assert controller.host.said == ["The sample is still coming."]


def test_a_successful_retry_lands_on_the_filled_language_list(make: Any) -> None:
    controller = Controller(lists=None)
    controller.fail_next = True
    groups = make(controller=controller)
    groups.retry.SetFocus()
    focused: list[Any] = []
    groups.language.SetFocus = lambda: focused.append(_strings(groups.language))  # type: ignore[method-assign]
    import wx

    original = wx.Window.FindFocus
    try:
        wx.Window.FindFocus = staticmethod(lambda: groups.retry)  # type: ignore[method-assign]
        controller.fail_next = False
        groups.load()
    finally:
        wx.Window.FindFocus = original  # type: ignore[method-assign]
    assert focused and "English" in focused[0]  # filled before the focus moved
    # The focus event that move causes is not the person reaching a setting,
    # so account defaults read later still go in.
    groups.touched = False
    event = wx.FocusEvent(wx.wxEVT_SET_FOCUS)
    event.SetEventObject(groups.language)
    groups._on_touched(event)
    assert not groups.touched
    groups._on_touched(event)  # the next one is the person's
    assert groups.touched
