# The QUILL Cast — podcast pipeline

A **54-episode**, two-host audio course that leads a brand-new user from
installation to every feature family QUILL has, in eight parts:

1. **First steps** (1–7): welcome, install, your first document, the main
   window, notebooks and versions, the command palette, what QUILL says.
2. **The everyday editor** (8–17): moving through text, the QUILL key, the
   keymap editor, editing power tools, the power tools deep dive, find and
   replace, compare, spelling and word tools, languages and thesaurus, never
   lose work.
3. **Documents and formats** (18–24): Markdown, the text-supply toolkit,
   the snippet gallery and prompts, rich formatting and hidden codes,
   Word/EPUB/PDF, document rescue and OCR, OCR and image describe.
4. **Files and automation** (25–27): files everywhere, watch folders,
   publishing and share.
5. **Speech and audio** (28–33): read aloud and voices, the voice catalog
   walkthrough, dictation, voice and conversation, transcription and the
   Listening Companion, the audio studio.
6. **AI** (34–39): setting up AI, Ask Quill, the AI library, the AI toolkit,
   every-day writing style, and agents.
7. **Organization and production** (40–51): the Accessible Vault, vault
   power, Story Studio, the practice build-along, Story Studio plus Vault
   plus AIs, GLOW audit, GLOW for files, the author tools mega, the bundled
   Quillins, braille production, the developer console, and build your own
   Quillin.
8. **Trust, community, and the power-user finish** (52–54): trust and the
   road ahead, accessibility power user, and the final stability and
   redaction deep-dive.

These part ranges are also `PARTS` in `tools/build_feed.py`, which files the
episode index under them; change both together.

The hosts, Liam and Jessica, are QUILL's own on-device **Kokoro** neural
voices (`am_liam` and `af_jessica`) — the podcast is produced with the same
speech engine the product ships. Total series length is roughly 4 hours.

## Layout

```text
docs/podcast/
  episodes.json         Series + per-episode metadata (titles, descriptions,
                        publish dates, audio base URL).
  scripts/ep01-*.txt    The transcripts: [LIAM] / [JESSICA] / [PAUSE] markers,
                        one turn per block. These are the canonical teaching
                        text and double as the published transcripts.
  tools/generate_kokoro.py
                        Synthesizes every episode to WAV + MP3 with Kokoro.
   tools/make_cover.py   Draws the 3000x3000 podcast cover PNG locally with
                                    Pillow; no network service is used.
  tools/build_feed.py   Builds the RSS feed, the accessible episode index
                        page, and per-episode transcript pages under
                        docs/site/podcast/ (served by GitHub Pages).
  tools/refresh_audio_manifest.py
                        Reads the podcast-v1 release (read-only) and rewrites
                        audio_assets.json.
  audio_assets.json     The audio that really exists on the release: every
                        asset's name, size and upload time, the date it was
                        read, and each episode's file and status.
  audio/                Generated audio (not committed; distributed via the
                        podcast-v1 GitHub release).
```

## Which episodes have audio

The site links an episode's MP3, and the feed lists the episode, only when
`audio_assets.json` marks it `published`: its file (`<slug>.mp3`, the name
`build_feed.py` derives) is on the `podcast-v1` release **and** was uploaded
after the episode's script last changed in git. Otherwise the status is
`missing` (no such file) or `stale` (a file of that name exists but was
recorded from an older script), the transcript page says "The audio for this
episode is not published yet", and the episode is left out of the feed.

Leaving it out of the feed is deliberate. Podcast apps treat the
`<enclosure>` as the episode: Apple Podcasts and most others silently drop an
item that has none, and some show it as a row that cannot play. A feed that
lists only playable episodes reads correctly in every app, and readers still
have every transcript on the site.

The site links gate (`tests/unit/docs/test_site_links.py`) fails on any page
that links podcast audio the manifest does not mark published, and on a
manifest that is out of step with `episodes.json`.

As of 2026-10-15 no episode is published. The release still holds the 36 MP3s
of the retired 36-episode series (uploaded 2026-07-02). Four of them,
episodes 1 to 4, share a name with today's episodes, but they are recordings
of the old scripts of about 600 words each, rewritten to about 4,000 words on
2026-07-10, so the manifest marks them `stale`. The other 32 old files match no
current episode name and are linked from nowhere.

## Recording and publishing the missing audio

Run these from the repository root on the machine with the Kokoro models.
Steps 5 and 6 are the only ones that change anything on GitHub.

