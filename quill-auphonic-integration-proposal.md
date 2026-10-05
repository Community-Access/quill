# QUILL Converter + Auphonic Integration Proposal

## Executive Summary

QUILL Converter could gain a substantial set of professional audio-production capabilities by integrating with the official Auphonic API as an optional online service.

The recommended model is:

> **QUILL → user's Auphonic account → Auphonic processing → QUILL**

Users would explicitly opt in, connect their own Auphonic account, and use their own Auphonic processing allowance or paid credits. QUILL would not need to collect user passwords or pay for processing on behalf of users.

The key architectural recommendation is to integrate with the **official Auphonic REST API**, rather than attempting to integrate with a separate accessible front end such as "Accessible Auphonic."

This approach would allow QUILL Converter to expose powerful audio tools through a screen-reader-first, keyboard-first interface that is considerably easier to operate than conventional waveform-based audio production software.

---

# 1. Integration Target

Auphonic exposes its processing system through a REST API.

Its developer platform includes:

- REST API
- OpenAPI-based API documentation
- Simple API
- Full JSON API
- OAuth 2.0
- API keys
- Presets
- Production management
- Multitrack production
- External services
- Webhooks
- Command-line tools

A conventional Python SDK is not required.

For QUILL, a lightweight internal Python client using a library such as `httpx` would likely be preferable to adding a large third-party dependency.

A possible internal structure:

```text
quill/
    services/
        auphonic/
            client.py
            auth.py
            models.py
            productions.py
            presets.py
            formats.py
            algorithms.py
            downloads.py
```

This keeps Auphonic isolated and optional.

Reference:

https://auphonic.com/help/api/index.html

---

# 2. Recommended QUILL Branding

The feature could appear in QUILL Converter as:

**Enhance with Auphonic...**

or:

**Auphonic Audio Studio**

The user should understand that Auphonic is an optional external online service.

A possible first-use disclosure:

```text
Auphonic Audio Processing — Optional Online Service

Connect your own Auphonic account to access professional online
audio cleanup, leveling, transcription, and production tools.

Your selected media file will be uploaded to Auphonic only when
you explicitly choose to process it.

Nothing will be uploaded until you choose Continue.

Continue
Learn More
Cancel
```

---

# 3. Basic User Experience

The simplest workflow should avoid requiring the user to understand technical audio terminology.

From QUILL Converter:

```text
Enhance Audio → Auphonic
```

Then offer approachable workflows:

```text
Quick Enhance
Clean Up Voice
Podcast
Audiobook
Lecture / Presentation
Broadcast
Custom...
```

QUILL would translate these selections into Auphonic API parameters.

Technical controls such as LUFS, true peak, compression, denoising strength, and EQ should remain available under an **Advanced** option.

---

# 4. Adaptive Volume Leveling

Auphonic includes an Adaptive Leveler that analyzes speech, music, and other sections of a recording and balances differences in volume.

This is useful when:

- one speaker is quieter than another
- microphones differ
- microphone distance changes
- music and speech have different levels
- interviews contain inconsistent recording levels

A QUILL interface could expose:

```text
Level voices automatically

Off
Gentle
Normal
Strong
```

The default could be **Normal**.

Reference:

https://auphonic.com/help/algorithms/singletrack.html

---

# 5. Noise and Room Cleanup

Auphonic can provide several kinds of audio cleanup, including:

- background noise reduction
- dynamic noise reduction
- hum removal
- reverberation reduction
- breath reduction
- speech isolation

QUILL could simplify this as:

```text
Clean Up Recording

[X] Remove background noise
[X] Reduce room echo
[ ] Reduce breathing sounds
[ ] Isolate speech
```

An Advanced button could expose processing strength.

This would be particularly useful for:

- Zoom recordings
- conference recordings
- lectures
- voice notes
- podcasts
- laptop-microphone recordings
- screen-reader demonstrations
- older recordings

Reference:

https://auphonic.com/help/algorithms/singletrack.html

---

# 6. Voice Enhancement and Studio Voice

Auphonic supports voice-processing functions including:

- adaptive high-pass filtering
- Voice AutoEQ
- bandwidth extension
- Studio Voice

QUILL could expose an approachable control:

```text
Voice Enhancement

( ) Natural
( ) Clear Voice
( ) Studio Voice
```

This makes advanced voice processing understandable without exposing DSP terminology.

---

# 7. Automatic Filler, Silence, and Cough Detection

Auphonic can identify and process items such as:

- filler words
- "um"
- "uh"
- silence
- coughs
- respiratory noises
- music regions

QUILL could expose:

