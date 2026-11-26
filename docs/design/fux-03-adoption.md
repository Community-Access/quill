# FUX-03: what is playing or recording here, and where the sound goes

**Date:** 2026-11-24
**Source:** FUX-03 in the family UX plan (`git show b7c6a1a04^:complete2.md`), with the audio rule in [2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md) (section 4: each app owns its own audio, and "what is playing or recording here?" is answered by each app about itself; there is no family mixer), held to [family-interaction-contracts.md](family-interaction-contracts.md). Radio first, then Studio, then the other apps that play or record. Earshot and macOS are out of scope.

## What an answer has to do

Every app that plays or records is held to the same four questions:

1. **Can the person ask?** One menu item and key, reachable through the Command Palette, that says what is playing or recording in this app and on which device. It is said once, only when asked, and goes through the announcement service, so it is brailled too. Nothing is announced in the main window that the person did not ask for.
2. **Does it name the device, and say when the device has gone?** By the name Windows gives it, not "System default" alone: the system default is followed by the device that is the default today. A chosen device Windows does not list as connected is said to be so, because a configured route is not proof that sound reaches it. When a device disappears, the app says which route was affected and does not silently move a private route (a monitor, a microphone) somewhere new. When it comes back, recovery is a deliberate choice.
3. **Does it say when another family app holds the microphone?** The family's microphone lock (`quill/core/dictation_owner.py`, `MicrophoneLock`) already refuses a second recorder and names the holder. The answer to question 1 also names a holder that is not this app.
4. **Are play and record states somewhere the person can look?** The status bar, a status readout, or the title, as the app already does it. No new panel.

## The shared part

`quill/ui/audio/sound_route.py` keeps the words and the device lookup the same in every app, so two apps never describe one headset in two ways:

- `output_device(saved)` and `input_device(saved)` look the saved device up in Windows' list of active endpoints (`quill/platform/windows/audio_routing.list_devices`), by its endpoint GUID for a playback device (the spelling the audio engines save, `wasapi/{guid}`) and by name for a microphone. No audio engine is started. When Windows cannot be asked, the app's own words are used and nothing is claimed about the connection.
- `on_device(device)` is "on Headphones (USB)", "on Speakers (Realtek), the system default" or "on Headphones (USB), not connected". A device is offered as the way back only when Windows answered (`Device.known`); a microphone saved by a name two devices answer to is not guessed.
- `microphone_note(asker)` is one sentence when another family app holds the microphone.
- `COMMAND_LABEL` and `DEFAULT_KEY`: **Where Is the Sound?** on **Alt+Shift+A**. Alt+Shift+A was checked against every media app's menus and keymaps (`family_menu_chords.json` and `APP_KEYMAPS`) on 2026-11-24 and is free in Radio, Studio, Cast, Media Player, Converter and Transcribe. In QUILL and QUILL Lite it is Expand Abbreviations, so the editors answer through their existing status commands instead (below).

## App by app

| App | Can the person ask? | Device named, and its loss | Another app on the microphone | Where state shows | What changed |
| --- | --- | --- | --- | --- | --- |
| Radio | What's Playing? (Ctrl+T) said the station and track, never the device | Output Device (Ctrl+Shift+D) chose it; a device that would not open was given back and said once (`output_device_guard`), then forgotten | Radio does not record from a microphone; Dictate Here asks QUILL Transcribe | The Now playing field, the status bar's Now playing cell, the tray tooltip | **Audio > Where Is the Sound?** (Alt+Shift+A, this pull request): the player and its device by name, a device Windows does not list, the classic Windows Media control (Windows decides the device), a device that could not be opened earlier and the way back once it is connected, the background station or mirror and its device, that recordings take the stream, and a family app on the microphone |
| Studio | Recording status (Ctrl+Alt+Shift+T) named the sources as "Microphone" and "System sound" only | The microphone and the sound card reconnect by identity and say so; Recording status did not say a source was gone | The lock refuses and names the holder when a recording or broadcast starts | "Recording" at the front of the title, the Recording status window, the tray tooltip | **Recording status** names the device behind each sound and says when one is disconnected and silence is going in. **Capture > Where Is the Sound?** (Alt+Shift+A): where Studio's players play (the device Windows gives Studio), the recording and broadcast, the recording microphone and whether it is connected, and another app on the microphone. The quick test in Record a demonstration already plays back what went in |
| Media Player | Read Status Bar (Shift+F6) and Where am I? say state and position; no device | Output Device (Ctrl+Shift+K) chooses; nothing is said when the device disappears | Does not record | Status bar fields State, Position, Chapter, Sleep, Backend | Planned, second pull request |
| Cast | Say Current Episode (Ctrl+T) and Player Information (Ctrl+I); no device | Output Device (Ctrl+Shift+K) chooses; on the Windows Media engine an absent device was reported as chosen (the readback in `output_routing.set_engine_output_device` never ran) | Does not record; Dictate Here asks QUILL Transcribe | Status bar cells; the title shows the Inbox count | Planned, second pull request |
| Transcribe | Dictation Status (Alt+F9) says state, engine and language; never the microphone | Choose Microphone (Ctrl+Shift+M); a microphone lost mid-dictation pauses and says so, and resumes when it comes back | Takes the lock; refuses with the holder's name | The state line, the tray tooltip | Planned, third pull request |
| Dictation in QUILL, QUILL Lite and Inkwell | Dictation Status (Alt+F9) in QUILL and QUILL Lite; no device | The microphone in Dictation Settings; lost mid-dictation pauses and resumes | Takes the lock | QUILL Lite's Dictation status cell; QUILL's status bar message | Planned, third pull request |
| QUILL read-aloud | No status command; the status bar's Read Aloud cell | Always the system default (`winsound`), with no choice; a device that fails is skipped silently | Does not record | The Read Aloud cell, which tests for a state the controller never uses | Planned, third pull request |
| QUILL Lite | Has no read-aloud of its own; dictation as above | As above | As above | As above | With dictation, third pull request |

## What each app does not do

- **No app moves another app's sound.** Nothing here pauses, ducks or reroutes anything outside the app that is asked; Studio Mixer, which can move a program, is still something the person opens and chooses in.
- **No new announcement nobody asked for.** Every sentence above is the answer to a command. The device rescue Radio already had still speaks once when it happens; it is a failure, which is always spoken.
- **Recovery is chosen, never automatic.** When a device comes back, the answer says so and names Output Device; the app does not move the sound back by itself.

## The acceptance list

- **Play Radio while rehearsing a Studio recording and tell each route without sight:** Alt+Shift+A in Radio names the station and its device; Alt+Shift+A in Studio names where Studio plays, the recording and the microphone behind it. Needs a live check with two devices.
- **Listen back to a short test capture:** Record a quick test in Studio's Record a demonstration plays back what went in; the Studio guide says a chosen microphone is not proof of what was captured, and the answer only says "not connected" for a device Windows does not list.
- **Identify and recover a disconnected device:** Radio names the device that could not be opened, and when it is connected again, the way back; Studio's Recording status says which source was disconnected. Needs a live check: unplug a USB headset mid-play and mid-recording.
- **Limits are stated:** the classic Windows Media control's device is Windows' to choose, and Radio says so; Studio has no output device of its own and says the device is the one Windows gives it.

## Left, and why

- **Studio's audiobook player is not reported as playing or paused.** It lives in the Chapter Workbench window, which has its own Where am I?; Studio's main window does not hold it.
- **QUILL's voice capture** (wake word, conversation, voice commands) does not take the family microphone lock. It is QUILL's speech mixin, and the third pull request looks at it with dictation.
