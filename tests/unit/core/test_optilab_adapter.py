"""The OptiLab Core adapter: locating it, arguing with it, and running it.

OptiLab Core is by **Lanes Audio / dgl1984** --
https://github.com/dgl1984/optilab -- vendored at v1.4.0 under
``quill/native/optilab/upstream/`` (Apache-2.0 WITH Commons Clause v1.0).

Two things these tests defend:

* **Optional means optional.** No adapter built must be an ordinary state --
  ``available()`` False, a reason a listener can act on, and every caller left
  on the ffmpeg chain. It must never raise.
* **The argv is a list.** It goes to ``safe_subprocess``; a shell would be a
  place for a filename to become an instruction.

The end-to-end test runs the real executable when one has been built and skips
otherwise, so a machine with no C++ toolchain is fully supported.
"""

from __future__ import annotations

import math
import struct
import subprocess
from pathlib import Path

import pytest

from quill.core import optilab_adapter as adapter

# -- attribution -------------------------------------------------------------


def test_upstream_is_credited_by_name_author_and_repository() -> None:
    """Attribution has to travel with the feature, not live only in a comment."""
    assert adapter.UPSTREAM_NAME == "OptiLab Core"
    assert adapter.UPSTREAM_AUTHOR == "Lanes Audio / dgl1984"
    assert adapter.UPSTREAM_URL == "https://github.com/dgl1984/optilab"
    assert adapter.UPSTREAM_AUTHOR_URL == "https://github.com/dgl1984"


def test_the_licence_records_the_commons_clause_not_bare_apache() -> None:
    """Upstream is Apache-2.0 WITH Commons Clause from v1.3.0; recording it as
    plain Apache-2.0 (as QUILL once did) understates the obligation."""
    assert adapter.UPSTREAM_LICENSE == "Apache-2.0 WITH Commons-Clause"


def test_the_attribution_sentence_is_speakable_and_complete() -> None:
    text = adapter.attribution()
    for part in ("OptiLab Core", "dgl1984", "github.com/dgl1984/optilab", "Commons-Clause"):
        assert part in text


def test_the_vendored_upstream_ships_its_licence_and_notice() -> None:
    """Vendoring the source makes the licence a real obligation, not a
    theoretical one -- both files must be present beside the code."""
    native = Path(__file__).resolve().parents[3] / "quill" / "native" / "optilab" / "upstream"
    for name in ("LICENSE", "NOTICE", "OptiLabCore.h", "OptiLabCore.cpp"):
        assert (native / name).is_file(), f"vendored upstream is missing {name}"
    licence = (native / "LICENSE").read_text(encoding="utf-8", errors="replace")
    assert "Commons Clause" in licence
    notice = (native / "NOTICE").read_text(encoding="utf-8", errors="replace")
    assert "Lanes Audio" in notice


def test_only_our_own_file_is_ours() -> None:
    """The adapter contains no DSP; the engine is upstream's, unmodified."""
    native = Path(__file__).resolve().parents[3] / "quill" / "native" / "optilab"
    ours = native / "quill_optilab.cpp"
    text = ours.read_text(encoding="utf-8", errors="replace")
    assert "github.com/dgl1984/optilab" in text
    assert "Commons Clause" in text


# -- optional by construction -----------------------------------------------


def test_availability_never_raises() -> None:
    assert adapter.available() in (True, False)


def test_an_unavailable_adapter_explains_itself() -> None:
    """A greyed-out option with no explanation is worse than an absent one."""
    reason = adapter.unavailable_reason()
    if adapter.available():
        assert reason == ""
    else:
        assert "OptiLab" in reason and "built-in" in reason


def test_an_override_that_points_nowhere_is_simply_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_OPTILAB_ADAPTER", str(tmp_path / "nope.exe"))
    monkeypatch.setattr("shutil.which", lambda _n: None)
    monkeypatch.setattr(adapter, "_exe_name", lambda: "definitely-not-a-real-binary")
    assert adapter.find_adapter() is None


def test_an_override_is_preferred_when_it_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = tmp_path / adapter._exe_name()
    fake.write_bytes(b"")
    monkeypatch.setenv("QUILL_OPTILAB_ADAPTER", str(fake))
    assert adapter.find_adapter() == fake