```text
Automatic Cleanup

[X] Remove long silences
[X] Remove filler words such as "um" and "uh"
[X] Remove coughs
[ ] Remove music
```

However, QUILL should also support:

```text
[X] Review suggested edits before removing them
```

This could become a major accessibility feature.

Instead of requiring waveform manipulation, QUILL could expose each detected edit as structured text.

Example:

```text
Suggested Edit 4 of 17

Type:
Filler word

Text:
"um"

Start:
00:06:21.430

End:
00:06:21.910

Duration:
0.48 seconds

Actions:
Play Before
Play Selection
Play After
Keep
Remove
Previous
Next
```

This is potentially one of the strongest differentiators of the entire integration.

---

# 8. Speech Transcription

Auphonic includes hosted speech recognition and can generate multiple transcript and caption formats.

Potential QUILL outputs include:

- plain text
- HTML
- SRT
- WebVTT
- JSON
- XML
- timestamps
- confidence information
- speaker diarization

QUILL could expose:

```text
Create Transcript
Create SRT Captions
Create WebVTT Captions
Create Transcript + Captions
```

Additional option:

```text
[X] Identify different speakers
```

Where supported, QUILL could also allow the user to assign speaker names.

---

# 9. Automatic Show Notes

Auphonic can generate automatic show notes and chapters.

This has immediate potential for QUILL Cast.

For example:

```text
BITS Weekly Podcast.wav
```

could produce:

```text
BITS Weekly Podcast.mp3
BITS Weekly Podcast.txt
BITS Weekly Podcast.srt
BITS Weekly Podcast.vtt
BITS Weekly Podcast-show-notes.md
```

This could substantially reduce podcast post-production effort.

Reference:

https://auphonic.com/help/api/details.html

---

# 10. Automatic Chapters

Auphonic can work with chapter metadata and can generate chapters as part of speech-recognition and show-note workflows.

QUILL could offer:

```text
[X] Generate chapters automatically
```

and then present them accessibly:

```text
Chapter 1
00:00
Introduction

Chapter 2
04:37
QUILL Radio Updates

Chapter 3
12:14
AI Dictation
```

Users could then rename, delete, or adjust chapters before export.

---

# 11. Loudness Standards

Auphonic supports professional loudness normalization and true-peak processing.

Potential targets include:

- podcast/mobile
- radio
- EBU R128
- ATSC A/85
- Audible/ACX
- streaming-oriented targets
- broadcast-oriented targets

Rather than asking users to understand LUFS values, QUILL could expose:

```text
Optimize For

Podcast
Audiobook / ACX
YouTube
Radio
Television
Music
Custom
```

QUILL would configure the technical values automatically.

---

# 12. Audiobook Processing

Audiobook production deserves a dedicated QUILL workflow.

Possible entry point:

```text
Convert → Audiobook → Prepare with Auphonic
```

Options could include:

```text
[X] Normalize chapters
[X] Match volume between chapters
[X] Clean background noise
[X] Reduce breaths
[X] Preserve chapter metadata

Output:
[X] MP3
[X] M4B
[ ] FLAC archive
```

This could become valuable for blind audiobook creators who do not want to work in a traditional DAW.

---

# 13. Input Format Support

Auphonic accepts a broad range of audio and video formats.

Examples include:

- MP2
- MP3
- MP4
- M4A
- M4B
- WAV
- BWF
- OGG
- Opus
- FLAC
- ALAC
- MOV
- AAC
- AIFF
- WMA
- WebM
- MKV
- AVI

This fits naturally into QUILL Converter.

Reference:

https://auphonic.com/help/web/production.html

---

# 14. Multiple Output Formats

Auphonic supports numerous output formats, including:

- MP3
- MP3 VBR
- AAC
- M4A
- MP4
- M4B
- Opus
- Ogg Vorbis
- FLAC
- ALAC
- WAV 16-bit
- WAV 24-bit
- video
- audiogram
- processed individual tracks
- transcript
- SRT
- WebVTT
- speech JSON
- speech XML

QUILL could let the user create multiple outputs in one production.

Example:

```text
Output Files

[X] MP3 - 128 kbps
[X] FLAC archive
[X] SRT captions
[X] Plain-text transcript
```

This is especially attractive because Auphonic generally bases processing usage on input duration rather than charging separately for every output format.

Reference:

https://auphonic.com/help/web/pricing_faq.html

---

# 15. Multitrack Processing

A more advanced phase could support multitrack projects.

Example:

```text
Jeff.wav
Brian.wav
David.wav
IntroMusic.wav
```

Auphonic multitrack processing can potentially provide:

