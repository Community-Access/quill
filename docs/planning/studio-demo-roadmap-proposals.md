# QUILL Studio: record, preview, mix and broadcast

Date: 2026-10-29 (second revision, the same night). For Jeff to review. Nothing here is built unless it says **Built**.

Sources: `do.md` (section 8, F01, F02); the earlier media parity study (its Media section: sound control, loop-back recording, recording your own voice); `docs/planning/QUILL-Studio-PRD.md` (sections 1.3, 5, 6, 7A, 8, 9, 9A, 10A, 10C); `docs/design/quill-studio-capture-milestone.md`. Audio editing and multitrack editing are out of scope, as asked; nothing below cuts, trims or arranges recorded audio.

Every item has an ID so a review can say "yes R1 to R6, later D4, no X2". Effort: **S** an evening, **M** a day or two, **L** several days, **XL** a project of its own.

## Decisions already made

| Question | Answer | Date |
|---|---|---|
| How to choose picture sources | Separate **Screen** and **Camera** check boxes, each on or off; no four-way choice | 2026-10-29 |
| Direct streaming to Icecast and SHOUTcast | Wanted. This reverses PRD section 10C.5, which listed it under "considered and not adopted"; the PRD is updated when this is built | 2026-10-29 |
| Ambition of this document | Dream large: the greatest flexibility, without giving up privacy, safety or the "nothing is changed without you" rule | 2026-10-29 |
| What AI reviews | The **whole video**, or a **section the user chooses** (from a start time to an end time, or between two markers) | 2026-10-29 |
| The Mixer | **One window** with tabs: Programs, Devices, Sources and buses, Scenes, Stream | 2026-10-29 |
| Archiving a stream | **Offered, and the user decides** each time and in each saved setup; nothing is assumed | 2026-10-29 |
| Stream options | **Rich and in plain words**: title, description, genre, website, format, quality, stereo or mono, sample rate, and more (section 6, S15) | 2026-10-29 |
| Next large items | **Both**: window recording that follows the window (R10), and the live engine for preview, monitoring and buses (P1 with M3) | 2026-10-29 |
| ASIO sound cards | **Wanted**: professional audio interfaces through ASIO, beside WASAPI (section 5, M13) | 2026-10-29 |
| Pictures and YouTube videos | **Wanted**: make a picture with AI in conversation, then turn a picture and an audio file (recorded or chosen) into a video ready for YouTube (section 6B) | 2026-10-29 |
| Getting to main | Land in QUILL's `main` only through a pull request with green checks; nothing is pushed or merged without that | 2026-10-29 |
| Language | Simple and understandable for users everywhere: plain words first, technical names only where a user needs them to match a server's settings | 2026-10-29 |
| Do Not Disturb and keep awake | **Must have.** Both are options in every recording and stream, on by default for recordings planned over 15 minutes, and always restored afterwards | 2026-10-29 |

## Where things stand tonight

**Built** in `S:\QUILL-demo`, branch `feat/studio-demo-recording`, not committed yet: screen, sound and camera recording to one checked MP4; per-source sound with the screen reader private by default; system sound without the screen reader; Sounds you hear (per-program mute and volume for the listener); camera overlay with on-device face framing advice; the spoken check; 5-second test; pause, markers, microphone mute, status, emergency stop, discard and crash recovery; the independent after-check with Verified, Needs review and Failed; user guide, changelogs and PRD 7A.7. 116 feature tests pass; the four modules that were over GATE-11's size budget are split; the full gate scorecard is rerunning.

Not verified: a live microphone or camera recording (not allowed unattended), a positive face detection with a person in front of the camera, screen-reader acceptance, and a 30-minute alignment run.

## 1. Kernel-mode drivers: do we need one?

**Short answer: no, for everything in this document except one thing, and that one thing has a good no-driver alternative.** QUILL keeps its PRD rule (section 1.3): no feature *requires* a virtual audio kernel driver, and QUILL never ships or silently installs one.

