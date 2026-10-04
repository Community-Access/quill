# Privacy Statement

This document describes how QUILL handles privacy for local and AI-assisted workflows.

## Core privacy commitments

1. QUILL is local-first by design. Your documents stay on your computer; nothing you write, dictate or record is sent anywhere unless you choose an action that sends it.
2. QUILL does not persist AI chat session transcripts by default.
3. **QUILL contains no tracking, analytics, advertising or usage reporting of any kind, and no identifier for your copy or your machine.** There is nothing that reports that you installed it, opened it, or what you did in it.
4. QUILL does not store document content in API-key storage or credential vault records.
5. A few features do contact the internet before you press anything, and they are listed under "Network requests you did not press a button for" below. QUILL used to claim here that it sent no network request without explicit user action; that was not true of every app in the family, and an unverifiable promise is worth less than an accurate list.

## Network requests you did not press a button for

Every one of these can be switched off, and all of them are off in Safe Mode
(`--safe-mode`).

| What | Where it goes | Default | Switch |
|---|---|---|---|
| Update check at launch | `api.github.com` -- asks for the list of releases; sends no version, account or machine detail | On | *Check for updates on launch*, in Preferences (each app has its own) |
| Quill Radio's station-catalogue refresh | `radio-browser.info` (and SomaFM) -- refreshes the local catalogue when the copy on disk is over six hours old, at launch and then daily | On | *Keep a local station catalogue* and *Check for station catalogue updates when Quill Radio starts* |
| Quill Radio's community play count | `radio-browser.info` -- when you play one of that directory's own stations, tells it so; sends the station's id and nothing about you | On | *Share play counts with the RadioBrowser directory* |
| Quill Radio's now-playing title | The station you are already listening to -- re-reads the current track title every 30 seconds. No third party is involved | On while playing | Stops with playback |
| Quill Radio's stream recovery | The failing station's own website, plus its provider's public address service -- only after a stream fails to play, once per station per session | On | *Recover failed streams from the station's website* |
| Quill Radio's new-video check | `youtube.com` -- for each channel you asked to be told about, reads its five newest uploads on the podcast refresh schedule; sends nothing about you unless you turned on the browser sign-in | Off (per channel) | *Notify Me About New Videos* on the channel |

Everything else -- every directory search, every AI request, every file
transfer, every podcast feed -- happens because you asked for it.

Every outbound call site in QUILL is inventoried in a build gate
(`quill/tools/network_egress_audit.py`): a new network call that is not
reviewed and listed fails the build. That is the mechanism this statement rests
on, rather than a promise to be careful.

## AI interaction data

When you use cloud AI providers, the prompt content you choose to send is transmitted to that provider. Provider-side storage, retention, and policy behavior are controlled by that provider's terms and settings, not QUILL.

QUILL does not persist Ask Quill chat transcripts or Writing Assistant interaction transcripts by default. If you explicitly copy output into a document, that content is then part of your document and saved according to your normal file and backup workflow.

## Key and credential handling

QUILL stores API keys using Windows Credential Manager when available. If Credential Manager is unavailable, QUILL falls back to DPAPI-encrypted local secret storage.

QUILL does not store API keys in plaintext.

## Local files QUILL may create

QUILL may create local settings and state files under your app data directory (for example `%APPDATA%\Quill\...`), including:

- editor and application settings
- onboarding state
- feature and UI preferences
- optional encrypted secret metadata

These files are local to your machine and are not uploaded by default.

### Developer Console history

If you use the QUILL Developer Console (QDC), each command you run is appended to a `history.jsonl` file in the app-data directory (up to 500 entries; oldest are removed first). Entries are passed through QUILL's redaction layer before being written, so API keys and tokens that match known patterns (GitHub PATs, OpenAI keys, AWS access keys, Slack tokens, and long alphanumeric tokens) are replaced with `[TOKEN]` in the history file.

If you believe sensitive data was stored before the redaction layer was active, you can delete the `history.jsonl` file from the app-data directory manually.

### GitHub temporary files

When you open a file from a GitHub repository using **File > Open from Remote**, QUILL downloads the file into a `github-temp` subdirectory of the app-data folder. These files are not automatically deleted when you close the tab or exit QUILL.

If you work with private repositories, review the `github-temp` directory periodically and delete files you no longer need. The directory is local to your machine and is not shared or uploaded.

### Read Document in Browser (experimental)

The optional **Read Document in Browser** feature (off by default, under **Settings > Experimental**) writes a self-contained reader page containing your document text to a `browser-reader` subdirectory of the app-data folder and opens it in your web browser. QUILL itself makes no network request for this feature, and the page is deleted when you close QUILL so no plaintext copy is left behind.

Be aware that the browser's speech voices are not all local. On-device voices (labelled "on this device" in the page's voice picker) synthesize speech locally. The browser's "Online (Natural)" voices synthesize in the voice vendor's cloud (for example, Microsoft Edge's online voices), which means selecting one sends the text being read to that service. Choose an on-device voice to keep everything local.

## YouTube in Quill Radio

Quill Radio uses YouTube API Services. By using its YouTube features you agree to the [YouTube Terms of Service](https://www.youtube.com/t/terms), and the [Google Privacy Policy](https://policies.google.com/privacy) applies to what Google does with your data.

**Without signing in.** Playing, searching, reading comments and reading live chat talk to YouTube directly, the way a web browser does. QUILL sends nothing about you beyond what any visitor to YouTube sends.

**Skip Sponsor Segments** (off until you turn it on) asks the community SponsorBlock service (`sponsor.ajay.app`) which parts of a video are sponsored. It sends only the first four characters of a scrambled (hashed) form of the video's id, so SponsorBlock cannot tell which video you are watching.

**Using your browser's YouTube sign-in** (off until you turn it on in Preferences). Quill Radio reads your browser's YouTube sign-in on your own computer each time it asks YouTube for something, so YouTube treats the request as coming from you. QUILL never sees your password. It saves only which browser you chose, or the location of a cookies.txt file, and never the sign-in itself. Sign-in data is removed from QUILL's logs and problem reports.

**Connect YouTube Account** (the official Google sign-in, when it is available). You sign in on Google's own page in your browser. QUILL asks Google for permission to read the channels and playlists you follow, and only if you then use a feature that needs it, to post comments, replies and live chat messages you write, to subscribe or unsubscribe, to rate videos, and to add videos to your playlists. QUILL does these things only when you press the button for them. The permission Google gives QUILL is kept in Windows' secure credential store, never in QUILL's own files and never on any server. QUILL has no servers that receive your data, and what it reads from YouTube stays on your computer. Disconnect YouTube Account forgets the sign-in on your computer and also removes QUILL's access at Google. You can also remove QUILL's access at any time from your Google account at <https://myaccount.google.com/permissions>.

QUILL's use of information received from Google APIs adheres to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements.

## User responsibility

You are responsible for reviewing AI-generated output before using, sharing, or publishing it. For sensitive content, use local models when possible and verify that cloud use meets your organization's security and compliance requirements.