- per-speaker leveling
- automatic mixing
- noise gating
- crosstalk removal
- microphone bleed reduction
- denoising
- automatic ducking
- stereo positioning
- final loudness normalization

QUILL could provide a structured interface such as:

```text
Create Multitrack Production

Track 1:
Jeff.wav
Type: Speech

Track 2:
Brian.wav
Type: Speech

Track 3:
Theme.wav
Type: Music
```

This could give blind users access to production workflows that are traditionally highly visual.

Reference:

https://auphonic.com/help/algorithms/multitrack.html

---

# 16. Microphone Bleed and Crosstalk Removal

When multiple microphones are used in the same room, speech from one participant may leak into another microphone.

Auphonic can analyze active speakers and reduce unwanted leakage.

This is valuable for:

- podcasts
- interviews
- conference recordings
- panel discussions
- multi-microphone productions

---

# 17. Automatic Music Ducking

If QUILL identifies one track as speech and another as music, Auphonic can automatically reduce music volume while speech is active.

Example:

```text
Narration.wav
BackgroundMusic.mp3
```

QUILL could create a professional mix without requiring the user to operate Audacity, Reaper, or another waveform-oriented DAW.

---

# 18. Video Processing

Auphonic also supports video processing.

Its automatic cutting tools can operate on video while detecting items such as:

- filler words
- silence
- coughs
- music sections

This means QUILL Converter could eventually offer:

```text
Clean Up Video
```

while preserving the video stream and improving or editing its audio.

Reference:

https://auphonic.com/blog/2026/04/15/automatic-video-cutting/

---

# 19. Audiogram Generation

Auphonic can generate waveform-style promotional videos from audio.

Possible ingredients include:

- cover art
- chapter images
- waveform visualization

QUILL could expose:

```text
Create Shareable Audiogram
```

This may be particularly useful for QUILL Cast and podcast promotion.

---

# 20. Metadata Support

Auphonic supports metadata including:

- title
- artist
- album
- track
- summary
- URL
- genre
- license
- tags
- chapters
- artwork

QUILL could provide an accessible metadata editor before processing.

This could replace the need for several separate tagging utilities.

Reference:

https://auphonic.com/help/api/update.html

---

# 21. Presets and QUILL Recipes

Auphonic supports reusable presets.

QUILL should expose both:

1. **Auphonic Presets**
   - Stored in the user's Auphonic account.

2. **QUILL Recipes**
   - Friendly QUILL-defined workflows that translate into Auphonic settings.

Examples:

```text
Auphonic Preset

QUILL Quick Enhance
BITS Podcast
My Audiobook
Zoom Cleanup
Lecture Cleanup
Custom...
```

Reference:

https://auphonic.com/help/api/complex.html

---

# 22. Authentication

Auphonic supports multiple authentication mechanisms, including:

- API key
- HTTP Basic authentication
- OAuth 2.0

For a multi-user desktop application, OAuth is the preferred approach.

QUILL should **not** collect or store the user's Auphonic password.

A proposed workflow:

```text
Settings
  Connected Services
    Auphonic
      Connect...
```

QUILL opens the user's browser.

The user signs into Auphonic directly and grants access.

QUILL receives an OAuth token.

Then QUILL could show:

```text
Auphonic

Connected as:
jeffbishop

Remaining processing:
8h 37m

Disconnect
```

Reference:

https://auphonic.com/help/api/authentication.html

---

# 23. OAuth Broker Recommendation

Desktop applications cannot securely protect a reusable client secret embedded inside the executable.

A stronger architecture would use a small QUILL-controlled OAuth broker.

Example:

```text
QUILL
   ↓
Browser
   ↓
Auphonic Authorization
   ↓
auth.quillforall.org
   ↓
QUILL
```

This would allow QUILL to protect secrets server-side rather than embedding them in the Python application.

It would also make future token-management changes easier.

Before shipping, it would be wise to contact Auphonic regarding the intended third-party desktop integration.

Reference:

https://auphonic.com/help/api/external_service.html

---

# 24. Credential Storage

QUILL should securely store only tokens required for authentication.

Recommended storage:

## Windows

Windows Credential Manager

## macOS

macOS Keychain

Tokens should not be stored in:

- plain-text JSON files
- INI files
- log files
- portable configuration folders

For QUILL Portable, the default should probably be to require reauthentication unless a secure cross-platform solution is deliberately implemented.

---

# 25. Privacy and Explicit Opt-In

Auphonic processing requires uploading media to an external service.

This must be explicit.

Before the first upload:

