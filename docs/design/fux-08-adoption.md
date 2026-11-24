# FUX-08: hear or see what a setting will do, app by app

**Date:** 2026-11-24
**Source:** FUX-08 in the family UX plan (`git show b7c6a1a04^:complete2.md`), held to [family-interaction-contracts.md](family-interaction-contracts.md). It is not one of the promoted pilots ([2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md), section 5), so the work here is limited to real gaps in settings the family already has. It adds no new panel, key, centre or settings surface: a preview is a button or a live change inside the window that already holds the setting.

## What a preview has to do

Every preview in the family, old and new, is held to the same five rules:

1. **Reached from the keyboard.** A real button (or a control whose change is heard at once), in the Tab order next to the setting it plays.
2. **Said once.** The preview's own sound and words, and one sentence only when nothing could be heard and the person needs to know why (sounds off, no sound in the scheme, the choice is silence). Nothing the screen reader already says (GATE-13).
3. **Never changes the saved value.** It plays what the window shows. Cancel, Close or Escape leaves the setting as it was, and any live change is put back.
4. **Stops.** Pressing the button again, pressing Escape, or closing the window stops it. Escape that stops a preview does not also close the window, the way Scribe's Play Sample works.
5. **Honest.** It uses the same rule the real moment uses, so a choice that falls back to words for real falls back to words in the preview.

## What the family already has

- **Scribe's Play Sample** (`quill/ui/scribe_convert_settings.py`): plays the chosen voice, becomes Stop Sample, and Escape stops it without closing the dialog. The model for rule 4.
- **Sound Scheme** (`quill/ui/sound_scheme_dialog.py`, QUILL and QUILL Lite): a Play button and "play each sound as I move through the list", nothing saved until OK.
- **Sound Enhancements in Radio** (`quill/ui/sound_enhance_dialog.py` with `on_live_change`): every slider and box is heard on what is playing a moment after it moves, and Cancel puts back the values it opened with.
- **Media Player's Audio tab** applies equaliser, boost and normalise live; there is nothing to keep or cancel.
- **Converter's Play Preview and Hear Original** (Ctrl+P, Ctrl+Shift+P): fifteen seconds with your settings or without, the same key stops, closing the window stops.
- **Weather's alert sound Play button**, **Studio's Preview voice**, **the Speech Hub's Preview Selected Voice**, and **Test Microphone** in Dictation Settings and Transcribe Set Up.
- **Scribe's feedback sound preview** (#2037, not merged yet): Play Success Sound and Play Failure Sound, saying why nothing played.

## The shared helper

`quill/ui/setting_preview.py` is the one place a feedback preview is built:

- `feedback_step(mode, ...)` resolves the family's "a sound, words, both or neither" choice through `quill.core.action_feedback.resolve`, the function the real moment uses, so a sound with no clip in the scheme speaks in the preview as it does for real.
- `edge_step(...)` is a start or stop moment with a "play sounds" box and a "say it" box, the rule dictation's `_announce_edge` follows.
- `PreviewSequence` plays a few steps a moment apart, once; the button again, Escape or closing the window stops it (`guard`). When every step is silent it says so in one sentence, and when the app's sounds are off it says that once.

Scribe's feedback preview (#2037) says the same three reasons in its own words; it can move onto this helper once both are merged.

## App by app

| App | Settings whose effect is not obvious | Preview today | The gap | What changed |
| --- | --- | --- | --- | --- |
| QUILL | Dictation feedback; voices, rate, volume and pitch; sound scheme; action and find-miss feedback; theme and font size | Sound Scheme; the Speech Hub's Preview Selected Voice; browse-mode WAV Preview | Dictation feedback could not be heard. The Speech Hub preview wrote the unsaved rate and volume into the live settings and kept playing after Escape or Close | Dictation Settings: **Hear Start, Phrase and Stop** (this pull request). The Speech Hub: planned, in the voices pull request |
| QUILL Lite | Dictation feedback; command and search-miss feedback; theme | Sound Scheme; Scribe Play Sample | Dictation feedback could not be heard | Dictation Settings: Hear Start, Phrase and Stop (the same window) |
| Radio | Sound Enhancements; reminder sound; dial hiss; output device | Sound Enhancements is live, and Cancel puts it back; App Sounds plays a sound on the chosen device | None that needs a button: the reminder and dial hiss are heard the next time they happen and say what they are | None needed |
| Cast | Sound Enhancements; speed; Volume Boost; Even Out Volume; action feedback | None. The Sound Enhancements window was heard only after Apply, which also saves | A pilot task ("change a podcast's speed and hear it take effect") had no way to hear an equaliser change before keeping it | Planned, in the Cast pull request: the Sound Enhancements window is heard live, and Close puts back what was not applied |
| Media Player | Equaliser, boost, normalise, skip silence | Live on the Audio tab | None | None needed |
| Converter | Effect, preset, Custom Effects | Play Preview and Hear Original | Custom Effects (loudness, gain, speed) is heard only after OK and Ctrl+P | Left: its preview has to render the file with unsaved effects through ffmpeg; Ctrl+P straight after OK is the honest path today |
| Transcribe | Dictation feedback, engine and model | Test Microphone in Set Up and Dictation Settings | Dictation feedback could not be heard | Dictation Settings: Hear Start, Phrase and Stop (the same window) |
| Inkwell | Dictation feedback | Test Microphone | Dictation feedback could not be heard | Dictation Settings: Hear Start, Phrase and Stop (the same window) |
| Studio | Voice, rate and speed for narration; audio processing | Speech Hub Preview; the Audio Studio wizard's Preview voice | Both previews kept playing after Escape or closing the window; the Speech Hub's also changed the saved rate and volume | Planned, in the voices pull request (the Speech Hub is shared with QUILL) |
| Beacon | High contrast, text scale, verbosity | Applied on OK | A visual setting is seen as soon as OK is pressed, and Beacon is not released | None now |
| Social | Notification channels; high contrast | None | Social keeps its own settings model in `standalone/social` | Left, for Social's own settings work |
| Weather | Alert sound and how many times it plays | A Play button | Play with a repeat count above one looped on a thread nothing could stop: Escape and closing Weather Settings left it playing, and each press added another loop | Planned, in the voices pull request |

## The acceptance list

- **A preview has a clear end and puts things back:** the button again, Escape, or closing the window stops it; Cast's live sound is put back on Close unless applied.
- **Shared versus app-only is clear before applying:** Dictation Settings is one window that four apps open, and says nothing is saved until OK. No new setting is shared (`family_preferences.py` is untouched).
- **Nothing silently synchronises keys, focus, microphones or credentials:** no preview reads or writes any of them; Test Microphone is unchanged.
- **A setting that needs a restart says so:** none of the settings previewed here needs one.
- **No extra confirmation for an ordinary reversible choice:** none added.
- **Undo without remembering the old value:** Cancel keeps the saved value; Cast's Close puts back the values the window opened with.
