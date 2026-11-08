"""Scrobbling and AudD from the app's side: titles in, ticks, workers, Preferences.

All fakes: no wx timer, no credential store (tests/conftest.py's
``radio_credential_store``), no network, no libmpv.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.apps import radio_preferences_scrobble as prefs
from quill.core.radio import lastfm, radio_credentials, scrobbling, song_recognition
from quill.core.radio import scrobble_queue as sq
from quill.core.radio.history import RadioHistory
from quill.core.radio.scrobble_tracker import Listen
from quill.ui.radio import scrobble_commands, scrobble_signin, song_identify_commands

T0 = 1_800_000_000.0


class _Tasks:
    def __init__(self) -> None:
        self.names: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
        self.names.append(name)
        try:
            result = work()
        except Exception as error:  # noqa: BLE001 - mirror the task manager
            on_failure("op", error)
            return
        on_success("op", result)


class _Wx:
    OK, CANCEL, YES, NO = 4, 16, 2, 8
    YES_NO = 10
    NO_DEFAULT = 128
    ICON_QUESTION = ICON_INFORMATION = 0

    @staticmethod
    def CallAfter(fn: Any, *args: Any) -> None:  # noqa: N802 - wx's name
        fn(*args)


class _Station:
    station_uuid = "uuid-1"
    stream_url = "https://example.invalid/stream"
    name = "Test FM"


class _Controller:
    def __init__(self) -> None:
        self.behind = 0.0
        self.station: Any = _Station()

    @property
    def state(self) -> Any:
        return type("S", (), {"station": self.station})()

    def behind_live_seconds(self) -> float:
        return self.behind


class _Host:
    def __init__(self, history: RadioHistory | None = None) -> None:
        self._radio_history = history or RadioHistory()
        self._radio_controller = _Controller()
        self._task_manager = _Tasks()
        self._wx = _Wx()
        self._safe_mode = False
        self.said: list[str] = []
        self.boxes: list[str] = []
        self.box_answer = _Wx.OK

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _show_message_box(self, message: str, _caption: str, _style: int = 0) -> int:
        self.boxes.append(message)
        return self.box_answer


@pytest.fixture
def scrobbling_on(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, radio_credential_store: dict[str, Any]
) -> dict[str, Any]:
    """ListenBrainz on with a token; sends recorded instead of made."""
    radio_credential_store[radio_credentials.LISTENBRAINZ_TOKEN] = ("LBTOKEN", "")
    monkeypatch.setattr(scrobble_commands, "_make_queue", lambda: sq.ScrobbleQueue(tmp_path))
    sent: dict[str, Any] = {"batches": [], "now_playing": []}

    def _submit_due(queue: sq.ScrobbleQueue, accounts: Any, *, now: float, safe_mode: bool):
        results = []
        for service in accounts.services():
            batch = queue.due_batch(service, now=now)
            if batch:
                sent["batches"].append((service, batch))
                outcome = sent.get("outcome", sq.Outcome(sq.SENT))
                queue.settle(service, batch, outcome, now=now)
                results.append((service, outcome))
        return results

    monkeypatch.setattr(scrobbling, "submit_due", _submit_due)
    monkeypatch.setattr(
        scrobbling,
        "send_now_playing",
        lambda _accounts, listen, **_k: sent["now_playing"].append(listen),
    )
    history = RadioHistory()
    history.scrobble_listenbrainz = True
    sent["host"] = _Host(history)
    return sent


def _listen_for(host: _Host, seconds: float, *, start: float = T0) -> None:
    moment = start
    while moment <= start + seconds:
        scrobble_commands.tick(host, now=moment)
        moment += 5


def test_a_minute_of_a_song_is_sent_off_the_ui_thread(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    scrobble_commands.on_title(host, "Artist - Song", now=T0)
    _listen_for(host, 70)
    assert scrobbling_on["now_playing"] == [Listen("Artist", "Song", int(T0))]
    ((service, batch),) = scrobbling_on["batches"]
    assert service == "listenbrainz" and batch == [Listen("Artist", "Song", int(T0))]
    assert "radio-scrobble-send" in host._task_manager.names
    assert host.said == [], "a song sent is not news"


def test_time_shift_is_read_from_the_engine(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    scrobble_commands.on_title(host, "A - First", now=T0)
    scrobble_commands.on_title(host, "B - Second", now=T0 + 30)
    host._radio_controller.behind = 300.0  # five minutes behind live
    _listen_for(host, 70, start=T0 + 300)
    titles = [listen.title for _s, batch in scrobbling_on["batches"] for listen in batch]
    assert titles == [], "only 30 s of First is in the buffer before Second"
    _listen_for(host, 70, start=T0 + 375)
    titles = [listen.title for _s, batch in scrobbling_on["batches"] for listen in batch]
    assert titles == ["Second"]


def test_noise_titles_are_not_sent(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    scrobble_commands.on_title(host, "Test FM", now=T0)
    _listen_for(host, 120)
    assert scrobbling_on["batches"] == [] and scrobbling_on["now_playing"] == []


def test_nothing_happens_while_scrobbling_is_off(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    radio_credential_store[radio_credentials.LISTENBRAINZ_TOKEN] = ("LBTOKEN", "")
    host = _Host()
    scrobble_commands.on_title(host, "Artist - Song", now=T0)
    assert getattr(host, "_radio_scrobble", None) is None
    _listen_for(host, 120)
    assert host._task_manager.names == []


def test_safe_mode_sends_nothing(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    host._safe_mode = True
    scrobble_commands.on_title(host, "Artist - Song", now=T0)
    _listen_for(host, 120)
    assert host._task_manager.names == []


def test_a_lost_sign_in_is_said_once(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    scrobbling_on["outcome"] = sq.Outcome(sq.SIGN_IN, "ListenBrainz did not accept your token.")
    scrobble_commands.on_title(host, "Artist - Song", now=T0)
    _listen_for(host, 70)
    scrobble_commands.on_title(host, "Artist - Next", now=T0 + 80)
    _listen_for(host, 70, start=T0 + 80)
    assert len(host.said) == 1 and "did not accept your token" in host.said[0]
    queue = host._radio_scrobble.queue
    assert queue.pending("listenbrainz"), "the songs wait for a new sign-in"


def test_a_stopped_station_stops_the_clock(scrobbling_on: dict[str, Any]) -> None:
    host = scrobbling_on["host"]
    scrobble_commands.on_title(host, "Artist - Song", now=T0)
    _listen_for(host, 30)
    host._radio_controller.station = None
    scrobble_commands.tick(host, now=T0 + 35)
    host._radio_controller.station = _Station()
    _listen_for(host, 60, start=T0 + 40)
    assert scrobbling_on["batches"] == [], "the half-heard song is forgotten, not resumed"


def test_record_song_feeds_scrobbling_even_with_song_history_off(
    scrobbling_on: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.radio import song_history_commands

    host = scrobbling_on["host"]
    host._radio_history.song_history_enabled = False
    seen: list[str] = []
    monkeypatch.setattr(scrobble_commands, "on_title", lambda _h, title, **_k: seen.append(title))
    song_history_commands.record_song(host, "Artist - Song")
    assert seen == ["Artist - Song"]


# -- Sign in to last.fm ------------------------------------------------------------


def _fake_lastfm(monkeypatch: pytest.MonkeyPatch, *, session_error: int = 0) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(lastfm, "bundled_credentials", lambda: ("", ""))

    def _token(service: lastfm.Service, **kwargs: Any) -> str:
        calls.append(f"token:{service.id}:{kwargs['api_key']}")
        return "TOK"

    def _session(service: lastfm.Service, **kwargs: Any) -> tuple[str, str]:
        calls.append(f"session:{kwargs['token']}")
        if session_error:
            raise lastfm.LastFmError("not yet", error_code=session_error)
        return "jeff", "SESSIONKEY"

    monkeypatch.setattr(lastfm, "get_token", _token)
    monkeypatch.setattr(lastfm, "get_session", _session)
    monkeypatch.setattr(scrobble_signin.webbrowser, "open", lambda url: calls.append(url) or True)
    return calls


def test_sign_in_opens_the_page_waits_for_ok_and_keeps_the_session(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    calls = _fake_lastfm(monkeypatch)
    host = _Host()
    refreshed: list[bool] = []
    scrobble_signin.sign_in(
        host, lastfm.LASTFM, lambda: ("MYKEY", "MYSECRET"), after=lambda: refreshed.append(True)
    )
    assert calls[0] == "token:lastfm:MYKEY"
    assert calls[1] == "https://www.last.fm/api/auth/?api_key=MYKEY&token=TOK"
    assert "choose Yes, allow access" in host.boxes[0]
    assert radio_credential_store[radio_credentials.LASTFM_SESSION] == ("SESSIONKEY", "jeff")
    assert radio_credential_store[radio_credentials.LASTFM_API_KEY] == ("MYKEY", "")
    assert refreshed == [True]
    assert host.said[-1].startswith("Signed in to last.fm as jeff.")


def test_sign_in_without_any_api_key_explains_and_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_lastfm(monkeypatch)
    host = _Host()
    scrobble_signin.sign_in(host, lastfm.LIBREFM, lambda: ("", ""))
    assert calls == []
    assert host.boxes == [lastfm.NO_APP_KEY]


def test_cancelling_the_wait_keeps_nothing(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    calls = _fake_lastfm(monkeypatch)
    host = _Host()
    host.box_answer = _Wx.CANCEL
    scrobble_signin.sign_in(host, lastfm.LASTFM, lambda: ("K", "S"))
    assert not any(call.startswith("session:") for call in calls)
    assert radio_credentials.LASTFM_SESSION not in radio_credential_store
    assert host.said[-1] == "Signing in to last.fm cancelled."


def test_coming_back_before_saying_yes_says_what_to_do(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    _fake_lastfm(monkeypatch, session_error=lastfm.NOT_AUTHORISED_CODE)
    host = _Host()
    scrobble_signin.sign_in(host, lastfm.LASTFM, lambda: ("K", "S"))
    assert "has not been told yes yet" in host.said[-1]
    assert radio_credentials.LASTFM_SESSION not in radio_credential_store


def test_pressing_sign_in_while_signed_in_offers_sign_out_no_by_default(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    calls = _fake_lastfm(monkeypatch)
    radio_credential_store[radio_credentials.LIBREFM_SESSION] = ("S", "jeff")
    host = _Host()
    host.box_answer = _Wx.NO
    scrobble_signin.sign_in(host, lastfm.LIBREFM, lambda: ("K", "S"))
    assert "signed in to Libre.fm as jeff" in host.boxes[0]
    assert radio_credentials.LIBREFM_SESSION in radio_credential_store and calls == []
    host.box_answer = _Wx.YES
    scrobble_signin.sign_in(host, lastfm.LIBREFM, lambda: ("K", "S"))
    assert radio_credentials.LIBREFM_SESSION not in radio_credential_store
    assert host.said[-1] == "Signed out of Libre.fm."


# -- Preferences ---------------------------------------------------------------------


class _App(_Host):
    pass


def test_every_new_row_has_help_and_no_access_key() -> None:
    rows = prefs.ScrobbleRows(_App())
    specs = [*rows.checkboxes(), rows.choice(), *rows.texts(), *rows.actions()]
    assert len(specs) == 11
    for spec in specs:
        assert spec.help_text.strip(), spec.name
        assert "&" not in spec.name, "this dialog has no letter left (GATE-14)"
        assert "tick" not in spec.help_text.lower(), "check boxes are checked, never ticked"


def test_everything_is_off_by_default() -> None:
    history = RadioHistory()
    assert not (
        history.scrobble_listenbrainz or history.scrobble_lastfm or history.scrobble_librefm
    )
    assert history.recognition_service == "acoustid"
    rows = prefs.ScrobbleRows(_App())
    assert [spec.value for spec in rows.checkboxes()] == [False, False, False]
    assert rows.choice().selected_index == 0


def test_apply_saves_switches_and_tokens_and_says_what_is_missing(
    radio_credential_store: dict[str, Any],
) -> None:
    app = _App()
    rows = prefs.ScrobbleRows(app)
    said = rows.apply([True, True, False], 1, ["  LBTOKEN ", "", "", ""])
    history = app._radio_history
    assert (
        history.scrobble_listenbrainz and history.scrobble_lastfm and not history.scrobble_librefm
    )
    assert history.recognition_service == song_recognition.SERVICE_AUDD
    assert radio_credential_store[radio_credentials.LISTENBRAINZ_TOKEN] == ("LBTOKEN", "")
    assert "last.fm is on, but you have not signed in yet." in said
    assert "no AudD token yet" in said
    assert "ListenBrainz" not in said


def test_an_unchanged_dialog_writes_no_secret(
    monkeypatch: pytest.MonkeyPatch, radio_credential_store: dict[str, Any]
) -> None:
    radio_credential_store[radio_credentials.AUDD_TOKEN] = ("AUDD", "")
    app = _App()
    rows = prefs.ScrobbleRows(app)

    def _no_save(*_args: Any, **_kwargs: Any) -> bool:
        raise AssertionError("nothing changed, so nothing is written")

    monkeypatch.setattr(radio_credentials, "save", _no_save)
    assert rows.apply([False, False, False], 0, ["", "", "", "AUDD"]) == ""


def test_clearing_a_token_removes_it(radio_credential_store: dict[str, Any]) -> None:
    radio_credential_store[radio_credentials.AUDD_TOKEN] = ("AUDD", "")
    rows = prefs.ScrobbleRows(_App())
    rows.apply([False, False, False], 0, ["", "", "", ""])
    assert radio_credentials.AUDD_TOKEN not in radio_credential_store


def test_the_sign_in_button_reads_the_boxes_as_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Dialog:
        def text_value(self, index: int) -> str:
            return {4: "TYPEDKEY", 5: "TYPEDSECRET"}[index]

    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        scrobble_signin, "sign_in", lambda _app, _service, pair, **_k: seen.append(pair())
    )
    rows = prefs.ScrobbleRows(_App())
    rows.attach(_Dialog(), first_text_index=3)
    rows.sign_in(lastfm.LASTFM)
    assert seen == [("TYPEDKEY", "TYPEDSECRET")]


# -- Identify This Song with AudD -------------------------------------------------


class _Engine:
    def __init__(self) -> None:
        self.dumped: list[float] = []

    def dump_recent_audio(self, seconds: float, target: str) -> bool:
        self.dumped.append(seconds)
        Path(target).write_bytes(b"clip")
        return True


class _IdentifyController(_Controller):
    def __init__(self, engine: _Engine) -> None:
        super().__init__()
        self._mpv_engine = engine

    def _is_mpv_active(self) -> bool:
        return True


def test_identify_uses_audd_when_chosen_without_fpcalc(
    monkeypatch: pytest.MonkeyPatch, quill_data_dir: Path, radio_credential_store: dict[str, Any]
) -> None:
    from quill.core.radio import audd, chromaprint

    radio_credential_store[radio_credentials.AUDD_TOKEN] = ("AUDDTOKEN", "")
    monkeypatch.setattr(chromaprint, "find_fpcalc", lambda dirs=None: None)
    seen: dict[str, Any] = {}

    def _identify(token: str, sample: bytes, **_kwargs: Any) -> list[Any]:
        seen["token"], seen["sample"] = token, sample
        return audd.parse_answer(
            '{"status": "success", "result": {"artist": "A", "title": "Song", "album": ""}}'
        )

    monkeypatch.setattr(audd, "identify", _identify)
    engine = _Engine()
    host = _Host()
    host._radio_history.recognition_service = "audd"
    host._radio_controller = _IdentifyController(engine)
    song_identify_commands.identify_song(host)
    assert engine.dumped == [audd.SAMPLE_SECONDS]
    assert seen == {"token": "AUDDTOKEN", "sample": b"clip"}
    assert host.said[-1] == "AudD says: Song by A."


def test_identify_with_audd_and_no_token_says_where_to_get_one() -> None:
    from quill.core.radio import audd

    engine = _Engine()
    host = _Host()
    host._radio_history.recognition_service = "audd"
    host._radio_controller = _IdentifyController(engine)
    song_identify_commands.identify_song(host)
    assert host.said == [audd.NO_TOKEN_SENTENCE]
    assert engine.dumped == []