```text
This feature sends the selected media file to Auphonic
for online processing.

Nothing will be uploaded until you choose Continue.

Continue
Learn More
Cancel
```

QUILL should also provide:

```text
Settings
  Privacy
    Connected Online Services
      Auphonic
```

with:

- connected account
- disconnect
- privacy information
- what data is uploaded
- when uploads occur
- whether files are retained
- link to Auphonic policies

---

# 26. Account Usage and Cost

Auphonic offers free and paid processing options.

QUILL should query and present account information when available.

Example:

```text
Auphonic Account

Available processing:
1 hour 42 minutes

Plan:
Free

Important:
Auphonic may add a promotional jingle to output created
with some free-plan processing.

Continue
View Auphonic Account
Cancel
```

The goal is to prevent surprises.

Reference:

https://auphonic.com/pricing

---

# 27. Recommended QUILL Converter Workflow

A file such as:

```text
conference-recording.wav
```

could be handled through:

```text
Convert With...

Standard QUILL Conversion
Auphonic Audio Studio
```

Then:

```text
What would you like QUILL to do?

Quick Enhance
Clean Up Voice
Prepare Podcast
Prepare Audiobook
Create Transcript
Create Captions
Remove Fillers and Silence
Create Audiogram
Advanced Processing
```

Example **Prepare Podcast** interface:

```text
Prepare Podcast

Audio Cleanup

[X] Balance speaker volume
[X] Remove background noise
[X] Reduce room echo
[X] Improve voice clarity
[X] Normalize podcast loudness
[X] Remove long silences
[ ] Remove filler words
[ ] Remove coughs

Transcript

[X] Create transcript
[X] Identify speakers
[X] Generate chapters
[X] Generate show notes

Output

[X] MP3 128 kbps
[ ] FLAC archive
[X] SRT captions

Start Processing
```

---

# 28. Job Management

Auphonic processing is asynchronous.

QUILL should provide a job manager.

Example:

```text
Auphonic Jobs

Conference Recording
Processing - 62%

BITS Podcast
Completed

David Interview
Waiting
```

Initial implementations could use periodic status polling.

A later QUILL cloud component could support webhook callbacks if useful.

Reference:

https://auphonic.com/help/api/query.html

---

# 29. Completion Reporting

When processing completes, QUILL could present a text-first report.

Example:

```text
Processing Complete

Original duration:
01:13:42

New duration:
01:08:17

Processing Summary:

18 filler words removed
7 silence regions removed
Background noise reduced
Loudness normalized to -16 LUFS

Files Created:

conference-recording.mp3
conference-recording.txt
conference-recording.srt
conference-recording.vtt

Actions:

Open Folder
Play Result
View Transcript
View Processing Report
```

Detailed processing data should be exposed as structured text rather than only through visual graphs.

---

# 30. Accessible Review of Automatic Cuts

This may be the most uniquely QUILL-oriented feature.

Waveform editors are inherently difficult for many blind users.

QUILL could instead expose every automatic edit as a navigable textual item.

Example:

```text
Detected Cuts

17 proposed edits

Edit 4 of 17

Type:
Filler word

Text:
"um"

Start:
00:06:21.430

End:
00:06:21.910

Duration:
0.48 seconds

Actions:

Play Before
Play Selection
Play After
Keep
Remove
Previous
Next
```

Keyboard commands could include:

```text
Space          Play selection
Shift+Space    Play context
Delete         Remove
K              Keep
Alt+Right      Next edit
Alt+Left       Previous edit
Ctrl+A         Accept all
```

This would transform a visual editing process into a screen-reader-first workflow.

---

# 31. Suggested Development Phases

## Phase 1 — Core Integration

- Auphonic account connection
- secure OAuth token storage
- upload
- production creation
- status monitoring
- download
- Quick Enhance
- Adaptive Leveler
- background noise cleanup
- reverberation cleanup
- loudness normalization
- MP3
- WAV
- FLAC
- AAC
- Opus output

## Phase 2 — Speech and Content Processing

- user presets
- QUILL recipes
- silence removal
- filler-word detection/removal
- cough detection/removal
- transcripts
- SRT
- WebVTT
- speaker diarization
- automatic chapters
- automatic show notes

## Phase 3 — Accessible Editing

- accessible proposed-cut review
- playback around edit points
- keep/remove individual edits
- audiobook mode
- audiogram generation
- video processing
- advanced metadata editor

## Phase 4 — Multitrack and QUILL Cast

- multitrack production
- per-speaker processing
- mic-bleed removal
- automatic music ducking
- advanced mixing
- QUILL Cast integration
- publication workflows
- podcast-production pipelines

---

