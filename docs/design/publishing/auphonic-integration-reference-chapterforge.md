> **Archived reference.** This is ChapterForge's Auphonic integration design,
> kept when ChapterForge was consolidated into QUILL (2026-07-04). QUILL's own
> shipped client is the compact `quill/core/publish/auphonic.py` (API-token auth,
> simple-API upload/poll/download, credential-vault storage) reached from the
> Chapter Workbench's Publish dialog. Mine this document when growing that
> client (OAuth flow, credit balance, multitrack, preset UX).

# Auphonic Integration

> **Beta feature** - Auphonic integration is opt-in. Enable it under **Tools > Settings > General > Enable beta features**. The Auphonic menu will appear after saving.

ChapterForge integrates with [Auphonic](https://auphonic.com) for professional audio post-production. Connect your own Auphonic account to process audio using your own credits - ChapterForge does not resell or proxy Auphonic billing.

## Features

- Connect your Auphonic account via OAuth 2.0 (no password stored)
- View your available credit balance before submitting jobs
- Submit singletrack and multitrack audio productions
- Six built-in presets plus your own Auphonic account presets
- Audio-only validation - video files are rejected at the source
- Automatic credit estimation with 3-minute minimum warning
- Background polling with exponential backoff until jobs complete
- Download all result files (audio, transcript, captions, stats, chapters)
- Review-before-publish workflow
- Full keyboard and screen reader accessibility

## Menu Access

**Auphonic** menu (between View and Help):

| Menu item | Shortcut | Action |
|---|---|---|
| Connect Account | - | OAuth connect / view credit balance |
| New Production | - | Submit audio for processing |
| Job History | - | View jobs and download results |

## Setup

### 0. Enable beta features

Open **Tools > Settings**, go to the **General** tab, and check **Enable beta features (Auphonic integration)**. Click OK. The **Auphonic** menu will appear in the menu bar.

### 1. Get an Auphonic account

Sign up at https://auphonic.com. New accounts receive free credits.

### 2. Register a desktop OAuth app (admin / developer step)

Contact Auphonic support to register a desktop OAuth application. You will receive a **Client ID** and **Client Secret**. These are set per deployment:

- For development: set environment variables before launching:
  ```powershell
  $env:AUPHONIC_CLIENT_ID = "your-client-id"
  $env:AUPHONIC_CLIENT_SECRET = "your-client-secret"
  python main.py
  ```
- For production builds: the build pipeline injects these at build time (same pattern as the GitHub feedback token).

### 3. Connect from inside ChapterForge

1. Open **Auphonic > Connect Account**
2. Click **Connect Auphonic** - your browser opens to Auphonic's authorization page
3. Log in and approve access
4. Return to ChapterForge - the dialog shows your credit balance

Your OAuth token is stored encrypted in `%APPDATA%\ChapterForge\auphonic_token.bin` using Windows DPAPI. It is never logged or sent to any server other than Auphonic.

## Submitting a Production

1. Open **Auphonic > New Production**
2. Click **Browse** and select an audio file
3. ChapterForge validates the file with ffprobe (rejects video streams)
4. Your credit estimate and available balance are shown
5. Choose a preset (or your own account preset)
6. Enter a title and click **Submit Production**
7. ChapterForge submits to Auphonic and polls for completion in the background

When the job finishes you receive a notification. Open **Job History** to download results.

## Built-in Presets

| Preset | Best for | Key settings |
|---|---|---|
| Podcast Cleanup | General podcast editing | Leveling, -16 LUFS, denoise, filtering. MP3 + stats |
| Podcast Cleanup + Transcript | Podcast with accessibility | Same + transcript HTML/TXT, SRT, WebVTT captions |
| Audiobook / ACX Draft | Audiobook submission drafts | -18 LUFS, heavy denoise, WAV + FLAC |
| Lecture Cleanup | Recorded lectures | Denoise, silence cutting, MP3 + captions |
| Meeting / Interview Multitrack | Multi-person recordings | Adaptive leveling, multitrack layout, MP3 |
| Archive Master | Long-term archival | Minimal processing, FLAC + WAV + chapters |

## Audio-Only Policy

This integration is audio-only. The following are enforced at every stage:

- Only audio file extensions are accepted (MP3, WAV, FLAC, M4A, AAC, OGG, Opus, AIFF, and others)
- ffprobe inspects every file for video streams - any video stream causes rejection
- Remote URLs must use HTTPS and must not resolve to private/loopback IP ranges
- Auphonic output files containing video or audiogram formats are hidden from results even if Auphonic returns them

## Credit Billing

Auphonic bills based on processed audio duration:

- Minimum charge: 3 minutes per production
- Re-running with changed settings on the same input does not trigger a new charge (per Auphonic's pricing FAQ)
- Creating a new production from the same audio does trigger a new charge
- ChapterForge shows your available balance before submission and the actual credits used after completion

## Job History

**Auphonic > Job History** shows all submitted jobs with:

- Title, status, credits used, and submission timestamp
- **Download Results** - saves allowed output files to a folder you choose
- **Publish** - triggers publishing for jobs held at review-before-publish

## Data Storage

All Auphonic job data is stored locally in `%APPDATA%\ChapterForge\auphonic.db` (SQLite). Nothing is sent to ChapterForge's servers.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Not connected to Auphonic" | Open Connect Account and click Connect |
| "Insufficient credits" | Purchase credits at auphonic.com or use a shorter file |
| "File contains a video stream" | Convert to audio-only before using (e.g., extract audio with ffmpeg) |
| Token expired | Open Connect Account - ChapterForge refreshes automatically, or reconnect |
| Job stuck in Processing | Job History > Refresh - polling continues in the background |
| OAuth credentials not configured | Set AUPHONIC_CLIENT_ID and AUPHONIC_CLIENT_SECRET environment variables |
