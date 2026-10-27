# Privacy Statement

This statement covers QUILL and every app in the QuillVille family: QUILL Lite, Quill Radio, QUILL Cast, QUILL Studio, Quill Weather, Quill Inkwell, Quill Converter, QUILL Transcribe, QuillBeacon, Quill Media Player and QUILL Social. Where it says QUILL, it means all of them unless it names one.

## Core privacy commitments

1. QUILL is local-first by design. Your documents stay on your computer; nothing you write, dictate or record is sent anywhere unless you choose an action that sends it.
2. QUILL does not persist AI chat session transcripts by default.
3. **QUILL contains no tracking, analytics or advertising, and nothing reports that you installed it, opened it, or what you did in it.** The one exception is QUILL's free AI service, which is off until you turn it on: connecting a computer to it creates an account with no name on it (a device token, shown to you as a Support ID), and the service records how many requests that account makes, how big they were, which features you used and what they cost. It never records what you wrote or what came back. See "QUILL's free AI service" below.
4. QUILL does not store document content in API-key storage or credential vault records.
5. A few features do contact the internet before you press anything, and they are listed under "Network requests you did not press a button for" below. QUILL used to claim here that it sent no network request without explicit user action; that was not true of every app in the family, and an unverifiable promise is worth less than an accurate list.

## Network requests you did not press a button for

Every one of these can be switched off. In QUILL itself, Safe Mode (`--safe-mode`)
turns all of them off. In the other apps Safe Mode turns off everything except
an automatic update check where that app provides one; that check still runs on
its own schedule.

| What | Where it goes | Default | Switch |
|---|---|---|---|
| App update check, at most once a day at launch (QUILL, QUILL Lite, Quill Radio, QUILL Cast and QUILL Studio) | `community-access.github.io` (a signed list of releases), falling back to `api.github.com`. The request carries a generic User-Agent and no version, account or machine detail. On the Beta and Dev release channels, an update it finds is also downloaded in the background; it is never installed without asking | On by default in those five apps | In each app's Preferences; for example *Check for updates on startup* in QUILL and *Look for updates when QUILL Lite starts* in QUILL Lite |
| Quill Radio's station-catalogue refresh | `radio-browser.info`, SomaFM and the Icecast directory (`dir.xiph.org`) -- refreshes the local catalogue when the copy on disk is over six hours old, at launch and then daily | On | *Keep a local station catalogue* and *Check for station catalogue updates when Quill Radio starts* |
| Quill Radio's community play count | `radio-browser.info` -- when you play one of that directory's own stations, tells it so; sends the station's id and nothing about you | On | *Share play counts with the RadioBrowser directory* |
| Quill Radio's now-playing title | The station you are already listening to -- re-reads the current track title every 30 seconds. No third party is involved | On while playing | Stops with playback |
| Quill Radio's stream recovery | The failing station's own website, plus its provider's public address service -- only after a stream fails to play, once per station per session | On | *Recover failed streams from the station's website* |
| Quill Weather's alert watch | `api.weather.gov` -- checks the alerts for your saved locations every 10 minutes, and every minute while an alert is active; it keeps running in the tray after the window closes | On in the Quill Weather app once you add a location (off in the editor's weather features) | *Start Monitoring* / *Stop Monitoring* |
| QUILL Social's timelines and feeds | Each account's own server (Mastodon, Bluesky) at launch, and each RSS feed you follow, by default every 15 minutes; posts you scheduled are published at their time | On for the accounts and feeds you added | Remove the account or feed. QUILL Social has no Safe Mode, and its RSS requests name the app and its version in the User-Agent |
| Quill Radio's new-video check | `youtube.com` -- for each channel you asked to be told about, reads its five newest uploads on the podcast refresh schedule; sends nothing about you unless you turned on the browser sign-in | Off (per channel) | *Notify Me About New Videos* on the channel |

Quill Weather, Quill Inkwell, Quill Converter, Quill Media Player and QUILL
Transcribe do not check for app updates automatically at launch. They check
only when you choose **Help > Check for Updates**. QuillBeacon has no in-app
update check.

Everything else -- every directory search, every AI request, every file
transfer, every podcast feed -- happens because you asked for it, or because
you set a schedule yourself. Those schedules are all off until you set them:
checking podcasts for new episodes, downloading new episodes automatically,
and Quill Radio's resume-on-launch. Opening a window can also fetch what it
shows: Quill Radio's Browse Stations loads its directories, Weather Now
refreshes the forecast, and the free AI windows ask the service for your
remaining allowance.

Every outbound call site in the apps built from the `quill` package -- every app
except QUILL Social, which has its own code base -- is inventoried in a build gate
(`quill/tools/network_egress_audit.py`): a new network call that is not
reviewed and listed fails the build. That is the mechanism this statement rests
on, rather than a promise to be careful.

## AI interaction data

### QUILL's free AI service

The free AI help in QUILL and QUILL Lite is off until you turn it on and agree to
what it sends. When you use it, the passage you ask about (or a few excerpts
QUILL picks on your computer, or only your question) goes over an encrypted
connection to QUILL's own service at `ai.community-access.org`, and from there
to OpenAI, which writes the answer. Connecting a computer creates an account
with no name on it; its token is kept in Windows Credential Manager. The service
keeps how many requests the account made, how big they were, which features
were used and what they cost, and nothing else: not what you wrote, not what
came back, not your name or email address. What OpenAI keeps is set by OpenAI's
own terms. If you use your own AI provider account instead, QUILL's service is
never involved.

