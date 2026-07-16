# Reset Sound Enhancements to Default

Date: 2026-07-16
Status: Approved

## Problem

Quill Radio favorites can each carry their own Sound Enhancements (EQ +
compressor), overriding the shared default
(`RadioHistory.eq_bass_db/mid_db/treble_db/compressor_enabled`). The data
layer already supports clearing a station's override
(`RadioFavoritesStore.clear_enhancement_override`), but nothing in the UI
calls it -- there is no way to undo a per-station override, or to walk back
every favorite that has one, short of manually re-editing each station's
sliders to guess the shared default's current values (which doesn't even
truly clear the override -- it just copies values, so the station stops
tracking future changes to the shared default).

## Goals

- A per-station "Reset to Default" action that clears that station's
  override and goes back to following the shared default.
- A bulk action that resets every favorite's override at once, for people
  who want to get back to a single global sound.

## Non-goals

- Podcasts' equivalent per-show override (`PodcastSettings`) is a separate
  concept with its own dialog; this spec does not touch it.
- Resetting the *shared default itself* to some fixed neutral value (e.g.
  flat 0 dB) is not in scope -- "reset" here means "stop overriding the
  shared default," not "change what the shared default is."

## Design

### Per-station reset -- Sound Enhancements dialog

`SoundEnhanceDialog` (`quill/ui/sound_enhance_dialog.py`) gains an optional
constructor parameter:

```python
on_reset: Callable[[], None] | None = None
```

When provided, the dialog adds a "&Reset to Default" button next to Apply
and Cancel. Clicking it calls `on_reset()` synchronously, then closes the
dialog the same way Cancel does (`EndModal(wx.ID_CANCEL)` -- `show()`
returns `None`). The dialog itself stays ignorant of favorites/overrides;
the caller's callback does the real work. Podcasts' call site doesn't pass
`on_reset`, so it never sees the button -- no behavior change there.

`open_sound_enhancements()` (`quill/ui/main_frame_radio.py`) passes
`on_reset` only when there is something to reset:

```python
favorite is not None and favorite.has_sound_enhancement_override
```

The callback:

1. `self._radio_favorites.clear_enhancement_override(favorite.key)`
2. `self._save_radio_favorites()`
3. If `favorite` is the currently playing station
   (`self._radio_controller.state.station` matches by
   `station_uuid or stream_url`), push the shared default's values live via
   `self._radio_controller.set_enhancement(bass_db=history.eq_bass_db, ...)`
   so the audible change happens immediately, not just next play.
4. `self._announce(f"Sound Enhancements for {favorite.display_label}: back to the shared default.")`

Editing the shared default itself (`favorite is None`) never shows the
button -- there's nothing to "stop overriding."

### Bulk reset -- Preferences dialog

`PreferencesDialog` (`quill/ui/app_preferences_dialog.py`) gains a new
dataclass and constructor parameter, following the existing
`PreferenceCheckbox`/`PreferenceChoice` pattern:

```python
@dataclass(slots=True)
class PreferenceAction:
    name: str          # button label, carries the & mnemonic
    help_text: str      # accessible name
    on_click: Callable[[], None]
```

```python
actions: list[PreferenceAction] | None = None
```

Action buttons render above the Save/Cancel row. Unlike checkboxes/choices,
clicking one fires `on_click()` immediately -- it is independent of
Save/Cancel and does not require or wait for the rest of the dialog to be
saved.

Quill Radio's `_open_preferences()` adds one action, "Reset &All Stations'
Sound Enhancements...". Its `on_click`:

1. Collects every favorite with `has_sound_enhancement_override`.
2. If none: `self._announce("No stations have their own Sound Enhancements to reset.")` and stop.
3. Otherwise, confirm: `"N station(s) have their own Sound Enhancements. Reset all of them to the shared default?"` (Yes/No, matching the existing confirm-dialog pattern used elsewhere in this app, e.g. `RadioCloseConfirmDialog`'s Yes/No/Cancel style but here just Yes/No).
4. On Yes: `clear_enhancement_override(key)` for each, one `_save_radio_favorites()` call afterward (not per-station), then the same live-update-if-playing check as the per-station path, then `self._announce(f"Reset {n} station(s) to the shared default.")`.
5. On No or Cancel: no-op, no announcement beyond whatever the confirm dialog itself gives.

QUILL Cast (the other consumer of `PreferencesDialog`) simply doesn't pass
`actions`, so it is unaffected.

## Testing

Both are pure logic once the wx button click is simulated, following the
existing `tests/unit/ui/test_radio_app_close_and_keys.py` pattern (bound
methods driven directly with `SimpleNamespace` stand-ins, no real `wx.App`
needed):

- `SoundEnhanceDialog` shows/hides the Reset button based on `on_reset`
  being provided; clicking it calls the callback exactly once and the
  dialog's `show()` returns `None`.
- `open_sound_enhancements()`'s `on_reset` callback: clears the override,
  saves favorites, announces, and pushes `set_enhancement` live only when
  the reset favorite is the one currently playing (not when a different
  station is playing, not when nothing is playing).
- The bulk action: zero-override case only announces, doesn't confirm;
  confirmed bulk reset clears every overridden favorite and saves once;
  declining the confirm leaves every override untouched; live-update fires
  only if the currently playing station was among the reset ones.

## Open questions

None -- resolved via brainstorming: reset means "stop overriding" (not
"force flat"); bulk action lives in Preferences; per-station reset is a
button in the Sound Enhancements dialog wired via callback.