# 32. Opportunities Across the QUILL Ecosystem

The integration should begin in QUILL Converter, but the service could eventually be shared across multiple QUILL products.

## QUILL Lite

Possible command:

```text
Tools → Improve Audio with Auphonic
```

## QUILL Radio

Potential uses:

- normalize recordings
- repair recordings
- convert archived recordings
- prepare recordings for libraries or rebroadcast

## QUILL Cast

This may eventually become the deepest integration.

Possible pipeline:

```text
Record
  ↓
Clean
  ↓
Level
  ↓
Transcribe
  ↓
Remove fillers
  ↓
Generate chapters
  ↓
Generate show notes
  ↓
Encode
  ↓
Publish
```

Auphonic also supports integrations with various storage, hosting, and publishing services.

Reference:

https://auphonic.com/help/web/services.html

---

# 33. Product Positioning

QUILL should not hide the fact that Auphonic is an external online service.

Recommended language:

> **Auphonic Audio Processing — Optional Online Service**
>
> Connect your own Auphonic account to access professional online audio cleanup, leveling, transcription, and production tools. Your files are sent to Auphonic only when you choose one of these features.

This provides:

- transparency
- user control
- clear privacy expectations
- clear cost ownership
- explicit opt-in

---

# 34. Strategic Value to QUILL

The strongest value proposition is not simply:

> "Auphonic inside QUILL."

The larger opportunity is:

> **Make advanced professional audio production usable through a keyboard-first, screen-reader-first textual interface.**

The most compelling areas include:

- automatic cut review
- multitrack processing
- microphone bleed removal
- automatic ducking
- transcription
- captions
- chapters
- show notes
- processing statistics
- audiobook preparation
- podcast production

These are capabilities that blind users have traditionally had difficulty accessing through waveform-heavy audio applications.

QUILL can potentially provide a dramatically more approachable interface without having to recreate Auphonic's audio-processing technology.

---

# 35. Recommended Technical Direction

The recommended architecture is:

```text
QUILL Converter
      │
      ├── Local Conversion Engine
      │
      └── Optional Online Services
              │
              └── Auphonic
                    │
                    ├── OAuth
                    ├── Account Information
                    ├── Presets
                    ├── Production Creation
                    ├── Upload
                    ├── Processing
                    ├── Status
                    └── Download
```

A Python implementation could use:

- `httpx`
- Python dataclasses or Pydantic models
- platform credential APIs
- QUILL's normal background-task infrastructure
- a small optional OAuth callback/broker service

Auphonic should remain a replaceable service module rather than being tightly coupled to the main Converter code.

---

# 36. Final Recommendation

Auphonic is a strong candidate for integration into QUILL Converter.

The first release should focus on:

1. secure account connection
2. explicit opt-in
3. audio upload
4. Quick Enhance
5. voice cleanup
6. loudness normalization
7. output conversion
8. job status
9. result download

The next release should add:

1. transcripts
2. captions
3. chapters
4. show notes
5. automatic filler/silence detection
6. accessible review of proposed edits

Longer term, multitrack production and QUILL Cast integration could turn this into one of the most capable screen-reader-accessible audio-production environments available.

The official Auphonic API is the correct integration target. "Accessible Auphonic" is useful evidence that there is demand for a more accessible Auphonic workflow, but QUILL should rely on the official API so that the integration remains stable, supported, and independent.

---

# References

Auphonic API Documentation  
https://auphonic.com/help/api/index.html

Auphonic Authentication  
https://auphonic.com/help/api/authentication.html

Auphonic API Details  
https://auphonic.com/help/api/details.html

Auphonic API Querying and Production Status  
https://auphonic.com/help/api/query.html

Auphonic API Update / Metadata  
https://auphonic.com/help/api/update.html

Auphonic Complex API / Presets  
https://auphonic.com/help/api/complex.html

Auphonic External Services  
https://auphonic.com/help/api/external_service.html

Auphonic Singletrack Algorithms  
https://auphonic.com/help/algorithms/singletrack.html

Auphonic Multitrack Algorithms  
https://auphonic.com/help/algorithms/multitrack.html

Auphonic Production Documentation  
https://auphonic.com/help/web/production.html

Auphonic Multitrack Production  
https://auphonic.com/help/web/multitrack.html

Auphonic Pricing  
https://auphonic.com/pricing

Auphonic Pricing FAQ  
https://auphonic.com/help/web/pricing_faq.html

Auphonic External/Publishing Services  
https://auphonic.com/help/web/services.html

Auphonic Automatic Video Cutting  
https://auphonic.com/blog/2026/04/15/automatic-video-cutting/