1. Make sure every script change is committed. An upload older than its
   script's last commit reads as `stale`.
2. Move any old audio out of the way, so nothing is skipped and the durations
   are fresh. `audio/` is not committed; an `ep01-welcome-to-quill.mp3` from
   2026-07-10 and a `durations.json` from 2026-07-05 were in the main checkout:

```powershell
Rename-Item docs/podcast/audio docs/podcast/audio-old
```

3. Record all 54 episodes (about 4 hours of audio; expect a long run). To do a
   few at a time, repeat `--slug`:

```powershell
python docs/podcast/tools/generate_kokoro.py
python docs/podcast/tools/generate_kokoro.py --slug ep05-notebooks-and-versions --slug ep06-the-command-palette
```

4. Listen to the start of a couple of files, and check there are 54 MP3s:

```powershell
(Get-ChildItem docs/podcast/audio/*.mp3).Count
```

5. Upload them. `--clobber` is needed because episodes 1 to 4 replace the
   stale files of the same name:

```powershell
gh release upload podcast-v1 (Get-ChildItem docs/podcast/audio/*.mp3).FullName --repo Community-Access/quill --clobber
```

6. Optional: the 32 old-numbering files that match no episode can be deleted
   from the release one at a time with
   `gh release delete-asset podcast-v1 <name> --repo Community-Access/quill`.
   Nothing links them, so leaving them is harmless.
7. Refresh the manifest, rebuild the site, and run the gate:

```powershell
python docs/podcast/tools/refresh_audio_manifest.py
python docs/podcast/tools/build_feed.py
python -m pytest tests/unit/docs/test_site_links.py -q
```

   The refresh prints how many episodes are published, stale and missing;
   expect 54 published. `refresh_audio_manifest.py --check` exits 1 when the
   committed manifest no longer matches the release.
8. Commit `docs/podcast/audio_assets.json` and `docs/site/podcast/`.

## Producing the audio

1. Kokoro model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) must be in
   `tools/models/` or pointed at via `QUILL_KOKORO_MODEL_DIR`. QUILL's own
   Kokoro download (Voice Picker, or `kokoro-models.zip` on the `assets-v1`
   release) provides them.
2. `pip install kokoro-onnx soundfile numpy`; ffmpeg on PATH for MP3.
3. Run:

```powershell
python docs/podcast/tools/generate_kokoro.py            # all episodes
python docs/podcast/tools/generate_kokoro.py --slug ep23-document-rescue-ocr
```

The generator skips any episode whose MP3 is already in `audio/`; add
`--force` to record it again.

Pacing (speed 1.06, short same-speaker gaps, longer speaker-change gaps, a
0.9 s beat at every `[PAUSE]`) is tuned for a conversational two-host cadence;
override with the CLI flags if a different feel is wanted.

## Publishing

1. Upload the MP3s to the **`podcast-v1`** release on Community-Access/quill
   (a non-`v*` tag, so it never touches the product release or autoupdate
   feed — the same model as `assets-v1`):

```powershell
gh release upload podcast-v1 (Get-ChildItem docs/podcast/audio/*.mp3).FullName --repo Community-Access/quill --clobber
```

2. Refresh the audio manifest, rebuild the cover art, feed, and site pages,
   then commit `docs/podcast/audio_assets.json` and `docs/site/podcast/`:

```powershell
python docs/podcast/tools/refresh_audio_manifest.py
python docs/podcast/tools/make_cover.py
python docs/podcast/tools/build_feed.py
```

The feed lands at `https://community-access.github.io/quill/podcast/feed.xml`
with enclosures pointing at the release assets (published episodes only) and the 3000x3000 cover attached
through RSS `<image>` and iTunes `<itunes:image>` tags. The episode index and
full transcripts are plain accessible HTML alongside it, including the cover alt
text and long description from `episodes.json`.

## Writing more episodes

Add `scripts/epNN-slug.txt` in the marker format, add the matching entry to
`episodes.json`, commit, generate, upload, refresh the manifest, rebuild the
feed. Keep turns short (a few
sentences), alternate hosts naturally, use `[PAUSE]` as a section break, and
write for the ear: no markdown, no symbols the TTS would read literally,
keystrokes spelled the way they should be spoken. Each script is 3,500–4,500
words with seven to nine `[PAUSE]` markers, a "do this now" interactive beat
before any hands-on segment, code-verified claims against the running code,
and a four-step homework block.
