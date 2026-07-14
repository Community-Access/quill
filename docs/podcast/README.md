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
   the snippet gallery and prompts, read aloud and voices, Word/EPUB/PDF,
   document rescue and OCR, OCR and image describe.
4. **Files and automation** (25–27): files everywhere, watch folders,
   publishing and share.
5. **AI** (28–39): agents, the voice catalog walkthrough, voice and
   conversation, transcription and the Listening Companion, the audio
   studio, setting up AI, Ask Quill, the AI library, the AI toolkit, and
   every-day writing style.
6. **Organization and production** (40–51): the Accessible Vault, vault
   power, Story Studio, the practice build-along, Story Studio plus Vault
   plus AIs, GLOW audit, GLOW for files, the author tools mega, the bundled
   Quillins, braille production, the developer console, and build your own
   Quillin.
7. **Trust, community, and the road ahead** (52).
8. **The power-user finish** (53–54): accessibility power user, and the
   final stability and redaction deep-dive.

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

2. Rebuild the cover art, feed, and site pages, then commit
   `docs/site/podcast/`:

```powershell
python docs/podcast/tools/make_cover.py
python docs/podcast/tools/build_feed.py
```

The feed lands at `https://community-access.github.io/quill/podcast/feed.xml`
with enclosures pointing at the release assets and the 3000x3000 cover attached
through RSS `<image>` and iTunes `<itunes:image>` tags. The episode index and
full transcripts are plain accessible HTML alongside it, including the cover alt
text and long description from `episodes.json`.

## Writing more episodes

Add `scripts/epNN-slug.txt` in the marker format, add the matching entry to
`episodes.json`, generate, upload, rebuild the feed. Keep turns short (a few
sentences), alternate hosts naturally, use `[PAUSE]` as a section break, and
write for the ear: no markdown, no symbols the TTS would read literally,
keystrokes spelled the way they should be spoken. Each script is 3,500–4,500
words with seven to nine `[PAUSE]` markers, a "do this now" interactive beat
before any hands-on segment, code-verified claims against the running code,
and a four-step homework block.
