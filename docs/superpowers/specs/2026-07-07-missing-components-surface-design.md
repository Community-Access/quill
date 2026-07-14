# Unified "missing component" surface — design

Closes GitHub issue #874.

## Problem

`quill/ui/optional_components_dialog.py` (Help > Download Optional
Components, shipped 2026-07-01 closing #773) already provides a single,
accessible list of every optional component with install state and a
one-click fetch — most of what #874 asked for already exists. Two real gaps
remain:

1. **Piper voices aren't tracked at all.** `gather_optional_components()`
   covers whisper.cpp, Vosk, Kokoro, eSpeak, DECtalk, ffmpeg, Pandoc, the
   braille pack, libmpv, and MathCAT, but not Piper's engine executable.
2. **The dialog is only reachable from the Help menu.** None of the
   "component missing" error messages a user actually hits the gap from
   (Kokoro synthesis failure, eSpeak/DECtalk/Piper pre-flight checks, Pandoc
   import/export failures, and three silent-fallback cases) link into it. A
   user has to already know the dialog exists rather than being routed there
   from the point of failure — the actual "meet people where they are" ask.

## Non-goals

- No changes to the core status model beyond one new `piper` entry —
  `optional_components.py` and `release_assets.py` already do the tracking
  #874 asked for; this is a UI-layer wiring pass over existing state.
- Not touched: Whisper's dictation-preflight prompt and the braille-pack
  install prompt. Both already offer a direct one-click action of their own;
  routing them through the generic picker would add a dialog hop and lose
  that directness for no benefit.
- Not adding per-voice Piper rows. Piper is represented as one row (engine
  executable present/absent), matching the existing eSpeak/DECtalk pattern;
  individual voice selection and download stays in the Voice Browser.

## Design

### 1. Add Piper to the component catalog

`quill/core/optional_components.py`: new `_piper_installed()` detector
(`quill.core.read_aloud.discover_piper_executable() is not None`) and a new
`OptionalComponent("piper", ...)` entry in `gather_optional_components()`,
category `VOICES`, alongside Kokoro/eSpeak/DECtalk.

### 2. Pre-focus the picker

`show_optional_components_picker()` gains an optional `preselect: str = ""`
parameter. When non-empty and present among `components`, that row is
selected/focused instead of row 0. Backward compatible — every existing
caller (just the Help-menu entry point today) keeps working unchanged.

### 3. Two dispatch helpers on MainFrame

**Hard blockers** (the action cannot proceed at all without the component;
fire every time, matching current frequency):

```python
def _offer_optional_component(self, component_id: str, message: str) -> None:
    """Show `message`; if the user says yes, open the components picker
    pre-focused on `component_id`."""
    wx = self._wx
    if self._show_message_box(
        f"{message} Open Download Optional Components to get it?",
        "Component Needed",
        wx.ICON_ERROR | wx.YES_NO,
    ) == wx.YES:
        self.open_optional_components(preselect=component_id)
```

Rewires 5 existing plain-`wx.OK` sites to call this instead, unchanged
message text otherwise:

- `generate_speech_audio()` pre-flight guards for `kokoro`, `espeak`,
  `dectalk`, `piper` (`quill/ui/main_frame.py`, ~18230-18290).
- Pandoc import/export failures (`quill/ui/main_frame.py`, ~7969-8010,
  ~8077-8078) — component_id `pandoc`.

**Soft fallbacks** (the feature still works via a fallback; component_id
absence is degraded quality, not a block — nag at most once, ever):

```python
def _nudge_once(self, component_id: str, message: str) -> None:
    if component_id in self.settings.nudged_missing_components:
        return
    self.settings.nudged_missing_components.append(component_id)
    save_settings(self.settings)
    wx = self._wx
    if self._show_message_box(
        f"{message} Open Download Optional Components to get it?",
        "Optional Upgrade Available",
        wx.ICON_INFORMATION | wx.YES_NO,
    ) == wx.YES:
        self.open_optional_components(preselect=component_id)
```

New call sites (none exist today — these fallbacks are currently silent):

- `ffmpeg`: when the Export to Speech Audio dialog builds its format list
  and compressed formats are unavailable (`generate_speech_audio()`, where
  `formats` is built, `quill/ui/main_frame.py` ~18178-18192).
- `libmpv`: `player_panel.py`'s `create_engine(...)` call (~line 49) already
  falls back to `wx.media` whenever `audio_engine.preferred_backend()` returns
  `"wx"` because `find_libmpv()` found nothing — nudge right after that call
  when the backend chosen was `"wx"` for that reason, not the rarer
  found-but-broken-DLL case (which logs and falls back silently on its own
  merits, per `create_engine`'s docstring, and is out of scope here).
- `mathcat`: where "Read this part aloud" falls back to template-based
  equation reading instead of MathCAT's natural speech.

### 4. New persisted state

`Settings.nudged_missing_components: list[str] = field(default_factory=list)`
— same shape as the existing `applied_recommended_updates` field. Marking a
nudge "shown" is permanent (not per-session): once a user has seen the
ffmpeg/libmpv/MathCAT nudge, it never fires again regardless of their answer.

## Testing

- `optional_components.py`: `piper` entry present with correct
  installed/not-installed detection, mirroring the existing detector tests.
- `show_optional_components_picker`: source-contract test asserting
  `preselect` exists and is used instead of an unconditional row-0 select
  (matching this beta-2 pass's established wx-dialog test convention —
  constructing a real `wx.Dialog` isn't exercised in this suite).
- Each of the 8 rewired/new call sites: source-contract test asserting the
  method body calls `_offer_optional_component`/`_nudge_once` with the
  correct `component_id`, matching the pattern in
  `test_main_frame_speech_export_contract.py`.
- `Settings.nudged_missing_components`: default-empty and round-trip
  persistence test, matching existing `Settings` field tests.
- `_nudge_once`: a direct unit test (not source-contract, since the logic is
  real and pure enough to stub) verifying it fires once, appends to
  `nudged_missing_components`, persists via `save_settings`, and is a no-op
  on a second call with the same `component_id`.

## Files touched

`quill/core/optional_components.py`, `quill/core/settings.py`,
`quill/ui/optional_components_dialog.py`, `quill/ui/main_frame.py`,
`quill/ui/audio_studio/player_panel.py`, plus new/updated tests in
`tests/unit/core/test_optional_components.py`,
`tests/unit/core/test_settings.py`, and new `tests/unit/ui/` contract test
files.

## Where the MathCAT "Read this part aloud" fallback lives

To confirm during planning: the exact call site inside the equation-reading
handler where MathCAT unavailability currently falls back to template
reading (per `optional_components.py`'s `_mathcat_installed` docstring
reference, "Insert > Explore Equation Structure..."). Not yet located to a
line number; the implementation plan should pin this down as its first
step, the same way the libmpv site was pinned down above.
