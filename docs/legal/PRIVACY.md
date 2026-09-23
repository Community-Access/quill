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

## User responsibility

You are responsible for reviewing AI-generated output before using, sharing, or publishing it. For sensitive content, use local models when possible and verify that cloud use meets your organization's security and compliance requirements.