# -- the command -------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "flag"), [("podcast", "podcast"), ("stream", "stream"), ("limiter", "limiter")]
)
def test_each_mode_maps_to_its_upstream_mode(mode: str, flag: str) -> None:
    argv = adapter.adapter_command(Path("x"), mode=mode, sample_rate=48000)
    assert argv[argv.index("--mode") + 1] == flag


def test_the_command_is_a_list_never_a_string() -> None:
    argv = adapter.adapter_command(Path("x"), mode="podcast", sample_rate=48000)
    assert isinstance(argv, list)
    assert all(isinstance(part, str) for part in argv)


def test_off_is_not_a_processing_mode() -> None:
    """ "off" means do not run this at all, not run it with nothing set."""
    with pytest.raises(ValueError):
        adapter.adapter_command(Path("x"), mode="off", sample_rate=48000)


def test_an_unusable_rate_or_channel_count_is_refused() -> None:
    with pytest.raises(ValueError):
        adapter.adapter_command(Path("x"), mode="podcast", sample_rate=10)
    with pytest.raises(ValueError):
        adapter.adapter_command(Path("x"), mode="podcast", sample_rate=48000, channels=6)


def test_auto_adapt_is_clamped_to_its_range() -> None:
    argv = adapter.adapter_command(Path("x"), mode="stream", sample_rate=48000, auto_adapt=500)
    assert argv[argv.index("--adapt") + 1] == "100"
    argv = adapter.adapter_command(Path("x"), mode="stream", sample_rate=48000, auto_adapt=-5)
    assert argv[argv.index("--adapt") + 1] == "0"


# -- the honest difference table --------------------------------------------


def test_exactly_three_differences_are_claimed() -> None:
    """Reach, live preview, and the feedback loop. Anything more is marketing."""
    assert len(adapter.ENGINE_DIFFERENCES) == 3
    labels = [row[0] for row in adapter.ENGINE_DIFFERENCES]
    assert "Where it runs" in labels
    assert any("feedback loop" in label.lower() for label in labels)


def test_the_table_says_the_exact_engine_is_saved_files_only() -> None:
    """The one thing a listener must not misread: choosing exact processing
    does not change live playback."""
    where = next(row for row in adapter.ENGINE_DIFFERENCES if row[0] == "Where it runs")
    assert "Saved files only" in where[2]
    assert "live" in where[1].lower()


# -- end to end, when a build exists -----------------------------------------


def _tone(frames: int = 24_000, rate: int = 48_000) -> list[float]:
    return [0.6 * math.sin(2 * math.pi * 440 * n / rate) for n in range(frames) for _ in range(2)]


@pytest.mark.skipif(not adapter.available(), reason="quill-optilab has not been built here")
def test_the_real_engine_processes_audio_and_preserves_length() -> None:
    """The whole point: this is upstream's DSP, not our approximation."""
    exe = adapter.find_adapter()
    assert exe is not None
    samples = _tone()
    raw = struct.pack(f"<{len(samples)}f", *samples)

    argv = adapter.adapter_command(exe, mode="podcast", sample_rate=48_000, channels=2)
    result = subprocess.run(argv, input=raw, capture_output=True, check=True)
    got = struct.unpack(f"<{len(result.stdout) // 4}f", result.stdout)

    assert len(got) == len(samples), "an offline pass must not change the length"
    assert any(abs(a - b) > 1e-6 for a, b in zip(samples, got, strict=True)), (
        "the engine did nothing"
    )


@pytest.mark.skipif(not adapter.available(), reason="quill-optilab has not been built here")
def test_a_bad_mode_is_refused_by_the_executable_too() -> None:
    """Defence in depth: Python validates, and so does the adapter."""
    exe = adapter.find_adapter()
    assert exe is not None
    result = subprocess.run(
        [str(exe), "--mode", "nonsense", "--rate", "48000"], capture_output=True
    )
    assert result.returncode == 2
    assert b"podcast" in result.stderr


@pytest.mark.skipif(not adapter.available(), reason="quill-optilab has not been built here")
def test_it_credits_upstream_on_version() -> None:
    exe = adapter.find_adapter()
    assert exe is not None
    out = subprocess.run([str(exe), "--version"], capture_output=True).stdout.decode()
    assert "dgl1984" in out and "OptiLab Core" in out
