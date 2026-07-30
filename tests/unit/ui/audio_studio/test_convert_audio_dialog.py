"""Tests for the Convert Audio dialog orchestration + contract (#1255 v1)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.audio.convert import Channels, ConversionJob, ConversionSpec, OnExisting
from quill.core.audio.dsp import DspOptions
from quill.ui.audio_studio import convert_audio_dialog as cad

_UI = Path(__file__).resolve().parents[4] / "quill" / "ui"


# --------------------------------------------------------------------------- #
# build_request (pure)
# --------------------------------------------------------------------------- #


def test_build_request_applies_preset_and_format_override() -> None:
    req = cad.build_request(
        [(Path("a.wav"), None)],
        fmt="flac",
        preset_id="mp3_320",
        dest_dir=Path("out"),
        recurse=True,
        on_existing=OnExisting.RENAME,
    )
    assert req is not None
    # Format choice overrides the preset's format; preset's other options remain.
    assert req.spec.fmt == "flac"
    assert req.spec.bitrate_kbps == 320
    assert req.recurse is True
    assert req.on_existing is OnExisting.RENAME


def test_build_request_mono_preset_carries_channels() -> None:
    req = cad.build_request(
        [(Path("a.wav"), None)],
        fmt="mp3",
        preset_id="podcast",
        dest_dir=Path("out"),
        recurse=False,
        on_existing=OnExisting.RENAME,
    )
    assert req is not None and req.spec.channels is Channels.MONO


def test_build_request_none_without_inputs() -> None:
    assert (
        cad.build_request(
            [],
            fmt="mp3",
            preset_id="just_convert",
            dest_dir=Path("out"),
            recurse=False,
            on_existing=OnExisting.RENAME,
        )
        is None
    )


def test_build_request_none_without_destination() -> None:
    assert (
        cad.build_request(
            [(Path("a.wav"), None)],
            fmt="mp3",
            preset_id="just_convert",
            dest_dir=Path(""),
            recurse=False,
            on_existing=OnExisting.RENAME,
        )
        is None
    )


# --------------------------------------------------------------------------- #
# apply_advanced (pure)
# --------------------------------------------------------------------------- #


def test_apply_advanced_none_leaves_preset_untouched() -> None:
    base = ConversionSpec(fmt="mp3", bitrate_kbps=192, channels=Channels.MONO)
    out = cad.apply_advanced(base)  # all-neutral == a no-op
    assert out.bitrate_kbps == 192
    assert out.channels is Channels.MONO
    assert out.filters == base.filters


def test_apply_advanced_overrides_only_what_is_set() -> None:
    base = ConversionSpec(fmt="mp3", bitrate_kbps=192, channels=Channels.STEREO)
    out = cad.apply_advanced(base, bitrate_kbps=320, sample_rate=48000)
    assert out.bitrate_kbps == 320
    assert out.sample_rate == 48000
    assert out.channels is Channels.STEREO  # untouched


def test_apply_advanced_dsp_populates_filters() -> None:
    base = ConversionSpec(fmt="mp3")
    out = cad.apply_advanced(base, dsp=DspOptions(high_pass=True, loudness="podcast"))
    assert any("highpass" in f for f in out.filters)
    assert any("loudnorm" in f for f in out.filters)


def test_advanced_choice_tables_start_neutral() -> None:
    # Index 0 of every Advanced table is the "keep preset/source" sentinel.
    assert cad._BITRATE_CHOICES[0][0] == ""
    assert cad._RATE_CHOICES[0][0] == ""
    assert cad._DEPTH_CHOICES[0][0] == ""
    assert cad._CHANNEL_CHOICES[0][0] is Channels.KEEP


# --------------------------------------------------------------------------- #
# plan_and_run (fake host)
# --------------------------------------------------------------------------- #


def _host() -> SimpleNamespace:
    calls: dict = {"status": [], "announce": [], "msgbox": [], "bg": None}
    return SimpleNamespace(
        frame=object(),
        _wx=SimpleNamespace(CallAfter=lambda fn, *a: fn(*a)),
        _set_status=lambda m: calls["status"].append(m),
        _announce=lambda m, **k: calls["announce"].append(m),
        _show_message_box=lambda m, *a, **k: calls["msgbox"].append(m),
        _run_background_task=lambda label, work, on_success, **k: calls.__setitem__(
            "bg", (label, work, on_success)
        ),
        _calls=calls,
    )


def _req(tmp_path: Path) -> cad.ConvertRequest:
    return cad.ConvertRequest(
        queue=[(tmp_path / "in.wav", None)],
        dest_dir=tmp_path / "out",
        spec=ConversionSpec(fmt="mp3"),
        recurse=False,
        on_existing=OnExisting.RENAME,
    )


def test_plan_and_run_without_ffmpeg_shows_message(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: None)
    host = _host()
    cad.plan_and_run(host, _req(tmp_path))
    assert host._calls["msgbox"] and "FFmpeg" in host._calls["msgbox"][0]
    assert host._calls["bg"] is None  # never started a run


def test_plan_and_run_no_jobs_reports_nothing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(cad, "plan_jobs", lambda *a, **k: ([], []))
    host = _host()
    cad.plan_and_run(host, _req(tmp_path))
    assert any("Nothing to convert" in m for m in host._calls["status"])
    assert host._calls["bg"] is None


def test_plan_and_run_starts_background_task(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("quill.core.speech.ffmpeg.find_ffmpeg", lambda: "ffmpeg")
    jobs = [ConversionJob(tmp_path / "in.wav", tmp_path / "out.mp3", ConversionSpec(fmt="mp3"))]
    monkeypatch.setattr(cad, "plan_jobs", lambda *a, **k: (jobs, []))
    host = _host()
    cad.plan_and_run(host, _req(tmp_path))
    assert host._calls["bg"] is not None
    label, _work, _on_success = host._calls["bg"]
    assert "1 file" in label


# --------------------------------------------------------------------------- #
# Dialog contract (source scrape — no wx needed)
# --------------------------------------------------------------------------- #


def _src(name: str) -> str:
    return (_UI / name).read_text(encoding="utf-8")


def test_dialog_follows_house_contract() -> None:
    src = _src("audio_studio/convert_audio_dialog.py")
    assert "apply_modal_ids(" in src
    assert "affirmative_id=wx.ID_OK" in src and "cancel_id=wx.ID_CANCEL" in src
    assert 'name="audio_studio.convert_audio"' in src
    # Sanctioned accessible list, never a CheckListBox; Delete removes a row.
    assert "wx.ListBox(" in src and "wx.CheckListBox(" not in src
    assert "apply_listbox_activation(" in src
    assert "WXK_DELETE" in src
    assert "set_accessible_name(" in src
    # Stock wx.FileDialog / wx.DirDialog ShowModal calls carry the exempt pragma.
    assert src.count("dialog_button_contract: exempt") >= 3


def test_advanced_reveal_moves_focus() -> None:
    # Advanced is a collapsible reveal that re-fits and moves focus (announce).
    src = _src("audio_studio/convert_audio_dialog.py")
    assert "Advanced o&ptions" in src
    assert "def _on_toggle_advanced(" in src
    assert ".SetFocus()" in src and "self.Fit()" in src


def test_studio_wires_convert_audio() -> None:
    src = (_UI.parent / "apps" / "studio.py").read_text(encoding="utf-8")
    assert "def convert_audio(self)" in src
    assert "run_audio_conversion(self)" in src
    assert '"studio.convert_audio"' in src
    assert "Con&vert Audio..." in src