### Other AI providers

When you use cloud AI providers, the prompt content you choose to send is transmitted to that provider. Provider-side storage, retention, and policy behavior are controlled by that provider's terms and settings, not QUILL.

QUILL does not persist Ask Quill chat transcripts or Writing Assistant interaction transcripts by default. If you explicitly copy output into a document, that content is then part of your document and saved according to your normal file and backup workflow.

## Dictation

Dictation in QUILL and QUILL Lite recognises your speech on your own computer.
The microphone opens only while dictation is on, or, if you switched on the
wake phrase, while QUILL is the window in front. No recording is kept, and
nothing is sent anywhere unless you choose a cloud speech engine: OpenAI with
your own key (below), or one of the providers on the Speech Providers page
(for example Azure, Google, Amazon, Deepgram, AssemblyAI, Speechmatics,
ElevenLabs, Gladia, Rev.ai, Groq, Mistral and IBM). Each asks first, the answer
is No unless you choose Yes, and all of them are refused in Safe Mode.

**OpenAI dictation, with your own key** (added October 2026). If you save your
own OpenAI key in Use My Own AI Key and then choose OpenAI as the dictation
speech engine, QUILL first asks, in plain words, whether your speech may be
sent; the answer is No unless you choose Yes, and you can take it back in More
Dictation Settings at any time. While dictation is on with that engine:

- each phrase you speak is sent to OpenAI (`api.openai.com`) over an encrypted,
  certificate-checked connection, and the words come back. Silence is not sent:
  only the speech QUILL's voice detector heard;
- the words in your My Words and Phrases list go with it, as words to expect,
  along with the dictation language;
- your key travels only in the request's authorization header. It is never
  logged, and QUILL's diagnostic bundles scrub anything that looks like a key;
- nothing goes through QUILL's servers, QUILL keeps no copy of the audio, and
  OpenAI bills your own account. What OpenAI keeps, and for how long, is set by
  OpenAI's own terms (openai.com/policies).

When More Dictation Settings opens on a computer with an OpenAI key saved,
QUILL asks OpenAI which speech models your key can use. That request sends
your key and nothing else. QUILL's free hosted AI is never used for dictation.
OpenAI dictation is refused in Safe Mode.

**Transcribe a Recording** (Shift+F5, added October 2026) reads a recording
you choose on your own computer, with the same engines, and keeps only the
text. If your own OpenAI key is saved, OpenAI's speech models are offered in
its list too (the list is asked of OpenAI the same way, sending only your
key). They are never chosen for you, and are refused in Safe Mode. Choosing
one asks, for each recording, whether to send it; the answer is No unless you
choose Yes. If you agree, the speech in that recording is sent to OpenAI's
transcription service about a minute at a time, over an encrypted connection,
with your key and the words from My Words and Phrases, and OpenAI bills your
account. Nothing goes through QUILL's servers and QUILL keeps no copy.

**Tidy Dictated Text** sends the passage you choose, and your My Dictation
Instructions if you wrote any, to the AI service you use with your own key or
ChatGPT subscription, only when you press it.

## Key and credential handling

Installed copies keep API keys and sign-in tokens in Windows Credential Manager. Portable copies keep them in a DPAPI-encrypted `keys.enc` file in the portable folder, so they travel with it and can only be read by your Windows account. A key can also come from an environment variable you set yourself. If an installed copy cannot reach Credential Manager, the key is not saved at all; QUILL does not fall back to another store.

QUILL does not store API keys in plaintext.

## Local files QUILL may create

QUILL may create local settings and state files under your app data directory (for example `%APPDATA%\Quill\...`), including:

- editor and application settings
- onboarding state
- feature and UI preferences
- optional encrypted secret metadata

These files are local to your machine and are not uploaded by default.

### Developer Console history

If you use the QUILL Developer Console (QDC), each command you run is appended to `console\history.jsonl` in the app-data directory (up to 500 entries; oldest are removed first). Entries are passed through QUILL's redaction layer before being written, so API keys and tokens that match known patterns (GitHub PATs, OpenAI keys, AWS access keys, Slack tokens, and long alphanumeric tokens) are replaced with `[TOKEN]`, web tokens (JWTs) with `[JWT]`, and a user name and password written into a web address are removed.

If you believe sensitive data was stored before the redaction layer was active, you can delete the `history.jsonl` file from the app-data directory manually.

### GitHub temporary files

When you open a file from a GitHub repository using **File > Open from Remote** (GitHub Repository or GitHub File URL), QUILL downloads the file into a `github-temp` subdirectory of the app-data folder. When you exit QUILL, it deletes every file there that is not still open in a tab. The directory is local to your machine and is not shared or uploaded.

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

## Support messages

Help > Get Help from Support in each app prepares an email to
support@community-access.org in your own mail program, with the app's version
and your Windows version filled in so you can read them first. QUILL sends
nothing itself; the message goes only if you send it.

## User responsibility

You are responsible for reviewing AI-generated output before using, sharing, or publishing it. For sensitive content, use local models when possible and verify that cloud use meets your organization's security and compliance requirements.