| What we want to do | User-mode Windows API that does it | Driver needed? |
|---|---|---|
| Record one program's sound, or everything except one program (the screen reader) | Process loopback (`ActivateAudioInterfaceAsync`, include or exclude a process tree), Windows 10 2004 and later. **Built.** | No |
| Record everything a playback device plays | WASAPI endpoint loopback | No |
| Record any microphone or line input | WASAPI capture (shared or exclusive) | No |
| Mute, unmute or set the volume of any program for the listener | Core Audio sessions (`ISimpleAudioVolume`). **Built.** | No |
| Move one program to a different sound card (per-app output device) | The Windows audio policy interface behind Settings, App volume and device preferences (Windows 10 1803 and later), user-mode | No (undocumented interface, so wrapped and checked) |
| Set the Windows default and communications devices | The `IPolicyConfig` COM interface that Windows sound utilities use | No (undocumented interface, so wrapped and tested defensively) |
| Change a recording input's level and mute | `IAudioEndpointVolume` on the capture endpoint | No |
| Live monitoring of the mix in headphones, mixing, effects, meters | A user-mode real-time engine (WASAPI or PortAudio callbacks) in a helper process | No |
| Stream to Icecast, SHOUTcast, RTMP or SRT servers | Network output from FFmpeg or Studio's own source client | No |
| Send Studio's **video** into Zoom, Teams or OBS as a camera | `MFCreateVirtualCamera`, Windows 11 (build 22000 and later), user-mode and driver-free | No |
| Send Studio's **audio mix** into Zoom, Teams or Discord **as a microphone** | Windows has no user-mode virtual microphone API. Options: (a) the user installs VB-CABLE or a similar signed driver (PRD MX-004, never bundled); (b) the meeting program listens to a real output Studio plays into ("CABLE Input"); (c) stream to the meeting through its own RTMP ingest where it has one (Teams and Zoom both offer RTMP for webinars). | **Yes, for a true virtual microphone only** |
| Split one screen reader's speech into "demo" and "private" utterances | Not possible from outside the reader. Possible with reader cooperation: an NVDA add-on or JAWS script that sends tutorial speech to a second synthesizer instance on a different device (MX-141) | No driver; reader cooperation |
| Capture protected (DRM) video or the secure desktop | Not done, ever. Recorded as black and reported | Never |

**Should QUILL ever write its own driver?** Not recommended. A kernel audio driver needs an EV code-signing certificate, Microsoft attestation signing or WHQL through Partner Center, the Hardware Lab Kit, and a driver-level support burden (blue screens are the failure mode, on the machines of blind users who cannot see a stop error). The one gap it fills, a virtual microphone, is covered by VB-CABLE for users who want it and by the streaming and output-device routes for everyone else. If Microsoft ships a user-mode virtual audio device API (as it did for cameras), QUILL adopts it at once (**K3**).

- **K1. VB-CABLE awareness, never installation** (MX-004, MX-127, MX-128). Detect CABLE endpoints, name them in plain words ("CABLE Input is where Studio plays; CABLE Output is what Zoom records"), map them as a mixer destination, and run the cable test (tone out, record back, report nothing, gaps or clean). Offer the vendor's download page with consent; never fetch or run an installer. (M)
- **K2. Driver-free virtual camera** on Windows 11: send Studio's picture (screen, camera, overlays, captions) into any meeting or broadcast program as a camera named "QUILL Studio". (L)
- **K3. Watch for a user-mode virtual audio API** and adopt it when one exists. (tracking item)

## 2. Every combination of picture and sound

The window gets two check boxes, **Screen** and **Camera**, and the Sound sources list. Any combination is valid, including nothing but sound, a picture with no sound, and a screen with a camera corner. A recording with nothing chosen at all is a Stop in the check.

