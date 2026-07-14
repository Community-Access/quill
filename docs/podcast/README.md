# The QUILL Cast — podcast pipeline

A **36-episode**, two-host audio course that leads a brand-new user from
installation to every feature family QUILL has, in seven parts:

1. **First steps** (1–6): welcome, install, files, the window, the palette,
   what QUILL says.
2. **The everyday editor** (7–13): navigation, the QUILL key, the keymap,
   editing power tools, search, spelling, the safety stack.
3. **Documents and formats** (14–18): Markdown, the text-supply toolkit,
   hidden-codes formatting, Word/EPUB/PDF, document rescue and OCR.
4. **Files and automation** (19–20): remote/GitHub/SSH, watch folders.
5. **Speech** (21–24): voices, dictation, transcription and the Listening
   Companion, audio export/audiobooks/DAISY.
6. **AI** (25–28): setup and free paths, Ask Quill, the Library, agents.
7. **Organization, production, trust** (29–36): Vault, Story Studio, GLOW,
   braille, Quillins and the console, the finale.

The hosts, Liam and Jessica, are QUILL's own on-device **Kokoro** neural
voices (`am_liam` and `af_jessica`) — the podcast is produced with the same
speech engine the product ships. Total series length is roughly 2¼ hours.

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
  tools/build_feed.py   Builds the RSS feed, the accessible episode index
                        page, and per-episode transcript pages under
                        docs/site/podcast/ (served by GitHub Pages).
  audio/                Generated audio (not committed; distributed via the
                        podcast-v1 GitHub release).
```

## Producing the audio

1. Kokoro model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) must be in
   `tools/models/` or pointed at via `QUILL_KOKORO_MODEL_DIR`. QUILL's own
   Kokoro download (Voice Picker, or `kokoro-models.zip` on the `assets-v1`
   release) provides them.
2. `pip install kokoro-onnx soundfile numpy`; ffmpeg on PATH for MP3.
3. Run:

```powershell
python docs/podcast/tools/generate_kokoro.py            # all episodes
python docs/podcast/tools/generate_kokoro.py --slug ep04-document-rescue
```

Pacing (speed 1.06, short same-speaker gaps, longer speaker-change gaps, a
0.9 s beat at every `[PAUSE]`) is tuned for a conversational two-host cadence;
override with the CLI flags if a different feel is wanted.

## Publishing

1. Upload the MP3s to the **`podcast-v1`** release on Community-Access/quill
   (a non-`v*` tag, so it never touches the product release or autoupdate
   feed — the same model as `assets-v1`):

```powershell
gh release upload podcast-v1 docs/podcast/audio/*.mp3 --repo Community-Access/quill
```

2. Rebuild the feed and site pages, then commit `docs/site/podcast/`:

```powershell
python docs/podcast/tools/build_feed.py
```

The feed lands at `https://community-access.github.io/quill/podcast/feed.xml`
with enclosures pointing at the release assets; the episode index and full
transcripts are plain accessible HTML alongside it.

## Writing more episodes

Add `scripts/epNN-slug.txt` in the marker format, add the matching entry to
`episodes.json`, generate, upload, rebuild the feed. Keep turns short (a few
sentences), alternate hosts naturally, use `[PAUSE]` as a section break, and
write for the ear: no markdown, no symbols the TTS would read literally,
keystrokes spelled the way they should be spoken.
