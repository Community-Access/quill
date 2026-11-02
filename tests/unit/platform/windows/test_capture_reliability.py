"""Studio's sound capture survives what Windows does not report.

Each test drives the real source classes against fakes of the Windows and
PortAudio calls: a dead process, a screen reader restarted under a new
process ID, a sound card that goes away, a source in one ear, a device clock
at 48,010 Hz, a callback stall, one device that cannot be described, a
worker thread opening a stream, and a device that only accepts 44.1 kHz.
"""

from __future__ import annotations

import ctypes
import importlib.util
import threading
import time
from types import SimpleNamespace

import pytest

from quill.core.demo_recording import PreflightFacts, SoundSource
from quill.core.demo_recording_session import SegmentRecord, source_timing_summary
from quill.core.demo_recording_verify import timing_sentence
from quill.platform.windows import (
    capture_health,
    com_apartment,
    demo_audio,
    demo_devices,
    demo_microphone,
    process_loopback,
)
from quill.platform.windows.demo_audio import WavStream

needs_numpy = pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None, reason="numpy is not installed"
)
pytestmark = needs_numpy

STUDIO_PID = 4242


def wait_for(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def tone(frames, channels=2, left=8000, right=8000):
    import numpy as np

    data = np.zeros((frames, channels), dtype=np.int16)
    data[:, 0] = left
    if channels > 1:
        data[:, 1] = right
    return data.tobytes()


class FakeCapture:
    """IAudioCaptureClient: a 10 ms stereo tone packet every 10 ms."""

    def __init__(self, fail_after=None, frames=480):
        self.frames = frames
        self.buffer = ctypes.create_string_buffer(tone(frames))
        self.reads = 0
        self.fail_after = fail_after
        self.last = 0.0

    def GetNextPacketSize(self):  # noqa: N802 - COM name
        if self.fail_after is not None and self.reads >= self.fail_after:
            raise OSError("AUDCLNT_E_DEVICE_INVALIDATED")
        return self.frames if time.monotonic() - self.last >= 0.01 else 0

    def GetBuffer(self):  # noqa: N802
        self.reads += 1
        self.last = time.monotonic()
        return (ctypes.addressof(self.buffer), self.frames, 0, 0, 0)

    def ReleaseBuffer(self, _frames):  # noqa: N802
        return None


class FakeClient:
    def Stop(self):  # noqa: N802
        return None


@pytest.fixture
def fast(monkeypatch):
    """Short rescans and liveness polls, and no real COM activation."""
    monkeypatch.setattr(demo_audio, "RESCAN_S", 0.05)
    monkeypatch.setattr(demo_audio, "ALIVE_POLL_S", 0.02)
    monkeypatch.setattr(demo_audio, "EXCLUDED_POLL_S", 0.02)
    monkeypatch.setattr(process_loopback, "_POLL_S", 0.002)
    monkeypatch.setattr(process_loopback, "import_comtypes", lambda: None)
    living: set[int] = set()
    monkeypatch.setattr(process_loopback, "alive", lambda pid: pid in living)
    monkeypatch.setattr(demo_audio, "alive", lambda pid: pid in living)
    running: dict[str, int] = {}
    monkeypatch.setattr(
        demo_audio, "find_process", lambda name, avoid=0: running.get(name.lower(), 0)
    )
    opened: list[tuple[int, bool]] = []
    captures: list[FakeCapture] = []

    def fake_open(pid, *, exclude=False, rate=48_000, channels=2):
        if pid not in living:
            raise OSError("no such process")
        opened.append((pid, exclude))
        capture = FakeCapture()
        captures.append(capture)
        return FakeClient(), capture

    monkeypatch.setattr(process_loopback, "_open", fake_open)
    return SimpleNamespace(living=living, running=running, opened=opened, captures=captures)


def recorder_events():
    events: list[tuple[str, bool]] = []
    return events, lambda text, failure: events.append((text, failure))


# -- A2 / REC-019: a recorded program that quits ----------------------------------------


def test_dead_pid_ends_the_source_and_it_is_found_again(fast, tmp_path):
    fast.living.add(100)
    events, on_event = recorder_events()
    source = demo_audio.LoopbackSource(
        SoundSource("application", "Notepad sound", "app", process_id=100, process_name="App.exe"),
        on_event,
        studio_pid=STUDIO_PID,
    )
    source.begin_segment(tmp_path / "app.wav")
    assert source.open() == ""
    assert wait_for(lambda: fast.captures and fast.captures[0].reads > 3)
    fast.living.discard(100)  # the program quits; Windows says nothing
    assert wait_for(lambda: any(failure for _text, failure in events))
    assert events[0] == ("Notepad sound stopped: App.exe quit.", True)
    fast.living.add(200)
    fast.running["app.exe"] = 200
    assert wait_for(lambda: len(events) == 2)
    assert events[1] == ("Notepad sound found again and recording.", False)
    assert fast.opened[-1] == (200, False)
    source.close()
    source.end_segment(time.time())


def test_a_dead_pid_is_never_opened(fast):
    events, on_event = recorder_events()
    source = demo_audio.LoopbackSource(
        SoundSource("application", "Gone sound", "app", process_id=55, process_name="gone.exe"),
        on_event,
        studio_pid=STUDIO_PID,
    )
    assert source.open() == "gone.exe is not running"
    assert fast.opened == []


# -- A1 / MX-184: the excluded screen reader restarts ----------------------------------


def test_restarted_reader_is_muted_at_once_then_excluded_again(fast, tmp_path):
    fast.living.update({STUDIO_PID, 300})
    events, on_event = recorder_events()
    system = SoundSource(
        "system",
        "System sound",
        "system",
        exclude_process_id=300,
        exclude_name="nvda.exe",
    )
    source = demo_audio.LoopbackSource(system, on_event, studio_pid=STUDIO_PID)
    source.begin_segment(tmp_path / "system.wav")
    assert source.open() == ""
    assert fast.opened == [(300, True)]
    assert wait_for(lambda: fast.captures[0].reads > 3)
    fast.living.discard(300)  # NVDA restarts...
    assert wait_for(lambda: events)
    reads_at_gone = fast.captures[0].reads
    assert events[0] == (
        "System sound muted: nvda closed, so its speech is kept out until Studio finds it again.",
        True,
    )
    fast.living.add(301)  # ...under a new process ID
    fast.running["nvda.exe"] = 301
    assert wait_for(lambda: len(events) == 2)
    assert events[1] == ("System sound back, still without nvda.", False)
    assert fast.opened[-1] == (301, True)
    # Not one packet was taken from the capture that no longer excluded the reader.
    assert fast.captures[0].reads == reads_at_gone
    source.close()
    source.end_segment(time.time())


# -- A3 / REC-020: a sound card that is lost --------------------------------------------


def test_lost_sound_card_is_reopened_by_endpoint_id(fast, monkeypatch, tmp_path):
    endpoint = "{0.0.0.00000000}.{speakers}"
    attempts: list[str] = []

    def fake_endpoint(device_id, *, rate, channels):
        attempts.append(device_id)
        if 2 <= len(attempts) <= 3:  # unplugged for two rescans, then back
            raise OSError("element not found")
        capture = FakeCapture(fail_after=5 if len(attempts) == 1 else None)
        fast.captures.append(capture)
        return FakeClient(), capture

    monkeypatch.setattr(process_loopback, "_open_endpoint", fake_endpoint)
    monkeypatch.setattr(demo_audio, "_render_device_name", lambda _id: "Speakers (USB Audio)")
    events, on_event = recorder_events()
    source = demo_audio.LoopbackSource(
        SoundSource("device", "Everything playing on Speakers", "added-speakers", device=endpoint),
        on_event,
        studio_pid=STUDIO_PID,
    )
    source.begin_segment(tmp_path / "card.wav")
    assert source.open() == ""
    assert wait_for(lambda: events)
    assert events[0] == (
        "Everything playing on Speakers stopped: the sound card Speakers (USB Audio) was lost "
        "or changed.",
        True,
    )
    assert wait_for(lambda: len(events) == 2)
    assert events[1] == (
        "Everything playing on Speakers: Speakers (USB Audio) is back and recording.",
        False,
    )
    assert set(attempts) == {endpoint} and len(attempts) == 4
    assert len([e for e in events if e[1]]) == 1  # one failure line, not one per retry
    source.close()
    source.end_segment(time.time())


# -- A4 / MX-185, REC-021: channels -------------------------------------------------------


def test_a_left_only_source_is_reported_and_a_centred_one_is_not(tmp_path):
    left = WavStream(tmp_path / "left.wav")
    left.write(tone(4800, left=8000, right=0), 1.0)
    left.finish(1.1)
    assert left.one_ear() == "left"
    centred = WavStream(tmp_path / "centred.wav")
    centred.write(tone(4800), 1.0)
    centred.finish(1.1)
    assert centred.one_ear() == ""
    from quill.core.demo_recording import DemoPlan
    from quill.core.demo_recording_rules import sound_findings

    plan = DemoPlan(
        "desktop",
        "Desktop",
        (0, 0, 0, 0),
        "",
        sources=(SoundSource("system", "S", "s", enabled=True),),
    )
    warnings: list[str] = []
    facts = PreflightFacts(one_ear={"s": "S is only in the left ear."})
    sound_findings(plan, facts, lambda text: None, warnings.append)
    assert "S is only in the left ear." in warnings


def test_mono_input_is_centred_and_input_choice_is_honoured():
    import numpy as np

    samples = np.array([[1000, 0], [1000, 0]], dtype=np.int16)
    assert list(demo_microphone.pick_channels(samples, "mix")) == [500.0, 500.0]
    assert list(demo_microphone.pick_channels(samples, "1")) == [1000.0, 1000.0]
    assert list(demo_microphone.pick_channels(samples, "2")) == [0.0, 0.0]


# -- A5 / REC-022: drift, not outages -----------------------------------------------------


@pytest.mark.parametrize("true_rate", [48_010, 47_990])
def test_a_drifting_clock_is_measured_not_patched_with_silence(tmp_path, true_rate):
    stream = WavStream(tmp_path / "drift.wav", channels=1)
    packet = 4_800
    payload = tone(packet, channels=1)
    t0 = 1000.0
    count = 600  # one minute of sound at the nominal rate
    for index in range(count):
        # The device stamps each packet by its own clock: 4,800 samples take
        # 4,800 / true_rate real seconds.
        stream.write(payload, t0 + index * packet / true_rate)
    end = t0 + count * packet / true_rate
    stream.finish(end)
    assert stream.filled_frames == 0
    timing = stream.timing()
    assert timing["measured_frames"] == packet * count
    assert timing["drift_ratio"] == pytest.approx(true_rate / 48_000, rel=1e-5)
    assert abs(timing["drift_ms"]) == pytest.approx(abs(true_rate - 48_000) / 48_000 * 60_000, 0.05)


def test_a_real_outage_is_still_filled(tmp_path):
    stream = WavStream(tmp_path / "gap.wav", channels=1)
    stream.write(tone(480, channels=1), 10.0)
    stream.write(tone(480, channels=1), 11.01)  # a second with nothing at all
    stream.finish(11.02)
    assert stream.filled_frames == pytest.approx(48_000, abs=10)
    assert stream.timing()["drift_ratio"] == pytest.approx(1.0, abs=1e-3)


def test_timing_reaches_the_session_and_the_report():
    segments = [
        SegmentRecord(
            1,
            "a",
            audio_timing={
                "mic": {
                    "measured_frames": 480_100.0,
                    "expected_frames": 480_000.0,
                    "monotonic_seconds": 10.0,
                    "drift_ratio": 1.0002,
                    "stall_count": 1.0,
                }
            },
        ),
        SegmentRecord(
            2,
            "b",
            audio_timing={
                "mic": {
                    "measured_frames": 480_100.0,
                    "expected_frames": 480_000.0,
                    "monotonic_seconds": 10.0,
                    "drift_ratio": 1.0002,
                    "stall_count": 2.0,
                }
            },
        ),
    ]
    rows = source_timing_summary(segments, {"mic": "Microphone"})
    assert rows[0]["drift_ratio"] == pytest.approx(960_200 / 960_000)
    assert rows[0]["stall_count"] == 2
    assert rows[0]["segment_drift_ratios"] == [1.0002, 1.0002]
    assert timing_sentence(rows[0]).startswith("Microphone: 960200 samples over 20.0 seconds")


# -- the microphone, through a fake PortAudio ---------------------------------------------


class FakeStream:
    def __init__(self, sd, **settings):
        self.sd = sd
        self.settings = settings
        self.callback = settings["callback"]
        self.active = False
        self.closed = False
        self.thread = threading.get_ident()

    def start(self):
        if self.sd.refuse(self.settings):
            raise RuntimeError(f"Invalid sample rate {self.settings['samplerate']}")
        self.active = True
        self.sd.streams.append(self)

    def stop(self):
        self.active = False

    def close(self):
        self.closed = True

    def feed(self, payload, frames):
        self.callback(payload, frames, SimpleNamespace(inputBufferAdcTime=0, currentTime=0), None)


class FakeSd:
    def __init__(self, devices, refuse=lambda settings: False):
        self.devices = devices
        self.apis = ["MME", "Windows DirectSound", "Windows WASAPI", "ASIO"]
        self.refuse = refuse
        self.streams: list[FakeStream] = []
        self.default = SimpleNamespace(device=(0, 0))
        self._lib = SimpleNamespace(Pa_GetDeviceCount=lambda: len(self.devices))

    def query_hostapis(self):
        return [{"name": name} for name in self.apis]

    def query_devices(self, index):
        device = self.devices[index]
        if isinstance(device, Exception):
            raise device
        return device

    def RawInputStream(self, **settings):  # noqa: N802
        return FakeStream(self, **settings)

    def WasapiSettings(self, auto_convert):  # noqa: N802
        return ("wasapi", auto_convert)


def _device(name, api, channels=2, rate=48_000.0):
    apis = {"MME": 0, "Windows DirectSound": 1, "Windows WASAPI": 2, "ASIO": 3}
    return {
        "name": name,
        "hostapi": apis[api],
        "max_input_channels": channels,
        "default_samplerate": rate,
    }


@pytest.fixture
def fake_sd(monkeypatch):
    def install(devices, refuse=lambda settings: False):
        sd = FakeSd(devices, refuse)
        monkeypatch.setattr(demo_devices, "_sd", lambda: sd)
        monkeypatch.setattr(demo_microphone, "_sd", lambda: sd)
        monkeypatch.setattr(demo_devices, "_capture_endpoints", lambda: {})
        return sd

    return install


def _mic(on_event, device="USB Interface", mode="mix", endpoint=""):
    return demo_microphone.MicrophoneSource(
        SoundSource(
            "microphone",
            "Microphone",
            "microphone",
            device=device,
            channel_mode=mode,
            endpoint_id=endpoint,
        ),
        on_event,
    )


def test_one_bad_device_name_leaves_the_others_listed(fake_sd):
    fake_sd([
        _device("Headset (WASAPI)", "Windows WASAPI", 1),
        UnicodeDecodeError("utf-8", b"\x92", 0, 1, "invalid start byte"),
        _device("USB Interface", "Windows WASAPI"),
    ])
    names = [mic.name for mic in demo_devices.list_microphones()]
    assert names == ["Headset (WASAPI)", "USB Interface"]


def test_input_one_only_is_recorded_in_both_ears_and_reported(fake_sd, tmp_path):
    import wave

    sd = fake_sd([_device("USB Interface", "Windows WASAPI")])
    events, on_event = recorder_events()
    mic = _mic(on_event)
    mic.begin_segment(tmp_path / "mic.wav")
    assert mic.open() == ""
    stream = sd.streams[-1]
    assert stream.settings["channels"] == 2
    for _ in range(20):
        stream.feed(tone(960, left=8000, right=0), 960)
    assert wait_for(lambda: mic.stream.frames >= 960 * 20)
    assert mic.input_balance() == "1"
    mic.close()
    mic.end_segment(time.time())
    with wave.open(str(tmp_path / "mic.wav"), "rb") as handle:
        assert handle.getnchannels() == 1  # one centred channel: both ears in the mix


def test_a_stalled_callback_is_spoken_once_and_counted(fake_sd, monkeypatch, tmp_path):
    monkeypatch.setattr(demo_microphone, "LOST_AFTER_S", 30.0)
    sd = fake_sd([_device("USB Interface", "Windows WASAPI", 1)])
    events, on_event = recorder_events()
    mic = _mic(on_event)
    mic.begin_segment(tmp_path / "mic.wav")
    assert mic.open() == ""
    stream = sd.streams[-1]
    for _stall in range(2):
        stream.feed(tone(960, channels=1), 960)
        time.sleep(1.0)  # active, but no callback for a second
        stream.feed(tone(960, channels=1), 960)
        time.sleep(0.1)
    mic.close()
    mic.end_segment(time.time())
    stalls = [text for text, _failure in events if "no sound arrived" in text]
    assert stalls == ["Microphone is losing audio: no sound arrived for over half a second."]
    assert mic.glitches.counts["stall"] == 2


def test_a_device_that_only_takes_44_1_khz_is_resampled_to_48(fake_sd, tmp_path):
    sd = fake_sd(
        [_device("ASIO Interface", "ASIO", 1, rate=44_100.0)],
        refuse=lambda settings: settings["samplerate"] != 44_100,
    )
    events, on_event = recorder_events()
    mic = _mic(on_event, device="ASIO Interface (ASIO)")
    mic.begin_segment(tmp_path / "mic.wav")
    assert mic.open() == ""
    assert (mic.api, mic.rate) == ("ASIO", 44_100)
    assert ("Microphone opened through ASIO at 44100 hertz.", False) in events
    stream = sd.streams[-1]
    for _ in range(50):
        stream.feed(tone(882, channels=1), 882)  # one second at 44.1 kHz
    assert wait_for(lambda: mic.stream.frames >= 47_900)
    mic.close()
    written = mic.stream.frames
    mic.end_segment(time.time())
    assert written == pytest.approx(48_000, abs=40)


def test_a_busy_wasapi_device_falls_back_to_directsound_as_the_same_device(fake_sd):
    sd = fake_sd(
        [
            _device("Microphone (USB Mic)", "Windows WASAPI", 1),
            _device("Microphone (USB Mic)", "Windows DirectSound", 1),
            _device("Other Mic", "Windows DirectSound", 1),
        ],
        refuse=lambda settings: settings["device"] == 0,
    )
    events, on_event = recorder_events()
    mic = _mic(on_event, device="Microphone (USB Mic)")
    assert mic.open() == ""
    mic.close()
    mic.end_segment(time.time())
    assert sd.streams[-1].settings["device"] == 1
    assert ("Microphone opened through DirectSound at 48000 hertz.", False) in events


def test_nothing_opens_and_every_attempt_is_named(fake_sd):
    fake_sd([_device("USB Interface", "MME", 1, rate=96_000.0)], refuse=lambda _s: True)
    mic = _mic(lambda *_a: None)
    error = mic.open()
    mic.close()
    mic.end_segment(time.time())
    assert "tried MME at 48000 hertz, MME at 44100 hertz, MME at 96000 hertz" in error


# -- A11 / MX-114: identity first ---------------------------------------------------------


def test_endpoint_id_wins_and_a_name_only_match_is_said(fake_sd, monkeypatch):
    fake_sd([_device("Microphone (USB Mic)", "Windows WASAPI", 1)])
    monkeypatch.setattr(
        demo_devices, "_capture_endpoints", lambda: {"Microphone (USB Mic)": "{id-new}"}
    )
    mic, note = demo_devices.resolve_saved_microphone("Microphone (USB Mic)", "{id-new}")
    assert (mic.name, note) == ("Microphone (USB Mic)", "")
    mic, note = demo_devices.resolve_saved_microphone("Microphone (USB Mic)", "{id-old}")
    assert mic is not None and "was not found by its Windows identity" in note
    mic, note = demo_devices.resolve_saved_microphone("Something Else", "{id-old}")
    assert mic is None


# -- A9 / MX-188: the MTA -----------------------------------------------------------------


class FakeOle32:
    def __init__(self, answer=0):
        self.answer = answer
        self.calls: list[tuple[str, int]] = []

    def CoInitializeEx(self, _reserved, flags):  # noqa: N802
        self.calls.append(("init", threading.get_ident()))
        assert flags == com_apartment.COINIT_MULTITHREADED
        return self.answer

    def CoUninitialize(self):  # noqa: N802
        self.calls.append(("uninit", threading.get_ident()))


def test_the_stream_is_opened_on_a_thread_that_joined_the_mta(fake_sd, monkeypatch):
    ole32 = FakeOle32()
    monkeypatch.setattr(com_apartment, "_ole32", lambda: ole32)
    sd = fake_sd([_device("USB Interface", "Windows WASAPI", 1)])
    mic = _mic(lambda *_a: None)
    assert mic.open() == ""  # called from this (test) thread...
    opener = sd.streams[-1].thread
    mic.close()
    mic.end_segment(time.time())
    assert opener != threading.get_ident()  # ...but opened on the source's own thread
    assert ("init", opener) in ole32.calls
    assert ole32.calls.index(("init", opener)) < ole32.calls.index(("uninit", opener))


def test_an_apartment_this_thread_did_not_open_is_never_uninitialised(monkeypatch):
    ole32 = FakeOle32(answer=0x80010106)  # RPC_E_CHANGED_MODE: already single-threaded
    monkeypatch.setattr(com_apartment, "_ole32", lambda: ole32)
    with com_apartment.mta() as joined:
        assert joined is False
    assert [kind for kind, _thread in ole32.calls] == ["init"]


# -- the pieces ---------------------------------------------------------------------------


def test_alive_reads_the_exit_code(monkeypatch):
    class Kernel32:
        def __init__(self, code):
            self.code = code

        def OpenProcess(self, *_a):  # noqa: N802
            return 7

        def GetExitCodeProcess(self, _handle, pointer):  # noqa: N802
            pointer._obj.value = self.code
            return 1

        def CloseHandle(self, _handle):  # noqa: N802
            return 1

    monkeypatch.setattr(capture_health, "_kernel32", lambda: Kernel32(259))
    assert capture_health.alive(10) is True
    monkeypatch.setattr(capture_health, "_kernel32", lambda: Kernel32(0))
    assert capture_health.alive(10) is False
    assert capture_health.alive(0) is False


def test_the_first_of_each_glitch_is_said_once():
    events, on_event = recorder_events()
    counter = capture_health.GlitchCounter("System sound", on_event)
    for kind in ("discontinuity", "discontinuity", "overflow"):
        counter.count(kind)
    assert [text for text, _f in events] == [
        "System sound is losing audio: Windows reported a gap in the sound.",
        "System sound is losing audio: the input overflowed.",
    ]
    assert counter.as_dict() == {"discontinuity_count": 2, "overflow_count": 1, "stall_count": 0}


def test_resampling_in_blocks_matches_resampling_whole_and_keeps_pitch():
    import numpy as np

    from quill.platform.windows.capture_timing import StreamResampler

    rate = 44_100
    signal = (8000 * np.sin(2 * np.pi * 1000 * np.arange(rate) / rate)).astype(np.int16)
    whole = StreamResampler(rate).process(signal.reshape(-1, 1))
    pieces = StreamResampler(rate)
    sizes = [441, 7, 1000, 2205, 13]
    parts, start, turn = [], 0, 0
    while start < rate:
        size = sizes[turn % len(sizes)]
        parts.append(pieces.process(signal[start : start + size].reshape(-1, 1)))
        start += size
        turn += 1
    blockwise = np.concatenate(parts)
    assert np.array_equal(whole, blockwise)  # no clicks at block edges
    spectrum = np.abs(np.fft.rfft(whole[:48_000, 0].astype(np.float64)))
    assert abs(int(np.argmax(spectrum)) * 48_000 / len(whole[:48_000]) - 1000) < 2
