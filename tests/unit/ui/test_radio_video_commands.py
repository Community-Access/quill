"""Showing a picture, and every time the app declines instead.

The refusals are the point. Video is a *view onto* playback, never a mode of it,
so nothing here may ever stop, restart or interrupt the audio -- and nothing is
ever greyed out: each command says why it declined, because a disabled item
teaches nothing.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import video_commands


class _Engine:
    """An mpv engine, minus mpv."""

    def __init__(
        self, *, size: tuple[int, int] | None = (1280, 720), attaches: bool = True
    ) -> None:
        self._size = size
        self._attaches = attaches
        self.attached: list[Any] = []
        self.audio_files: list[str] = []
        self.subtitles: list[str] = []
        self.visible: list[bool] = []
        self.styles: list[Any] = []
        self.brightness: list[int] = []
        self.snapshots: list[str] = []

    def attach_video(self, handle: int | None) -> bool:
        self.attached.append(handle)
        return self._attaches

    def set_audio_file(self, url: str) -> bool:
        self.audio_files.append(url)
        return True

    def video_size(self) -> tuple[int, int] | None:
        return self._size

    def add_subtitles(self, url: str) -> bool:
        self.subtitles.append(url)
        return True

    def set_subtitles_visible(self, visible: bool) -> bool:
        self.visible.append(visible)
        return True

    def apply_caption_style(self, style: Any) -> bool:
        self.styles.append(style)
        return True

    def set_brightness(self, percent: int) -> bool:
        self.brightness.append(percent)
        return True

    def take_snapshot(self, path: str) -> bool:
        self.snapshots.append(path)
        return True


class _WxEngine:
    """The classic backend: no video story at all."""


class _Stream:
    def __init__(self, *, video: bool = True) -> None:
        self.title = "A Lecture"
        self.stream_url = "https://audio"
        self.video_url = "https://video" if video else ""
        self.video_width = 1920 if video else 0
        self.video_height = 1080 if video else 0
        self.video_fps = 30.0
        self.video_codec = "avc1"


class _Controller:
    def __init__(self, engine: Any, stream: Any, *, captions: str = "", automatic: bool = False):
        self._engine = engine
        self._youtube_stream = stream
        self._captions = (captions, automatic)

    def caption_track(self) -> tuple[str, bool]:
        return self._captions

    def audio_tracks(self) -> list:
        return []

    def selected_audio_track(self) -> Any:
        return None

    def is_seekable(self) -> bool:
        return True

    def position_ms(self) -> int:
        return 0

    def duration_ms(self) -> int:
        return 1000


class _Window:
    """Stands in for the Video Window."""

    def __init__(self, handle: int | None = 4242) -> None:
        self._handle = handle
        self.closed = False
        self.status = ""
        self.sized: list[tuple[int, int]] = []
        self.full_screen = False

    def handle(self) -> int | None:
        return self._handle

    def show(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    def set_status(self, text: str) -> None:
        self.status = text

    def resize_to(self, width: int, height: int) -> None:
        self.sized.append((width, height))

    def toggle_full_screen(self) -> bool:
        self.full_screen = not self.full_screen
        return self.full_screen


class _Tasks:
    """Runs submitted work immediately, so a test reads top to bottom."""

    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any = None, on_failure: Any = None):
        self.submitted.append(name)
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001 - mirrors the task manager
            if on_failure is not None:
                on_failure(name, exc)
            return
        if on_success is not None:
            on_success(name, result)


class _Host:
    def __init__(self, engine: Any = None, stream: Any = None, **kwargs: Any) -> None:
        self._radio_controller = (
            _Controller(engine, stream, **kwargs) if engine is not None else None
        )
        self.frame = object()
        self.said: list[str] = []
        self._video_window: Any = None
        self._captions_window: Any = None
        self._task_manager = _Tasks()

    def _announce(self, message: str) -> None:
        self.said.append(message)


class _Cue:
    def __init__(self, start_ms: int, text: str) -> None:
        self.start_ms = start_ms
        self.end_ms = start_ms + 1000
        self.text = text


class _CaptionsWindow:
    """Stands in for the Captions window."""

    def __init__(self, host: Any, cues: list, automatic: bool) -> None:
        self.host = host
        self.cues = cues
        self.automatic = automatic
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _fake_captions_window(monkeypatch: Any, cues: list | None = None) -> list:
    """Replace the real window and the fetch; return the windows opened."""
    from quill.core.podcasts import transcripts as transcripts_module

    opened: list[_CaptionsWindow] = []
    rows = cues if cues is not None else [_Cue(0, "Hello"), _Cue(2000, "World")]
    monkeypatch.setattr(transcripts_module, "fetch_transcript_cues", lambda _url, _mime: list(rows))

    def _open(host: Any, found: list, *, automatic: bool) -> None:
        window = _CaptionsWindow(host, found, automatic)
        host._captions_window = window
        opened.append(window)
        host._announce(
            "Captions on, in the Captions window. These are automatic captions, so expect mistakes."
            if automatic
            else "Captions on, in the Captions window."
        )

    monkeypatch.setattr(video_commands, "_open_captions_window", _open)
    return opened


def test_the_classic_engine_says_video_needs_mpv() -> None:
    host = _Host(_WxEngine(), _Stream())
    video_commands.toggle_video(host)
    assert video_commands.NEEDS_MPV in host.said


def test_hiding_the_picture_never_touches_the_audio() -> None:
    # The whole design: video is a view onto playback, not a mode of it.
    engine = _Engine()
    host = _Host(engine, _Stream())
    host._video_window = _Window()
    video_commands.hide_video(host)

    assert engine.attached == [None]  # detached, and nothing else called
    assert engine.audio_files == []
    assert host._video_window is None
    assert video_commands.HIDDEN in host.said


def test_stopping_playback_closes_the_window_silently() -> None:
    engine = _Engine()
    host = _Host(engine, _Stream())
    window = _Window()
    host._video_window = window

    video_commands.close_for_stop(host)

    assert window.closed and host._video_window is None
    # The stop already spoke; a second announcement would be noise.
    assert host.said == []


def test_a_station_with_no_video_says_so() -> None:
    host = _Host(_Engine(), None)
    video_commands.toggle_video(host)
    assert video_commands.NO_VIDEO in host.said


def test_a_video_with_no_captions_says_so_rather_than_greying_out() -> None:
    host = _Host(_Engine(), _Stream(), captions="")
    video_commands.toggle_captions(host)
    assert any("no captions published" in m for m in host.said)


def test_automatic_captions_are_announced_as_automatic(monkeypatch) -> None:
    engine = _Engine()
    host = _Host(engine, _Stream(), captions="https://cc", automatic=True)
    _fake_captions_window(monkeypatch)

    video_commands.toggle_captions(host)

    assert engine.subtitles == ["https://cc"]
    assert any("automatic captions, so expect mistakes" in m for m in host.said)


def test_written_captions_are_not_called_automatic(monkeypatch) -> None:
    host = _Host(_Engine(), _Stream(), captions="https://cc", automatic=False)
    _fake_captions_window(monkeypatch)

    video_commands.toggle_captions(host)

    assert "Captions on, in the Captions window." in host.said
    assert not any("automatic" in m for m in host.said)


def test_captions_toggle_off_again(monkeypatch) -> None:
    engine = _Engine()
    host = _Host(engine, _Stream(), captions="https://cc")
    opened = _fake_captions_window(monkeypatch)

    video_commands.toggle_captions(host)
    video_commands.toggle_captions(host)

    assert "Captions off." in host.said
    assert engine.visible[-1] is False
    assert opened[0].closed and host._captions_window is None


# -- captions you can read ---------------------------------------------------------


def test_captions_open_a_window_with_the_fetched_lines(monkeypatch) -> None:
    """Reported 2026-08-23: captions went into the picture and nowhere else.

    mpv draws them as pixels -- unreadable by a screen reader, unreachable by a
    braille display, and invisible to anyone listening without the Video Window
    open, which is most people here.
    """
    host = _Host(_Engine(), _Stream(), captions="https://cc")
    opened = _fake_captions_window(monkeypatch, [_Cue(0, "One"), _Cue(1000, "Two")])

    video_commands.toggle_captions(host)

    assert len(opened) == 1
    assert [c.text for c in opened[0].cues] == ["One", "Two"]
    assert host._captions_window is opened[0]


def test_captions_do_not_need_mpv_or_a_picture(monkeypatch) -> None:
    """The readable half works on the classic engine, audio-only.

    This is the case the old implementation refused outright ("Video needs the
    mpv playback engine"), which meant captions were unavailable to anyone not
    watching a picture -- the opposite of who captions in a window are for.
    """
    host = _Host(_WxEngine(), _Stream(), captions="https://cc")
    opened = _fake_captions_window(monkeypatch)

    video_commands.toggle_captions(host)

    assert opened, "captions refused without mpv"
    assert video_commands.NEEDS_MPV not in host.said


def test_closing_the_captions_window_turns_captions_off(monkeypatch) -> None:
    engine = _Engine()
    host = _Host(engine, _Stream(), captions="https://cc")
    _fake_captions_window(monkeypatch)
    video_commands.toggle_captions(host)

    video_commands._captions_window_closed(host)

    assert host._captions_window is None
    assert host._captions_on is False
    assert engine.visible[-1] is False
    assert "Captions off." in host.said


def test_a_caption_track_that_cannot_be_read_says_so(monkeypatch) -> None:
    from quill.core.podcasts import transcripts as transcripts_module

    monkeypatch.setattr(transcripts_module, "fetch_transcript_cues", lambda _u, _m: [])
    host = _Host(_Engine(), _Stream(), captions="https://cc")

    video_commands.toggle_captions(host)

    assert any("none could be read" in m for m in host.said)


def test_dimming_is_clamped_and_spoken() -> None:
    # For light sensitivity and migraine triggers: flashing cannot be detected
    # before it plays, so control is the honest answer rather than a claim.
    engine = _Engine()
    host = _Host(engine, _Stream())
    video_commands.dim_video(host, -300)
    assert engine.brightness == [-100]
    assert any("dimmed by 100%" in m for m in host.said)

    video_commands.dim_video(host, 0)
    assert any("normal brightness" in m for m in host.said)


def test_a_snapshot_needs_a_picture_and_says_so() -> None:
    host = _Host(_Engine(), _Stream())
    video_commands.take_snapshot(host)
    assert any("no picture to snapshot" in m for m in host.said)


def test_resizing_without_a_window_says_so() -> None:
    host = _Host(_Engine(), _Stream())
    video_commands.set_video_size(host, 200)
    assert any("no picture to resize" in m for m in host.said)


def test_resizing_scales_the_reported_picture() -> None:
    engine = _Engine(size=(1280, 720))
    host = _Host(engine, _Stream())
    window = _Window()
    host._video_window = window

    video_commands.set_video_size(host, 50)

    assert window.sized == [(640, 360)]
    assert any("Video at 50%, 640 by 360" in m for m in host.said)


def test_full_screen_without_a_window_says_so() -> None:
    host = _Host(_Engine(), _Stream())
    video_commands.toggle_full_screen(host)
    assert any("no picture to show full screen" in m for m in host.said)


def test_video_information_reports_the_two_accessibility_facts() -> None:
    host = _Host(_Engine(), _Stream(), captions="https://cc")
    video_commands.video_information(host)
    assert any("Captions are available" in m for m in host.said)
    assert any("No described audio was published" in m for m in host.said)


# -- the feature announcing itself ------------------------------------------------


def test_described_audio_announces_itself_once_per_video() -> None:
    """Without this, the feature only helps people who already know it exists."""
    from quill.core.radio.audio_tracks import AudioTrack
    from quill.ui.radio import track_selection

    class _Station:
        stream_url = "https://video/1"
        name = "A Lecture"

    class _State:
        station = _Station()

    class _Ctrl:
        state = _State()
        _youtube_stream = type(
            "_S",
            (),
            {"audio_tracks": (AudioTrack("1", "en", ""), AudioTrack("2", "en", "descriptive"))},
        )()

    class _Frame:
        def __init__(self) -> None:
            self._radio_controller = _Ctrl()
            self.said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    frame = _Frame()
    assert track_selection.announce_described_if_new(frame) is True
    assert track_selection.DESCRIBED_AVAILABLE in frame.said
    assert "Ctrl+Alt+D" in frame.said[0]

    # Once. A repeat on every state change would be unbearable.
    assert track_selection.announce_described_if_new(frame) is False
    assert len(frame.said) == 1


def test_a_video_without_described_audio_says_nothing() -> None:
    from quill.core.radio.audio_tracks import AudioTrack
    from quill.ui.radio import track_selection

    class _Ctrl:
        state = type("_St", (), {"station": type("_S", (), {"stream_url": "u"})()})()
        _youtube_stream = type("_S", (), {"audio_tracks": (AudioTrack("1", "en", ""),)})()

    class _Frame:
        _radio_controller = _Ctrl()
        said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    frame = _Frame()
    assert track_selection.announce_described_if_new(frame) is False
    assert frame.said == []