- **R1. Screen and Camera check boxes.** **Built** 2026-10-29. Screen on and Camera off records the screen (today's behaviour). Camera on adds the corner picture, or fills the frame when Screen is off. Both off is a sound-only recording. (M)
- **R2. Sound-only formats.** **Built** 2026-10-29 (M4A, MP3, WAV, FLAC, Opus). WAV (lossless), FLAC, M4A (AAC), MP3 and Opus, with bit rate. The after-check becomes "one audio stream, right length, each source present, no clipping, loudness measured". (S)
- **R3. Picture with no sound.** **Built** 2026-10-29. A silent soundtrack (some sites reject video without one) or no audio stream; the check and result say which. (S)
- **R4. Loop-back recording of any playback device** (**Built** 2026-10-29 as "Everything playing on" a sound card) as a one-step preset: "Record what my headphones are playing". (S)
- **R5. Camera capabilities probed, not assumed:** resolutions and frame rates from DirectShow; camera-only recordings use the camera's own size. (S)
- **R6. More output choices.** MP4 (H.264), MKV, WebM (VP9 and Opus), MOV; H.265 and AV1 when the encoder exists; hardware encoders (NVENC, Quick Sync, AMF, Media Foundation) as an opt-in with a speed test. (M)
- **R7. Several sound tracks inside one video**, one per source, beside the mixed track, for people who edit elsewhere. This is a recording choice, not editing in Studio. (S)
- **R8. Several cameras and several screens** at once, each with a position and size, laid out by name ("camera 2 top left, 20 percent"). (L)
- **R9. Region recording** that keeps the picker's guided portions (top half, middle quarter) and UI Automation elements, with the same "never broaden" rule as screenshots. (M)
- **R10. Window recording that follows the window** (Windows.Graphics.Capture, PRD spike S1): a covering window is not recorded and moving the window is followed. The biggest remaining version 1 gap. (L)
- **R11. Scheduled recordings**: start at a time, for a length, with the same check run first and its result kept. (M)
- **R12. Instant replay buffer**: keep the last 30 seconds to 10 minutes in memory, saved only on a key ("save that"), for the moment something went right without warning. Off by default; the microphone and screen reader rules still apply. (M)

## 3. Preview and rehearsal before a long recording

- **P1. Live preview: hear the exact mix before you record**, in headphones, with spoken levels on request. Never recorded. Shares the real-time engine with the mixer (M3). (M)
- **P2. Rehearsal recordings** (**Built in part** 2026-10-29: the quick test lasts 5 seconds to 10 minutes; keeping a rehearsal and AI review of it are still to do) of any length, kept until deleted, with the full after-check and AI review (A1). (S)
- **P3. "Ready for an hour?" check** (**Built in part** 2026-10-29: a 3-second dropped-frame trial, battery and pending-restart warnings; Do Not Disturb and keep awake are P7; the microphone level check and readable-text check are still to do), added when the planned length is over 15 minutes: disk space for the length plus margin; a 10-second encoding speed test at the chosen settings with a suggestion if this computer cannot keep up; battery level, estimated time and power plan; sleep, screen saver and display-off timers (Studio keeps the computer awake while recording and says so); notifications and Do Not Disturb; a pending Windows Update restart; microphone noise floor and headroom from a "say a sentence" check; the demonstrated program's text size versus the output size, from OCR of the trial picture. (M)
- **P4. Planned length and safety splits**: start a new file every 30 or 60 minutes if wanted, so one failure never costs the whole hour. (S)
- **P5. Named setups** ("JAWS tutorial", "Zoom demo", "Friday show") holding target, sources, levels, camera, streaming destinations and folder. The microphone's on state is still never saved (MX-179). (S)
- **P6. Setup fingerprint** (PREFLIGHT-007): when devices, displays or the screen reader changed since the last good session, say what changed and offer a rehearsal. (S)
- **P7. Do Not Disturb and keep awake (must have).** **Built** 2026-10-29. Two options in the Record a demonstration window and in every stream setup: **Turn on Do Not Disturb while recording** and **Keep the computer awake while recording**. On by default for a planned length over 15 minutes, and offered for any recording. Keep awake uses `SetThreadExecutionState` (system and display) and also stops the screen saver; it lasts exactly as long as the recording or stream and is released on stop, discard, crash recovery and exit. Do Not Disturb uses Windows' own notification setting (Focus on Windows 11, Focus Assist on Windows 10), remembers what it was before, and restores that afterwards, even after a crash (restored on next launch). The check says which are on and warns when Do Not Disturb could not be set, so notifications may appear in the picture. (S)
- **P8. Other one-key fixes where safe**: close a named notification app, switch the screen reader to a second sound card, pause Windows Update for the length of the recording, each confirmed and undone afterwards. Never a blanket admin prompt or a driver install (PREFLIGHT-005). (M)

## 4. AI that helps before and after (opt-in, consent per provider, off in Safe Mode)

- **A1. Ask AI about a recording or rehearsal: the whole video, or a section you choose.** **Built in part** 2026-10-29: frames from the whole video or a chosen stretch, as one labelled contact sheet, with the stretch's transcript when captions exist, in the Screenshot Inspector's conversation. Still to do: sending the video itself to providers that accept video, and choosing a stretch by markers. Choose **Whole video**, or a section by start and end time or between two markers ("from marker 3 to marker 4", "the last 2 minutes"). Studio sends the video itself to providers that accept video (Gemini, and others as they add it), with sound, so the AI hears and sees what happened; for providers that take only images, it sends frames from the chosen stretch (every second or two and at every scene change) plus a local transcript of the same stretch. A long video is sent in pieces the provider accepts, each answered in context. Answers cite times, and the frame inspector jumps to any cited time. The approval names the provider, the stretch, its length and size, and an estimate of the cost where the provider publishes one. Follow-up questions stay grounded in the same stretch unless you choose another. (M)
- **A2. Pre-recording coach.** A trial frame, 10 seconds of sound and the stated goal; back come recommendations you accept or ignore. (S after A1)
- **A3. After-recording review**: suggested chapters with titles, long silences, restarts, filler words, a title, description and tags for YouTube, a plain summary. Markers and text only. (M)
- **A4. Camera coach beyond faces** (VIS-005): lighting, headroom, background, blur, from one approved frame. The local face detector stays the free default. (S)
- **A5. Captions and transcript files** (**Built** 2026-10-29 from the result window; burned-in captions still to do) beside the video, transcribed locally (SRT, VTT, plain text). Optional burned-in captions as a recording option. (S)
- **A6. Audio description draft** (VIS-008): AI drafts descriptions of visual events at their times, for a human to review and record. (M)
- **A7. Live co-pilot while recording**, opt-in and silent unless asked: "did the dialog open?" answered from the latest frame, through a system-wide key. Spoken into headphones only; never into the recording. (M)
- **A8. Local-only AI path**: the same questions answered by a local vision model through Ollama when the hardware allows, so nothing leaves the machine. (S, reuses shared AI settings)

## 5. The Studio Mixer

All of Windows sound in one place: output devices with Set default and Set communications, every program's volume, mute and sound card, recording inputs with level and mute, loop-back recording, Refresh, and screen reader routing, plus buses, monitoring and safety. One window, tabs, Ctrl+Alt+Shift+M (Sounds you hear becomes its first tab).

- **M1. Programs, just like Windows** (**Built** 2026-10-29 in the Studio Mixer: volume, mute, playing now and the sound card; balance and "only this program" still to do). Every program that is playing sound, with:
  - **Volume up and down** with the arrow keys (1 percent) and Page Up and Page Down (10 percent), the new level spoken by the control itself, and a number field for an exact percentage.
  - **Mute and unmute** with Space.
  - **Sound card**: move a program to a different output, such as a browser to the speakers while the screen reader stays in the headset, exactly as Windows Settings, App volume and device preferences does. Choose "Default" to send it back. Windows remembers the choice for that program. This uses the same user-mode Windows interface that Settings uses (no driver); because Microsoft does not document it, Studio checks the result and says plainly when a Windows version refuses.
  - **Balance** (left and right) where the program's session has two channels.
  - Spoken peak level on request, and "only this program for me" (every other program muted for the listener) with one key to restore. (M)
- **M2. Devices** (**Built** 2026-10-29: default and communications devices, recording level and mute; test sound and the "restore my sound" key still to do): playback and recording devices; Set default and Set communications; input level and mute; a test sound; Refresh. Safety rule from do.md F01: a change can never leave the screen reader silent without a spoken "restore my sound" key. (M)
- **M3. Sources and buses**, the heart of it (PRD 5.2, UX-004): a spreadsheet-like list, one row per source, with columns for level, mute, solo, and a send to each bus: **Monitor** (your headphones), **Recording**, **Stream** (section 6), **Meeting** (a VB-CABLE or chosen output), and user buses. Keys from MX-151: Space mute, Left and Right fine level, Shift for coarse, S solo, H monitor, R record, L live (stream), Enter details, F find. Units always spoken. (L)
- **M4. Independent monitor level** (MX-177), so headphone comfort never changes the recording. (S)
- **M5. Effects per source**, all as native lists and number fields (MX-131, MX-139): high-pass, noise gate, compressor, limiter, EQ, de-esser, noise reduction (RNNoise or FFmpeg's `arnndn`), delay for sync. Bypass and reset per effect. (L)
- **M6. Ducking** (MX-134, MX-138): music ducks under the microphone, keyed by the microphone being open, with depth and timing in dB and milliseconds. (M)
- **M7. Meters and loudness on request** (MX-136): peak, RMS, integrated LUFS and true peak of any source or bus, spoken when asked; a clipping sound in headphones only. (S)
- **M8. Scenes** (MX-160 to MX-165): save, load, import and export mixer states; any change that newly sends private sound to a public bus is previewed in words and confirmed (MX-123, MX-166). (M)
- **M9. Screen-reader routing helpers** (do.md F01): show and change which device JAWS or NVDA speaks on, so speech stays in headphones while the program plays on speakers. (M)
- **M10. Emergency keys** (MX-178, TRAY-007): Mute everything public, and Stop all recording, each with a second chord, confirmation-free. (S)
- **M11. Mix-minus for calls** (MX-129): send a meeting everything except that meeting's own sound, held by stable identity. (M)
- **M12. Controllers**: MIDI faders and buttons and Stream Deck keys mapped to any mixer action, with the same spoken feedback as the keyboard (MX-157). (M)
- **M13. ASIO sound cards (wanted).** **Built in part** 2026-10-29: an opt-in preference loads the ASIO-enabled PortAudio already shipped inside `sounddevice`, and ASIO inputs appear as microphones for recording. Still to do: ASIO outputs for the Monitor and Stream buses (with the live engine), the buffer-size setting, and the third-party notice for the ASIO SDK in that DLL, which must be in `docs/legal/` before a release turns this on. Professional audio interfaces through ASIO, beside WASAPI, for the lowest delay and for interfaces whose Windows drivers are poor. Each input channel of an ASIO card becomes a named source in the mixer and in Record a demonstration ("Input 1, Shure SM7B"), and outputs can carry the Monitor or Stream bus. Plain-word settings: buffer size shown as milliseconds of delay, sample rate, and which channels to use. Studio warns when another program has the ASIO card, because most ASIO drivers allow only one program at a time. How: a PortAudio build with ASIO enabled, used through `sounddevice` (the ASIO SDK is free from Steinberg under its licence, which is recorded in third-party notices before shipping; nothing is compiled from the SDK into QUILL's own code). Where a card has no ASIO driver, FlexASIO or ASIO4ALL are explained as optional, user-installed choices, never bundled. (L)
- **M14. WASAPI exclusive mode** as the other low-delay choice for a single interface, with a plain warning that other programs (including the screen reader, if it uses that card) go silent on that device while Studio holds it. (M)
- **M15. Automation of levels over time is not offered**: that is editing, out of scope by request.

## 6. Live streaming to Icecast, SHOUTcast and beyond

Studio becomes a source client: what you hear on the Stream bus goes to the server, and nothing else. It works for an audio-only radio show (the PRD's scenario 2), a demonstration streamed while it is recorded, or both at once.

**Control of what goes out is the whole point:**

- The **Stream bus** is its own send in the mixer (M3). Each source has a Stream on or off and its own stream level, independent of the recording.
- The screen reader's send to Stream is off by default and needs confirmation, exactly as for recording (MX-122).
- Studio's own cues, previews and monitor-only material can never reach the Stream bus (MX-008, MX-127).
- **Going live runs a spoken preflight** (MX-166): where it goes, what is in it, whether the microphone is in it, and every Stop and Warn (wrong password, mount in use, bit rate not accepted, microphone absent from the stream, stream silent). Enter goes live.
- **Mute everything public** (M10) cuts the stream to silence or a holding sound without disconnecting; the recording continues if wanted.

**Servers and formats:**

- **S1. Icecast 2** (HTTP PUT source protocol, with the legacy SOURCE method for older servers): MP3, AAC, Ogg Vorbis, Ogg Opus, FLAC in Ogg; mount point, user, password, public or private listing, stream name, description, genre and URL. TLS where the server offers it. (M)
- **S2. SHOUTcast v1 and v2 (DNAS 2.x)**: the v1 password handshake and v2 stream IDs, MP3 and AAC. Studio carries its own small source client for these, because FFmpeg speaks Icecast but not SHOUTcast's handshake. (M)
- **S3. Now-playing metadata**: title and artist sent through Icecast's admin metadata update and SHOUTcast's `updinfo`, typed by hand, taken from the cart or playlist (S9), or from a marker. Ogg streams carry it in-band. (S)
- **S4. Several destinations at once** (BCAST-015): Icecast and SHOUTcast together, each with its own format and bit rate, each with its own status; a failed second destination is never hidden behind one green light. (M)
- **S5. Reconnect without leaving dead air**: automatic reconnect with back-off, a spoken notice once, a marker, and the local archive keeps recording through the outage. (S)
- **S6. Listener confidence check** (BCAST, VERIFY-006): Studio connects to its own public stream as a listener, measures the delay, and confirms the far end carries sound, not silence; "Verified with external loopback". (S)
- **S7. Listener statistics** on request: current and peak listeners from the server's status page, spoken when asked. (S)
- **S8. Archive while streaming**: the same Stream bus mix saved locally, with the recording's after-check. (S)
- **S9. A small show kit, not an editor**: a playlist of files to play into the stream in order, a cart wall of sound clips on keys (PRD 10C, the parts that are playback), a station ID on a timer, and talk-over with ducking (M6). (L)
- **S10. Video streaming** beside audio: RTMP and RTMPS (YouTube Live, Twitch, Facebook, Teams and Zoom webinar ingest), SRT, and WHIP to WebRTC servers, with the Screen and Camera choices from section 2. (L)
- **S11. Credentials stored safely**: passwords and stream keys in Windows Credential Manager through QUILL's DPAPI store, never in settings JSON, never in logs (redaction), never in exported setups. (S)
- **S12. Consent and audit**: every server is a network destination the user typed; each connection goes through QUILL's network egress audit; Safe Mode does not block local recording but does block streaming unless confirmed. (S)
- **S13. Relay and listen-in**: optionally re-stream another Icecast stream (for example a partner station) into the Stream bus with its own level, and Quill Radio can open your own stream from a "Listen to my show" key. (M)
- **S14. Scheduled shows**: go live at a set time with the preflight result kept, end after a set length, and archive if you chose to. (M)
- **S15. Stream settings, in plain words.** Every setting has a plain name first and the technical name beside it only where a server's form uses it:
  - **About the show**: title, description, genre, website, and whether the server lists it publicly ("Show this stream in public directories"). Title and description can include today's date or the show number automatically.
  - **Sound quality**: a simple choice of Speech (smallest), Talk and music, Music (best), or Custom. Custom offers the format (MP3, AAC, AAC+ (HE-AAC), Ogg Vorbis, Opus, FLAC), the quality as a bit rate from 16 to 320 kilobits a second, or a variable quality level, stereo or mono, and the sample rate (22.05, 32, 44.1 or 48 kHz). Studio says how much internet upload each choice needs and warns when it is more than the connection measured.
  - **Loudness**: an optional automatic level so the stream sounds even, aimed at a chosen loudness (for example minus 16 LUFS for talk), with a safety limiter that stops distortion. Off means the mix goes out exactly as it is.
  - **Connection**: server address and port, mount point or stream number, user name, password, secure connection where the server offers it, and how hard to try reconnecting.
  - **Now playing**: what listeners see as the current title, typed, taken from the playlist or cart, or left as the show title.
  - **Save a copy (archive)**: off or on, chosen each time and saved with the setup; when on, the copy's own format and quality can differ from the stream's (for example FLAC at home, MP3 to listeners), and long shows can be split into hours.
  - **Delay**: an optional broadcast delay of a few seconds, with Studio saying what it is, so a slip can be cut before listeners hear it (the Mute everything public key acts on the delayed sound).
  - **Test before going live**: a private test connection that checks the password, the mount, and that the server accepts the format, without anyone hearing it. (L, across S1 to S14)

## 6A. Meetings: Zoom and Teams in a recording, a stream, or both ways

The goal: put the people in a Zoom or Teams meeting into a demonstration or a stream, and send Studio's sound (your microphone, a demo program, music) into the meeting, with no echo and no loop of the meeting hearing itself.

**How the echo is avoided (the rule for everything below).** Studio never records or streams "everything the computer plays" when a meeting is in it. It takes the meeting's sound from the meeting program alone (process loopback of `Zoom.exe` or `ms-teams.exe`), and whatever Studio sends *to* the meeting is a **mix-minus**: everything except the meeting's own sound (MX-129). The meeting is heard in your headphones only, never on speakers that the microphone could pick up. Each piece is checked in the spoken check and named in plain words.

- **Z1. The meeting as a sound source** (works today's way, no driver): a "Zoom meeting" or "Teams meeting" row in Sound sources, found by name, with its own level, in or out of the recording and the stream. The far-end speakers are recorded cleanly because only the meeting program's sound is taken; your screen reader and other programs are not in it. (S)
- **Z2. Send to the meeting, the plain way** (no driver): both programs can share computer sound with a screen share (Zoom "Share sound", Teams "Include computer sound"). Studio explains the exact steps for the version found, plays its mix-minus to the device the meeting shares, and checks with the cable test that the meeting is not hearing itself. Best for a demonstration inside a meeting. (S)
- **Z3. Send to the meeting as a microphone** (needs a virtual cable the user installs, section 1): Studio plays the mix-minus into "CABLE Input", and the meeting's microphone is set to "CABLE Output". Studio tells you exactly which setting to change in Zoom or Teams and confirms it worked by listening for its own test tone coming back through the meeting's sound. Your real microphone stays in Studio's mix, so you can add music, a demo program or sound clips to what the meeting hears. (M)
- **Z4. Meeting-friendly sound in Zoom**: Studio's guide for Zoom's "Original sound for musicians" and echo cancellation settings when it is sending a clean mix, so Zoom does not fight the mix. (S)
- **Z5. Studio's picture into the meeting as a camera** (no driver on Windows 11, K2): the screen, the camera, captions and overlays arrive in Zoom or Teams as a camera called "QUILL Studio". (L)
- **Z6. The meeting into a live stream**: the Z1 source on the Stream bus, so an Icecast show or an RTMP video stream carries the guests, with your microphone and music, and the guests hear you through Z2 or Z3 without hearing themselves. (S once S1 and M3 exist)
- **Z7. Meeting controls from Studio's keys**: mute and unmute yourself in the meeting, raise a hand, start or stop sharing, by sending the meeting program its own documented keys (Zoom Alt+A, Teams Ctrl+Shift+M) or its accessibility controls, with spoken confirmation. Opt-in, and only to a meeting window you chose. (M)
- **Z8. Separate tracks for later**: the meeting and your microphone kept as separate files beside the recording (R7), so a podcast made from a call can be balanced later in another program. (S)
- **Z9. Deeper integrations, considered for later**: Zoom's Meeting SDK raw audio and its real-time media streams, and Teams media bots through Microsoft Graph, can give each participant as a separate source. They need developer accounts, app review and server components, so they are recorded here as possibilities, not plans. Webinar RTMP output from Zoom and Teams can already feed a server Studio streams to. (XL)

## 6B. Pictures made with AI, and a picture with sound as a YouTube video

The goal: a podcast episode, a talk or a song becomes a video YouTube accepts, with a picture you made by describing it, without editing any audio.

- **V1. Make a picture by talking about it** (PRD VIS-009). A conversation like the Screenshot Inspector's: describe what you want ("a warm cover for a podcast about blind travel, a suitcase and a cane, no text"), the AI asks what it needs, an image is generated with the image model of your choice (the shared AI providers that make images, such as OpenAI's image models or Google's Imagen, and local generation where the computer can run it), and then you hear a detailed description of what was made, from a separate look by the vision model, so you are not relying on the generator's own claims. Ask for changes in words ("make the background darker", "move the suitcase left", "add the title QUILL Talk at the top in large white letters") and each version is kept so you can go back. Sizes offered in plain words: "YouTube video (1920 by 1080)", "Square cover (3000 by 3000)", "YouTube thumbnail (1280 by 720)". Every picture is saved with its prompt, its description and its alt text. Consent, cost notice and Safe Mode rules are the same as for screenshots. (L)
- **V2. Check a picture before using it**: text readable at YouTube's sizes, contrast of any words, nothing cut off at the edges, and an alt text you approve. Uses OCR first and AI only with approval. (S)
- **V3. Picture plus sound becomes a video.** **Built** 2026-10-29 (Capture > Make a YouTube video from a picture and sound). Choose a picture (made in V1, a file, a screenshot, or a camera photo) and a sound: record it now (microphone, a program, the system, any mix of sources, through Record a demonstration with the picture off) or choose an audio file. Studio makes an MP4 that YouTube accepts: 1920 by 1080 (or the picture's own size, padded rather than stretched), H.264 at a low frame rate suited to a still picture, AAC sound at 48 kHz, and the same independent check as a recording. No audio is edited; the sound goes in exactly as it is. (M)
- **V4. Options for the video, all optional** (**Built** so far: slow zoom, sound wave, chapters from markers into the file and the description; still to do: several pictures, title card, burned-in captions): a gentle slow zoom on the picture; several pictures changing at chapter markers or at set times; a title card at the start; burned-in captions from a local transcript (A5); a sound wave or level bar along the bottom ("audiogram"), so viewers can see that sound is playing; and chapters written into the file and into the YouTube description as timestamps. (M)
- **V5. Ready to upload.** Studio writes the title, description (with chapter timestamps), tags and the thumbnail beside the video, with A3's AI suggestions offered for each field. With your consent and your own Google sign-in, it can upload to YouTube directly (private or unlisted first, by default), and it reports the processing result. Without sign-in, Open folder and the written files make a manual upload quick. (M for files, L for direct upload)
- **V6. The same for other places**: square video for social posts, a vertical version for Shorts, and an audio file with embedded cover art and chapters for podcast hosts. (S)

## 7. More from the parity study and the PRD (no editing, no multitrack)

- **O1. Keystroke and focus track** (DEMO-003): optional timed record of keys pressed (passwords never) and the screen reader's focus, as a text file and as optional on-screen captions. (M)
- **O2. Click and focus highlight, and zoom** (CAP-003, ZoomIt): a ring around the focused control, click marks, and a keyboard zoom that follows focus. (M)
- **O3. Markers become chapters** inside MP4, M4A and MP3 so every player shows them, after a backup copy. (S)
- **O4. Tags on the output**: title, artist, album, year, comment, cover image. (S)
- **O5. Intro and outro sounds**, and one sound on a key, played into the recording (playback, not editing). (S)
- **O6. Identify the music** in any source (do.md F02). (S)
- **O7. Share**: post a link to Mastodon through QUILL's existing posting; upload to YouTube or PeerTube with consent, title and description from A3. (M)
- **O8. Screenshot sequence with narration** (DEMO-002's fourth mode), saved as a narrated slideshow video. (M)
- **O9. Guest and remote sources**: a caller over a meeting program's output, or a phone over a USB interface, as named sources with their own mix-minus (M11). (M)
- **O10. Text overlays** typed in words: name and title strip, a "Recording" badge, a website address, positioned by name, not by dragging. (M)
- **O11. Background blur or replace for the camera**, on the device, with a privacy check that the effect is really on before going live. (L)
- **O12. Sign language window**: a second camera fixed in a corner at a size suited to signing, with a check that hands stay in frame. (S after R8)

## 8. Finishing version 1 (continuing tonight)

- **F1.** GATE-11 splits done; snapshots regenerated; full scorecard and Studio suites rerunning.
- **F2.** `docs/audio-studio/` holds the older Audio Studio copies; only `standalone/studio/docs/` (QUILL Studio's current docs) was updated. Decide whether to retire the old copies.
- **F3.** Live checks for you: a 1-minute recording with the microphone and camera on, Check camera framing with you in front of the camera, and the keys from inside another program with JAWS and NVDA.
- **F4.** Commit to the branch at the end of the night; no push and no PR unless you say so.

## Order of work

Tonight, in this order, each with tests, gates and documentation before the next starts:

1. F1, then **R1** (Screen and Camera check boxes), **R2**, **R3**, **R4** (all combinations of picture and sound).
2. **P7** (Do Not Disturb and keep awake, must have), then **P2**, **P3**, **P4** (rehearsal and the long-recording check).
3. **M1** and **M2** (the Mixer window with Programs and Devices tabs, including moving a program to another sound card).
4. **V3** and **V4** (picture plus sound as a YouTube video), **A5** (local captions), then **A1** (Ask AI about the whole video or a chosen section) and **V1** (pictures made with AI).
5. **S1**, **S3**, **S5**, **S8**, **S11**, **S12** (Icecast streaming with a Stream bus send per source, metadata, reconnect, archive, safe credentials, consent) and **S2** (SHOUTcast).
6. If something has to wait, it is the broadcasting pieces (section 6): everything else comes first.

Then the two large items, both chosen: **R10** (window recording that follows the window) and **P1 with M3** (the live engine: preview, monitoring, buses, the Stream bus). After them: M4 to M12, S4, S6, S9, S10, S15 in full, K1, K2, O1 to O12.

## Decisions still open

None tonight. New questions will be added here as they come up.
