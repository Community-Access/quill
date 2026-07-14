# Voice Preview Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voice preview (Voice Browser dialog + Download Optional Components hub) gets a "generating, please wait" cue for slow synthesis, stops a prior preview instead of overlapping it, and its button toggles between Preview/Test and Stop.

**Architecture:** A generation-token counter on `MainFrame` makes `_preview_voice` the single choke point: every call stops whatever was previously active (playback + a pending cue timer) and stamps a new generation id, so any late callback from the *old* generation is a silent no-op. An optional `on_state_change` callback reports `"generating"/"playing"/"idle"` so callers can toggle their own button label. The cue itself reuses the existing QSP sound-event system (one new `SoundEvent`, mapped to an already-bundled WAV — no new audio asset) plus one new boolean setting for the spoken half.

**Tech Stack:** Python 3.13, wxPython, `winsound`/Windows MCI (existing playback backend), the existing QSP sound-pack system (`quill.core.sound_events`, `quill.ui.sound_manager`).

## Global Constraints

- No true pause/resume — the button is Preview/Test ↔ **Stop**; clicking Stop cancels playback outright, the next click starts fresh.
- No forced cancellation of in-flight external synthesis (Piper/eSpeak/DECtalk subprocess, Kokoro's Python call) — a superseded/stopped generation's synthesis finishes silently in the background; only playback and QUILL's own announcements are guaranteed to stop immediately.
- The cue is one-shot per generation (fires at most once), gated by a ~400ms delay so instant paths (sample playback, SAPI5) essentially never trigger it.
- No new combined "mode" setting — the sound half is configured through the existing Sound Events dialog (per-event toggle, already built); only the spoken half gets one new boolean, default `True`.
- Every new/changed test must pass; run the smallest relevant test file per task, not the full suite, per project convention (`CLAUDE.md`).

---

### Task 1: Register the `VOICE_PREVIEW_GENERATING` sound event

**Files:**
- Modify: `quill/core/sound_events.py`
- Modify: `quill/assets/sound_packs/ink/manifest.json`
- Modify: `quill/ui/sound_events_dialog.py`
- Test: `tests/unit/core/test_voice_preview_sound_event.py` (new)

**Interfaces:**
- Produces: `SoundEvent.VOICE_PREVIEW_GENERATING` (value `"voice_preview_generating"`), usable anywhere via `from quill.core.sound_events import SoundEvent` and `post_sound(SoundEvent.VOICE_PREVIEW_GENERATING)`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/test_voice_preview_sound_event.py`:

```python
"""The voice-preview 'generating' cue must exist as a SoundEvent and ship in the pack."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sound_events import SoundEvent

_ROOT = Path(__file__).resolve().parents[3]


def test_voice_preview_generating_is_a_registered_sound_event() -> None:
    valid = {e.value for e in SoundEvent}
    assert "voice_preview_generating" in valid


def test_ink_pack_maps_voice_preview_generating() -> None:
    pack = _ROOT / "quill" / "assets" / "sound_packs" / "ink"
    events = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))["events"]
    assert "voice_preview_generating" in events
    assert (pack / events["voice_preview_generating"]).is_file()


def test_voice_preview_generating_is_labeled_in_the_sound_events_dialog() -> None:
    src = (_ROOT / "quill" / "ui" / "sound_events_dialog.py").read_text(encoding="utf-8")
    assert '"voice_preview_generating"' in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_voice_preview_sound_event.py -v`
Expected: FAIL (`voice_preview_generating` not in `SoundEvent` values; not in manifest; not in dialog source).

- [ ] **Step 3: Add the enum member**

In `quill/core/sound_events.py`, the class ends with:

```python
    # System
    ERROR = "error"
    WARNING = "warning"
    SOUND_ON = "sound_on"
    SOUND_OFF = "sound_off"
```

Add a new section right before `# System`:

```python
    # Voice preview (Voice Browser + Download Optional Components hub)
    VOICE_PREVIEW_GENERATING = "voice_preview_generating"

    # System
    ERROR = "error"
    WARNING = "warning"
    SOUND_ON = "sound_on"
    SOUND_OFF = "sound_off"
```

- [ ] **Step 4: Map it in the bundled Ink pack**

In `quill/assets/sound_packs/ink/manifest.json`, the `"events"` object currently ends with:

```json
  "conversation_error": "conversation_error.wav"
 }
}
```

Change to (reusing the existing `ai_start.wav` — same "something is being generated" tone, no new WAV file):

```json
  "conversation_error": "conversation_error.wav",
  "voice_preview_generating": "ai_start.wav"
 }
}
```

- [ ] **Step 5: Label it in the Sound Events dialog**

In `quill/ui/sound_events_dialog.py`, `_EARCON_ORDER` currently ends its "AI and transcription" group with:

```python
    "transcription_word_inserted",
    # Voice conversation mode (Hey QUILL Phase 2)
```

Add a new entry and group right after it:

```python
    "transcription_word_inserted",
    # Voice preview (Voice Browser + Download Optional Components hub)
    "voice_preview_generating",
    # Voice conversation mode (Hey QUILL Phase 2)
```

And in `_EARCON_LABELS`, right after the `"transcription_word_inserted"` entry:

```python
    "transcription_word_inserted": "Transcription word inserted",
    "voice_preview_generating": "Voice preview: generating, please wait",
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/core/test_voice_preview_sound_event.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Run the existing sound-system tests to check for regressions**

Run: `pytest tests/unit/core/test_sound_pack.py tests/unit/core/test_conversation_sound_events.py tests/unit/core/test_compare_sound_events.py tests/unit/ui/test_sound_events_dialog.py tests/unit/ui/test_sound_manager.py -q`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add quill/core/sound_events.py quill/assets/sound_packs/ink/manifest.json quill/ui/sound_events_dialog.py tests/unit/core/test_voice_preview_sound_event.py
git commit -m "feat(sound): add voice_preview_generating earcon (reuses ai_start.wav)"
```

---

### Task 2: Add the `voice_preview_announce_generating` setting

**Files:**
- Modify: `quill/core/settings.py`
- Modify: `quill/core/settings_specs.py`
- Test: `tests/unit/core/test_settings.py`

**Interfaces:**
- Produces: `Settings.voice_preview_announce_generating: bool` (default `True`), round-tripped through `save_settings`/`load_settings` like every other field.

- [ ] **Step 1: Write the failing test**

In `tests/unit/core/test_settings.py`, add (near the other sound-related round-trip tests, e.g. after `test_settings_persists_batch_speech_chapter_fields`):

```python
def test_voice_preview_announce_generating_defaults_true_and_round_trips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert Settings().voice_preview_announce_generating is True

    save_settings(Settings(voice_preview_announce_generating=False))
    loaded = load_settings()
    assert loaded.voice_preview_announce_generating is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_settings.py -k voice_preview_announce_generating -v`
Expected: FAIL (`TypeError: Settings.__init__() got an unexpected keyword argument 'voice_preview_announce_generating'`)

- [ ] **Step 3: Add the field**

In `quill/core/settings.py`, this block currently reads:

```python
    sound_enabled: bool = True
    sound_pack_path: str = ""  # empty = bundled Ink pack
    sound_volume: int = 80  # 0-100; passed to sound_lib Output.set_volume()
    sound_events_disabled: str = ""  # comma-separated SoundEvent IDs to silence
```

Add a new field right after it:

```python
    sound_enabled: bool = True
    sound_pack_path: str = ""  # empty = bundled Ink pack
    sound_volume: int = 80  # 0-100; passed to sound_lib Output.set_volume()
    sound_events_disabled: str = ""  # comma-separated SoundEvent IDs to silence
    # Speak "Generating preview, please wait" when a voice preview's synthesis
    # is still running after the ~400ms cue delay (paired with the
    # voice_preview_generating earcon, configured independently via the
    # Sound Events dialog).
    voice_preview_announce_generating: bool = True
```

- [ ] **Step 4: Wire the parse**

In `quill/core/settings.py`, this line currently reads:

```python
        sound_events_disabled = str(data.get("sound_events_disabled", ""))
```

Add right after it:

```python
        sound_events_disabled = str(data.get("sound_events_disabled", ""))
        voice_preview_announce_generating = bool(
            data.get("voice_preview_announce_generating", True)
        )
```

- [ ] **Step 5: Wire the constructor call**

In `quill/core/settings.py`, this line currently reads:

```python
            sound_events_disabled=sound_events_disabled,
```

Add right after it:

```python
            sound_events_disabled=sound_events_disabled,
            voice_preview_announce_generating=voice_preview_announce_generating,
```

- [ ] **Step 6: Add the SettingSpec entry**

In `quill/core/settings_specs.py`, find the `"sound_events_disabled"` spec (a `SettingSpec("sound_events_disabled", "Silenced sound events", "accessibility", "text", ...)`). Add a new spec immediately after its closing `),`:

```python
    SettingSpec(
        "voice_preview_announce_generating",
        "Announce \"Generating preview, please wait\" for slow voice previews",
        "accessibility",
        "bool",
        (
            "When a voice preview (Voice Browser, or Test in Download Optional "
            "Components) takes a moment to synthesize, speak a short heads-up "
            "so it's clear something is happening. The matching earcon is "
            "configured separately in the Sound Events dialog."
        ),
        keywords=("voice", "preview", "generating", "please wait", "announce", "sound"),
    ),
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/unit/core/test_settings.py -k voice_preview_announce_generating -v`
Expected: PASS (2 passed)

- [ ] **Step 8: Run the full settings test file to check for regressions**

Run: `pytest tests/unit/core/test_settings.py -q`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add quill/core/settings.py quill/core/settings_specs.py tests/unit/core/test_settings.py
git commit -m "feat(settings): add voice_preview_announce_generating (default on)"
```

---

### Task 3: Generation-token tracking — stop a prior preview instead of overlapping it

**Files:**
- Modify: `quill/ui/main_frame.py:17683-17842` (`_play_preview_asset`, `_preview_voice`)
- Test: `tests/unit/ui/test_voice_preview_generation.py` (new)

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: `MainFrame._stop_active_voice_preview() -> None`, `MainFrame._preview_generation: int` (an ever-increasing counter read by later tasks to decide whether a callback is stale), `MainFrame._purge_preview_playback() -> None`.

This task does **not** yet add the cue or the `on_state_change` callback (Tasks 4-5) — it only fixes the overlap bug: starting a new preview stops the old one's playback and prevents its completion callback from doing anything.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/ui/test_voice_preview_generation.py`:

```python
"""Starting a new voice preview must stop/supersede the previous one."""

from __future__ import annotations

import time

import pytest
import wx

from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_second_preview_supersedes_the_first(wx_app, monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)  # bypass __init__: only exercising _preview_voice
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {})()
    calls: list[str] = []

    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: calls.append(f"status:{a[0]}"))
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: calls.append(f"announce:{a[0]}"))

    def fake_play(_self, path):
        calls.append(f"play:{path}")

    monkeypatch.setattr(MainFrame, "_play_preview_asset", fake_play)
    monkeypatch.setattr(
        frame, "_voice_preview_sample_path", lambda *a, **k: __import__("pathlib").Path("a.wav")
    )

    # First preview (sample playback -- runs on a background thread).
    frame._preview_voice("piper", "voice-a", live=False)
    # Immediately start a second preview before the first's background thread
    # has necessarily finished; the first's generation must now be stale.
    frame._preview_voice("piper", "voice-b", live=False)

    # Let both background threads (and their wx.CallAfter completions) run.
    for _ in range(20):
        wx.YieldIfNeeded()
        time.sleep(0.02)

    finished_count = sum(1 for c in calls if c == "status:Preview finished")
    assert finished_count == 1, calls
    frame.frame.Destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/ui/test_voice_preview_generation.py -v`
Expected: FAIL — both previews currently announce "Preview finished" (no staleness check exists yet), so `finished_count == 2`.

- [ ] **Step 3: Add the stop/purge helper and generation tracking**

In `quill/ui/main_frame.py`, `_play_preview_asset` currently reads:

```python
    def _play_preview_asset(self, sample_path: Path) -> None:
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME)
            return
```

Add a new method right before it:

```python
    def _purge_preview_playback(self) -> None:
        """Best-effort: stop whatever voice-preview audio is currently sounding.

        Covers both playback backends `_play_preview_asset` uses. Never raises --
        called opportunistically whenever a new preview supersedes an old one.
        """
        if _winsound is not None:
            try:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass
        try:
            import ctypes as _ct

            _ct.windll.winmm.mciSendStringW("stop quill_preview", None, 0, None)  # type: ignore[attr-defined]
            _ct.windll.winmm.mciSendStringW("close quill_preview", None, 0, None)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def _stop_active_voice_preview(self) -> None:
        """Stop/supersede whatever voice preview is currently active.

        Bumps the generation counter first (so any in-flight callback from the
        old generation becomes a no-op the instant it checks), then best-effort
        stops the old preview's audio: SAPI5 goes through the ReadAloudController
        it already owns; every other engine plays through `_play_preview_asset`,
        stopped via `_purge_preview_playback`. Does NOT stop an old preview's
        synthesis if it is still computing (e.g. a Piper/Kokoro call in
        progress) -- that finishes in the background and its result is
        discarded when the stale generation check fails.
        """
        self._preview_generation = getattr(self, "_preview_generation", 0) + 1
        try:
            self._read_aloud.stop()
        except Exception:  # noqa: BLE001
            pass
        self._purge_preview_playback()

    def _play_preview_asset(self, sample_path: Path) -> None:
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME)
            return
```

- [ ] **Step 4: Make `_preview_voice` generation-aware**

In `quill/ui/main_frame.py`, `_preview_voice` currently starts:

```python
    def _preview_voice(
        self, engine: str, voice_id: str, *, live: bool = False, text: str | None = None
    ) -> None:
        """Preview *voice_id* through *engine* on a background thread.

        ``live`` True means the voice is downloaded and ready, so synthesize the
        preview phrase with the real model. ``live`` False (the voice is not yet
        downloaded) plays the bundled pre-recorded sample instead, so the user
        can still hear what the voice sounds like before downloading; if no
        sample ships for it, we say so rather than failing silently.
        """
        import tempfile as _tmpfile
        from pathlib import Path as _Path

        sample = text or self._PREVIEW_TEXT
        s = self.settings

        # Not downloaded: play the bundled pre-recorded sample (same phrase the
        # live synthesis uses), or explain that none is available.
        if not live:
            preview_sample = self._voice_preview_sample_path(engine, voice_id)
            if preview_sample is None:
                self._set_status("Download this voice to hear a preview.")
                return

            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                self._play_preview_asset(preview_sample)
                return None

            self._run_background_task(
                f"Previewing {engine} voice",
                _play_sample,
                lambda _r: self._set_status("Preview finished"),
            )
            return
```

Replace that whole method opening (through the sample-playback `return`) with:

```python
    def _preview_voice(
        self, engine: str, voice_id: str, *, live: bool = False, text: str | None = None
    ) -> None:
        """Preview *voice_id* through *engine* on a background thread.

        ``live`` True means the voice is downloaded and ready, so synthesize the
        preview phrase with the real model. ``live`` False (the voice is not yet
        downloaded) plays the bundled pre-recorded sample instead, so the user
        can still hear what the voice sounds like before downloading; if no
        sample ships for it, we say so rather than failing silently.

        Starting a preview always stops/supersedes whatever preview was
        previously active (see ``_stop_active_voice_preview``): its playback is
        cut short and its completion callback becomes a no-op, so two previews
        started in quick succession never overlap.
        """
        import tempfile as _tmpfile
        from pathlib import Path as _Path

        self._stop_active_voice_preview()
        my_generation = self._preview_generation

        def _still_current() -> bool:
            return getattr(self, "_preview_generation", 0) == my_generation

        sample = text or self._PREVIEW_TEXT
        s = self.settings

        # Not downloaded: play the bundled pre-recorded sample (same phrase the
        # live synthesis uses), or explain that none is available.
        if not live:
            preview_sample = self._voice_preview_sample_path(engine, voice_id)
            if preview_sample is None:
                self._set_status("Download this voice to hear a preview.")
                return

            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                self._play_preview_asset(preview_sample)
                return None

            def _sample_done(_r: object) -> None:
                if _still_current():
                    self._set_status("Preview finished")

            self._run_background_task(
                f"Previewing {engine} voice",
                _play_sample,
                _sample_done,
            )
            return
```

- [ ] **Step 5: Guard the sapi5 branch's completion callback**

In `quill/ui/main_frame.py`, the sapi5 branch currently reads:

```python
        # sapi5: delegate to ReadAloudController so SAPI5/COM runs on its own
        # dedicated thread, avoiding the "started a loop" error from ThreadPoolExecutor.
        if engine == "sapi5":
            try:
                self._read_aloud.start(
                    sample,
                    0,
                    voice_id,
                    engine_name="sapi5",
                    rate=s.read_aloud_rate,
                    volume=s.read_aloud_volume / 100.0,
                    pitch=s.read_aloud_pitch,
                    on_state_change=lambda state: (
                        self._wx.CallAfter(self._set_status, "Preview finished")
                        if state in ("idle", "error")
                        else None
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Preview failed: {exc}")
            return
```

Replace the `on_state_change` lambda's body so it also checks staleness:

```python
        # sapi5: delegate to ReadAloudController so SAPI5/COM runs on its own
        # dedicated thread, avoiding the "started a loop" error from ThreadPoolExecutor.
        if engine == "sapi5":
            try:
                self._read_aloud.start(
                    sample,
                    0,
                    voice_id,
                    engine_name="sapi5",
                    rate=s.read_aloud_rate,
                    volume=s.read_aloud_volume / 100.0,
                    pitch=s.read_aloud_pitch,
                    on_state_change=lambda state: (
                        self._wx.CallAfter(self._set_status, "Preview finished")
                        if state in ("idle", "error") and _still_current()
                        else None
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Preview failed: {exc}")
            return
```

- [ ] **Step 6: Guard the synthesis branches' completion callback**

In `quill/ui/main_frame.py`, the final block of `_preview_voice` currently reads:

```python
                self._play_preview_asset(wav)
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            lambda _r: self._set_status("Preview finished"),
        )
```

Replace the final two statements:

```python
                self._play_preview_asset(wav)
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        def _synth_done(_r: object) -> None:
            if _still_current():
                self._set_status("Preview finished")

        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            _synth_done,
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/unit/ui/test_voice_preview_generation.py -v`
Expected: PASS

- [ ] **Step 8: Run the broader speech/UI test surface to check for regressions**

Run: `pytest tests/unit/ui/test_optional_components_dialog.py tests/unit/core/test_optional_components.py -q`
Expected: all PASS (this task doesn't touch those files, but `_preview_voice` is shared with the hub's voice Test path)

- [ ] **Step 9: Commit**

```bash
git add quill/ui/main_frame.py tests/unit/ui/test_voice_preview_generation.py
git commit -m "fix(speech): stop a prior voice preview instead of overlapping a new one"
```

---

### Task 4: The "generating, please wait" cue

**Files:**
- Modify: `quill/ui/main_frame.py` (`_preview_voice`)
- Test: `tests/unit/ui/test_voice_preview_generation.py`

**Interfaces:**
- Consumes: `SoundEvent.VOICE_PREVIEW_GENERATING` (Task 1), `settings.voice_preview_announce_generating` (Task 2), `self._preview_generation`/`_still_current` pattern (Task 3).
- Produces: `MainFrame._fire_generating_cue(generation: int) -> None`; a pending `wx.CallLater` stored on `self._preview_cue_timer`, cancelled by `_stop_active_voice_preview`.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/ui/test_voice_preview_generation.py`:

```python
def test_generating_cue_fires_once_after_the_delay(wx_app, monkeypatch) -> None:
    from quill.core.sound_events import SoundEvent

    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {"voice_preview_announce_generating": True})()
    posted: list[str] = []
    announced: list[str] = []

    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: None)
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: announced.append(a[0]))
    monkeypatch.setattr(
        "quill.ui.main_frame.post_sound", lambda event_id: posted.append(event_id)
    )

    frame._stop_active_voice_preview()
    my_generation = frame._preview_generation
    frame._preview_cue_timer = wx.CallLater(50, frame._fire_generating_cue, my_generation)

    for _ in range(30):
        wx.YieldIfNeeded()
        time.sleep(0.02)
        if posted:
            break

    assert posted == [SoundEvent.VOICE_PREVIEW_GENERATING.value]
    assert announced == ["Generating preview, please wait."]
    frame.frame.Destroy()


def test_generating_cue_does_not_fire_if_superseded_first(wx_app, monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = type("S", (), {"voice_preview_announce_generating": True})()
    posted: list[str] = []
    monkeypatch.setattr(frame, "_set_status", lambda *a, **k: None)
    monkeypatch.setattr(frame, "_announce", lambda *a, **k: None)
    monkeypatch.setattr(
        "quill.ui.main_frame.post_sound", lambda event_id: posted.append(event_id)
    )

    frame._stop_active_voice_preview()
    stale_generation = frame._preview_generation
    frame._preview_cue_timer = wx.CallLater(50, frame._fire_generating_cue, stale_generation)
    # Supersede before the timer fires.
    frame._stop_active_voice_preview()

    for _ in range(30):
        wx.YieldIfNeeded()
        time.sleep(0.02)

    assert posted == []
    frame.frame.Destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/ui/test_voice_preview_generation.py -k generating_cue -v`
Expected: FAIL (`AttributeError: 'MainFrame' object has no attribute '_fire_generating_cue'` / no `post_sound` imported in `main_frame.py`)

- [ ] **Step 3: Import `post_sound` and add the cue method**

In `quill/ui/main_frame.py`, add to the imports near the other `quill.ui` imports (alongside existing sound-adjacent imports; place near the top-level import block):

```python
from quill.ui.sound_manager import post_sound
```

Add the cue method right after `_stop_active_voice_preview` (defined in Task 3):

```python
    def _fire_generating_cue(self, generation: int) -> None:
        """One-shot "still generating" cue -- fires only if *generation* is
        still current (the ~400ms delay elapsed before synthesis finished)."""
        if getattr(self, "_preview_generation", 0) != generation:
            return
        post_sound(SoundEvent.VOICE_PREVIEW_GENERATING)
        if getattr(self.settings, "voice_preview_announce_generating", True):
            self._announce("Generating preview, please wait.")
```

Add the `SoundEvent` import near the top of `quill/ui/main_frame.py`, alongside the new `post_sound` import:

```python
from quill.core.sound_events import SoundEvent
```

- [ ] **Step 4: Cancel the pending timer in `_stop_active_voice_preview`**

In `quill/ui/main_frame.py`, `_stop_active_voice_preview` (added in Task 3) currently reads:

```python
        self._preview_generation = getattr(self, "_preview_generation", 0) + 1
        try:
            self._read_aloud.stop()
        except Exception:  # noqa: BLE001
            pass
        self._purge_preview_playback()
```

Add the timer cancellation right after bumping the generation:

```python
        self._preview_generation = getattr(self, "_preview_generation", 0) + 1
        timer = getattr(self, "_preview_cue_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
            self._preview_cue_timer = None
        try:
            self._read_aloud.stop()
        except Exception:  # noqa: BLE001
            pass
        self._purge_preview_playback()
```

- [ ] **Step 5: Start the timer for synthesis branches only**

In `quill/ui/main_frame.py`, the end of `_preview_voice` (from Task 3, Step 6) currently reads:

```python
        def _synth_done(_r: object) -> None:
            if _still_current():
                self._set_status("Preview finished")

        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            _synth_done,
        )
```

Replace with (starting the cue timer right before dispatch — sample playback and the `sapi5` branch both `return` earlier in the method and never reach this point, matching "nothing to wait for" for those two):

```python
        def _synth_done(_r: object) -> None:
            if _still_current():
                self._set_status("Preview finished")

        self._preview_cue_timer = self._wx.CallLater(400, self._fire_generating_cue, my_generation)
        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            _synth_done,
        )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/ui/test_voice_preview_generation.py -v`
Expected: PASS (all tests in this file)

- [ ] **Step 7: Run the full sound + settings + preview test surface to check for regressions**

Run: `pytest tests/unit/core/test_sound_pack.py tests/unit/core/test_settings.py tests/unit/ui/test_voice_preview_generation.py tests/unit/core/test_voice_preview_sound_event.py -q`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add quill/ui/main_frame.py tests/unit/ui/test_voice_preview_generation.py
git commit -m "feat(speech): play/announce a 'generating preview' cue for slow voice previews"
```

---

### Task 5: Play ↔ Stop button in the Voice Browser dialog

**Files:**
- Modify: `quill/ui/main_frame.py` (`_preview_voice` signature)
- Modify: `quill/ui/voice_browser_dialog.py`
- Test: `tests/unit/ui/test_voice_browser_dialog.py`

**Interfaces:**
- Consumes: `MainFrame._preview_voice(..., on_state_change: Callable[[str], None] | None = None)`; `MainFrame._stop_active_voice_preview()` (Task 3).
- Produces: `VoiceBrowserDialog._on_preview_state(state: str) -> None`; `_preview_btn` toggles between `"&Preview Selected Voice"` and `"&Stop Preview"`.

- [ ] **Step 1: Give `_preview_voice` an `on_state_change` parameter**

In `quill/ui/main_frame.py`, `_preview_voice`'s signature (after Task 3/4's edits) currently reads:

```python
    def _preview_voice(
        self, engine: str, voice_id: str, *, live: bool = False, text: str | None = None
    ) -> None:
```

Change to:

```python
    def _preview_voice(
        self,
        engine: str,
        voice_id: str,
        *,
        live: bool = False,
        text: str | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
```

Add a small helper right after the `_still_current` closure (defined in Task 3, Step 4):

```python
        def _report(state: str) -> None:
            if on_state_change is not None and _still_current():
                self._wx.CallAfter(on_state_change, state)
```

Call `_report("playing")` right before every `_play_preview_asset`/`_read_aloud.start` call, and `_report("idle")` in each completion path. Concretely:

- In the sample-playback branch, `_play_sample` currently reads `self._play_preview_asset(preview_sample)`; change to:

```python
            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                _report("playing")
                self._play_preview_asset(preview_sample)
                return None
```

  and `_sample_done` currently reads:

```python
            def _sample_done(_r: object) -> None:
                if _still_current():
                    self._set_status("Preview finished")
```

  change to:

```python
            def _sample_done(_r: object) -> None:
                if _still_current():
                    self._set_status("Preview finished")
                _report("idle")
```

- In the `sapi5` branch, call `_report("playing")` immediately before `self._read_aloud.start(`, and inside the existing `on_state_change` lambda passed to `self._read_aloud.start`, add `_report("idle")` alongside the existing `_still_current()`-guarded call:

```python
                    on_state_change=lambda state: (
                        (self._wx.CallAfter(self._set_status, "Preview finished"), _report("idle"))
                        if state in ("idle", "error") and _still_current()
                        else None
                    ),
```

- In the synthesis branches, call `_report("generating")` right before `self._preview_cue_timer = self._wx.CallLater(...)`, change `self._play_preview_asset(wav)` (inside `_work`) to also report:

```python
                _report("playing")
                self._play_preview_asset(wav)
```

  and `_synth_done` currently reads:

```python
        def _synth_done(_r: object) -> None:
            if _still_current():
                self._set_status("Preview finished")
```

  change to:

```python
        def _synth_done(_r: object) -> None:
            if _still_current():
                self._set_status("Preview finished")
            _report("idle")
```

  and right before the `_preview_cue_timer` line, add:

```python
        _report("generating")
```

- [ ] **Step 2: Write the failing UI test**

In `tests/unit/ui/test_voice_browser_dialog.py`, add:

```python
def test_preview_button_toggles_to_stop_while_active(wx_app) -> None:
    import wx

    from quill.ui.voice_browser_dialog import VoiceBrowserDialog

    states: list[str] = []

    def fake_preview(engine, voice_id, *, live=False, on_state_change=None):
        states.append("called")
        if on_state_change is not None:
            on_state_change("playing")

    frame = wx.Frame(None)
    dlg = VoiceBrowserDialog(
        frame,
        engine_options=[("SAPI 5", "sapi5")],
        current_engine="sapi5",
        piper_model_dir=__import__("pathlib").Path("."),
        settings=type("S", (), {"read_aloud_rate": 200, "read_aloud_volume": 100, "read_aloud_pitch": 0})(),
        preview_fn=fake_preview,
    )
    dlg._all_voices = [type("V", (), {"id": "v1", "name": "Voice 1", "installed": True})()]
    dlg._displayed_voices = dlg._all_voices
    dlg._voice_lb.Append("Voice 1")
    dlg._voice_lb.SetSelection(0)

    dlg._do_preview()
    wx.YieldIfNeeded()

    assert dlg._preview_btn.GetLabel() == "&Stop Preview"
    frame.Destroy()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/ui/test_voice_browser_dialog.py -k toggles_to_stop -v`
Expected: FAIL (button label stays `"&Preview Selected Voice"`; `_do_preview` does not pass `on_state_change` yet)

- [ ] **Step 4: Wire the button state in the dialog**

In `quill/ui/voice_browser_dialog.py`, `_do_preview` currently reads:

```python
    def _do_preview(self) -> None:
        idx = self._voice_lb.GetSelection()
        wx = self._wx
        if idx == wx.NOT_FOUND or idx >= len(self._displayed_voices):
            return
        eng = self._current_engine_id()
        v = self._displayed_voices[idx]
        ready = self._voice_is_ready(eng, v)
        # Downloaded -> real synthesis with the model; not downloaded -> the
        # bundled pre-recorded sample (if one ships for this voice).
        if not ready and not self._has_preview_sample(eng, v.id):
            return
        voice_id = self._espeak_combined_voice_id(v.id) if eng == "espeak" else v.id
        self._preview_fn(eng, voice_id, live=ready)
```

Replace with:

```python
    def _do_preview(self) -> None:
        if self._previewing:
            self._stop_preview()
            return
        idx = self._voice_lb.GetSelection()
        wx = self._wx
        if idx == wx.NOT_FOUND or idx >= len(self._displayed_voices):
            return
        eng = self._current_engine_id()
        v = self._displayed_voices[idx]
        ready = self._voice_is_ready(eng, v)
        # Downloaded -> real synthesis with the model; not downloaded -> the
        # bundled pre-recorded sample (if one ships for this voice).
        if not ready and not self._has_preview_sample(eng, v.id):
            return
        voice_id = self._espeak_combined_voice_id(v.id) if eng == "espeak" else v.id
        self._preview_fn(eng, voice_id, live=ready, on_state_change=self._on_preview_state)

    def _on_preview_state(self, state: str) -> None:
        """Toggle the Preview button between its idle and Stop labels."""
        self._previewing = state in ("generating", "playing")
        self._preview_btn.SetLabel("&Stop Preview" if self._previewing else "&Preview Selected Voice")

    def _stop_preview(self) -> None:
        """Cancel the active preview via the same path a new preview would use."""
        self._preview_stop_fn()
        self._on_preview_state("idle")
```

- [ ] **Step 5: Initialize `_previewing`/`_preview_stop_fn` and pass the stop hook**

In `quill/ui/voice_browser_dialog.py`, `__init__` currently reads:

```python
        self._preview_fn = preview_fn
        self._engine_available: dict[str, bool] = engine_available or {}
```

Change to:

```python
        self._preview_fn = preview_fn
        self._preview_stop_fn = preview_stop_fn or (lambda: None)
        self._previewing = False
        self._engine_available: dict[str, bool] = engine_available or {}
```

Add the new constructor parameter to `__init__`'s signature, which currently reads:

```python
        preview_fn: Callable[..., None],
        engine_available: dict[str, bool] | None = None,
```

Change to:

```python
        preview_fn: Callable[..., None],
        preview_stop_fn: Callable[[], None] | None = None,
        engine_available: dict[str, bool] | None = None,
```

- [ ] **Step 6: Pass the stop hook from MainFrame**

In `quill/ui/main_frame.py`, find where `"preview_fn": self._preview_voice,` is set (inside the kwargs dict built for `open_speech_hub`). Add right after it:

```python
            "preview_fn": self._preview_voice,
            "preview_stop_fn": self._stop_active_voice_preview,
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/unit/ui/test_voice_browser_dialog.py -k toggles_to_stop -v`
Expected: PASS

- [ ] **Step 8: Run the full Voice Browser + preview test files to check for regressions**

Run: `pytest tests/unit/ui/test_voice_browser_dialog.py tests/unit/ui/test_voice_preview_generation.py -q`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add quill/ui/main_frame.py quill/ui/voice_browser_dialog.py tests/unit/ui/test_voice_browser_dialog.py
git commit -m "feat(speech): Voice Browser Preview button toggles to Stop while active"
```

---

### Task 6: Play ↔ Stop button in the Download Optional Components hub (voice rows)

**Files:**
- Modify: `quill/ui/optional_components_dialog.py`
- Modify: `quill/ui/main_frame_speech.py` (`_test_optional_component`, `_Controller` in `open_optional_components`)
- Test: `tests/unit/ui/test_optional_components_dialog.py`

**Interfaces:**
- Consumes: `MainFrame._preview_voice(..., on_state_change=...)` (Task 5), `MainFrame._stop_active_voice_preview()` (Task 3), `oc.read_aloud_engine_for_component(component_id) -> str | None` (existing).
- Produces: `ComponentsController.test(component_id, on_state_change=None)`, `ComponentsController.stop_test(component_id) -> None`, `ComponentsController.is_previewable(component_id) -> bool`.

- [ ] **Step 1: Extend the `ComponentsController` protocol**

In `quill/ui/optional_components_dialog.py`, the protocol currently reads:

```python
    def test(self, component_id: str) -> None:
        """Prove the component works (play a voice sample / self-test); announces."""

    def manage(self, component_id: str) -> None:
        """Open the component's own management dialog (models / voices)."""
```

Change to:

```python
    def test(self, component_id: str, *, on_state_change: Callable[[str], None] | None = None) -> None:
        """Prove the component works (play a voice sample / self-test); announces.

        ``on_state_change``, when the component is a voice, reports
        "generating"/"playing"/"idle" so the caller can toggle a Stop button.
        Ignored for non-voice components (engine/tool self-tests run to
        completion quickly and only announce their result)."""

    def stop_test(self, component_id: str) -> None:
        """Cancel an in-progress voice preview started via test()."""

    def is_previewable(self, component_id: str) -> bool:
        """True when test() reports state changes (a voice component)."""

    def manage(self, component_id: str) -> None:
        """Open the component's own management dialog (models / voices)."""
```

Add `Callable` to the imports at the top of the file, which currently read:

```python
from typing import Any, Protocol
```

Change to:

```python
from collections.abc import Callable
from typing import Any, Protocol
```

- [ ] **Step 2: Wire the Test button's state and click handling**

In `quill/ui/optional_components_dialog.py`, `_sync_controls` currently reads (after the earlier `effective_ready` change):

```python
        ready = comp.effective_ready
        download_btn.Enable(not ready)
        download_btn.SetLabel("Installed" if ready else "&Download")
        test_btn.Enable(ready)
```

Change to:

```python
        ready = comp.effective_ready
        download_btn.Enable(not ready)
        download_btn.SetLabel("Installed" if ready else "&Download")
        test_btn.Enable(ready)
        if not testing["active"]:
            test_btn.SetLabel("&Test")
```

Add a small mutable state cell right where `chosen = {"id": ""}` is declared, which currently reads:

```python
    chosen = {"id": ""}
    rows: list[OptionalComponent] = []
```

Change to:

```python
    chosen = {"id": ""}
    testing = {"active": False}
    rows: list[OptionalComponent] = []
```

`_on_test` currently reads (after the earlier `effective_ready` change):

```python
    def _on_test(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None or not comp.effective_ready:
            return
        controller.test(comp.component_id)  # announces its own result
```

Replace with:

```python
    def _on_state_change(state: str) -> None:
        testing["active"] = state in ("generating", "playing")
        test_btn.SetLabel("&Stop" if testing["active"] else "&Test")

    def _on_test(_evt: Any = None) -> None:
        comp = _selected()
        if comp is None:
            return
        if testing["active"]:
            controller.stop_test(comp.component_id)
            _on_state_change("idle")
            return
        if not comp.effective_ready:
            return
        if controller.is_previewable(comp.component_id):
            controller.test(comp.component_id, on_state_change=_on_state_change)
        else:
            controller.test(comp.component_id)  # announces its own result
```

- [ ] **Step 3: Implement the new controller methods**

In `quill/ui/main_frame_speech.py`, `open_optional_components`'s `_Controller` class currently reads:

```python
            def test(self, component_id: str) -> None:
                frame._test_optional_component(component_id)
```

Change to:

```python
            def test(
                self, component_id: str, *, on_state_change: Callable[[str], None] | None = None
            ) -> None:
                frame._test_optional_component(component_id, on_state_change=on_state_change)

            def stop_test(self, component_id: str) -> None:
                frame._stop_active_voice_preview()

            def is_previewable(self, component_id: str) -> bool:
                from quill.core import optional_components as oc

                return oc.read_aloud_engine_for_component(component_id) is not None
```

`_test_optional_component` currently reads:

```python
    def _test_optional_component(self, component_id: str) -> None:
        """Prove *component_id* works: voices play a spoken sample; other
        components run their wx-free self-test on a worker and announce the
        result. Expected "get one more piece" states (no model / no voice) route
        the user to Manage rather than erroring or offering a bug report."""
        from quill.core import optional_components as oc

        engine = oc.read_aloud_engine_for_component(component_id)
        if engine is not None:
            voices = oc.available_live_voices(engine)
            if not voices:
                # Engine present but no voice to speak yet: route to Manage Voices
                # instead of previewing an empty voice (which errors with "model
                # file not found" and leaves focus stranded behind the hub).
                self._set_status(
                    f"No {engine} voice is downloaded yet — opening Manage Voices to get one."
                )
                self._manage_component_models_or_voices(component_id)
                return
            # One voice: play it straight away (no dialog friction). More than one:
            # let the user pick which to hear via an accessible single-select
            # dialog, so Test is a small delight rather than always voice #1.
            chosen = voices[0]
            if len(voices) > 1:
                picked = self._choose_voice_to_preview(engine, voices)
                if picked is None:
                    self._set_status("Voice test cancelled.")
                    return
                chosen = picked
            self._announce(f"Playing {chosen.name}.")
            self._preview_voice(engine, chosen.id, live=True, text=oc.voice_preview_phrase())
            return
```

Change the signature and the final call:

```python
    def _test_optional_component(
        self, component_id: str, *, on_state_change: Callable[[str], None] | None = None
    ) -> None:
        """Prove *component_id* works: voices play a spoken sample; other
        components run their wx-free self-test on a worker and announce the
        result. Expected "get one more piece" states (no model / no voice) route
        the user to Manage rather than erroring or offering a bug report."""
        from quill.core import optional_components as oc

        engine = oc.read_aloud_engine_for_component(component_id)
        if engine is not None:
            voices = oc.available_live_voices(engine)
            if not voices:
                # Engine present but no voice to speak yet: route to Manage Voices
                # instead of previewing an empty voice (which errors with "model
                # file not found" and leaves focus stranded behind the hub).
                self._set_status(
                    f"No {engine} voice is downloaded yet — opening Manage Voices to get one."
                )
                self._manage_component_models_or_voices(component_id)
                return
            # One voice: play it straight away (no dialog friction). More than one:
            # let the user pick which to hear via an accessible single-select
            # dialog, so Test is a small delight rather than always voice #1.
            chosen = voices[0]
            if len(voices) > 1:
                picked = self._choose_voice_to_preview(engine, voices)
                if picked is None:
                    self._set_status("Voice test cancelled.")
                    return
                chosen = picked
            self._announce(f"Playing {chosen.name}.")
            self._preview_voice(
                engine,
                chosen.id,
                live=True,
                text=oc.voice_preview_phrase(),
                on_state_change=on_state_change,
            )
            return
```

- [ ] **Step 4: Write the failing test**

In `tests/unit/ui/test_optional_components_dialog.py`, add:

```python
def test_test_button_toggles_to_stop_for_voice_rows() -> None:
    src = _src("optional_components_dialog.py")
    assert '"&Stop"' in src
    assert "controller.stop_test(" in src
    assert "controller.is_previewable(" in src


def test_controller_protocol_supports_preview_state() -> None:
    src = _src("optional_components_dialog.py")
    assert "def stop_test(self, component_id: str) -> None:" in src
    assert "def is_previewable(self, component_id: str) -> bool:" in src
```

- [ ] **Step 5: Run test to verify it fails, then passes**

Run: `pytest tests/unit/ui/test_optional_components_dialog.py -k "toggles_to_stop_for_voice or supports_preview_state" -v`
Expected: FAIL before Steps 1-3, PASS after.

- [ ] **Step 6: Run the full hub + speech test files to check for regressions**

Run: `pytest tests/unit/ui/test_optional_components_dialog.py tests/unit/core/test_optional_components.py -q`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add quill/ui/optional_components_dialog.py quill/ui/main_frame_speech.py tests/unit/ui/test_optional_components_dialog.py
git commit -m "feat(speech): hub Test button toggles to Stop for voice components"
```

---

### Task 7: Documentation — user guide, PRD, CHANGELOG, release notes

**Files:**
- Modify: `docs/user guide/userguide.md`
- Modify: `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/release notes/release0.9.0-beta2.md`

**Interfaces:** none (prose only).

- [ ] **Step 1: User guide**

In `docs/user guide/userguide.md`, find the section documenting voice preview (search for "Preview Selected Voice" or the Voice Browser section). Add a paragraph:

```markdown
When you preview a voice, QUILL stops any preview already playing before
starting the new one, so previews never overlap. If a voice takes a moment
to synthesize (some neural voices do), QUILL plays a short earcon and, by
default, says "Generating preview, please wait" so you know it's working —
turn either off independently in Preferences > Sound (the earcon, via Sound
Events) and Preferences > Accessibility (the announcement). While a preview
is generating or playing, the Preview/Test button becomes a Stop button so
you can cancel it at any time.
```

- [ ] **Step 2: PRD**

In `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`, find the Read Aloud / voice preview section (search for "voice preview" or "Voice Browser"). Add a subsection:

```markdown
#### Voice preview feedback

Voice preview (Voice Browser dialog and the Download Optional Components
hub's Test button) reports its own state: starting a new preview always
stops/supersedes a prior one (no overlapping audio or announcements), a
one-shot "generating, please wait" cue (earcon + optional spoken
announcement, `voice_preview_announce_generating`, default on) fires only
when synthesis is still running after a short delay, and the Preview/Test
button toggles to Stop while a preview is generating or playing. No true
pause/resume; Stop cancels outright. An in-flight external synthesis call
that gets superseded is not force-killed — it completes in the background
and its result is discarded.
```

- [ ] **Step 3: CHANGELOG**

In `CHANGELOG.md`, add an entry under the current unreleased/beta2 heading:

```markdown
- Voice preview (Voice Browser, and Test in Download Optional Components) now
  plays a "generating, please wait" cue for slow voice synthesis, never
  overlaps a prior preview with a new one, and its button toggles to Stop
  while a preview is generating or playing.
```

- [ ] **Step 4: Release notes**

In `docs/release notes/release0.9.0-beta2.md`, add an entry in the appropriate features/fixes section:

```markdown
- **Voice preview feedback.** Previewing a voice no longer overlaps a
  previous preview's audio or announcement. Slow voice synthesis now plays a
  short cue and (by default) says "Generating preview, please wait," and the
  Preview/Test button turns into a Stop button while a preview is active.
```

- [ ] **Step 5: Regenerate the rendered doc artifacts**

Run: `powershell -File scripts/gen.ps1 -RootPath "docs/user guide" -NoPause`
Run: `powershell -File scripts/gen.ps1 -RootPath "docs/Product Requirement Documents and Specifications" -NoPause`
Run: `powershell -File scripts/gen.ps1 -RootPath "docs/release notes" -NoPause`
Run: `powershell -File scripts/gen.ps1 -RootPath "." -NoPause` (regenerates `CHANGELOG.html`/`.epub` — **only stage `CHANGELOG.html`/`.epub` from this run**, since running gen.ps1 over `.` touches every `.md` in the repo; discard any other incidental diffs with `git restore --worktree <path>` before committing, exactly as done when this spec's own artifacts were generated)

- [ ] **Step 6: Commit**

```bash
git add "docs/user guide/userguide.md" "docs/user guide/userguide.html" "docs/user guide/userguide.epub" \
        "docs/Product Requirement Documents and Specifications/QUILL-PRD.md" \
        "docs/Product Requirement Documents and Specifications/QUILL-PRD.html" \
        "docs/Product Requirement Documents and Specifications/QUILL-PRD.epub" \
        CHANGELOG.md CHANGELOG.html CHANGELOG.epub \
        "docs/release notes/release0.9.0-beta2.md" \
        "docs/release notes/release0.9.0-beta2.html" \
        "docs/release notes/release0.9.0-beta2.epub"
git commit -m "docs: document voice preview feedback (user guide, PRD, CHANGELOG, release notes)"
```

---

## Final check

- [ ] Run the full touched-area test surface: `pytest tests/unit/core/test_voice_preview_sound_event.py tests/unit/core/test_settings.py tests/unit/ui/test_voice_preview_generation.py tests/unit/ui/test_voice_browser_dialog.py tests/unit/ui/test_optional_components_dialog.py tests/unit/core/test_optional_components.py tests/unit/core/test_sound_pack.py tests/unit/core/test_conversation_sound_events.py tests/unit/ui/test_sound_events_dialog.py -q`
- [ ] `ruff check quill/core/sound_events.py quill/ui/sound_events_dialog.py quill/core/settings.py quill/core/settings_specs.py quill/ui/main_frame.py quill/ui/voice_browser_dialog.py quill/ui/optional_components_dialog.py quill/ui/main_frame_speech.py`
- [ ] `mypy quill/core quill/io` (scoped, per project convention — `quill/ui` is gradually typed and excluded)
- [ ] Report the working tree state (clean vs. remaining diffs) and a summary of the 7 commits.
