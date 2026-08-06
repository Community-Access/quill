# Section — Speech, Dictation, Read Aloud & OCR (`tools.*`, 36 commands)

Everything QUILL does with **your voice and your ears**: reading the document
aloud in a TTS voice, turning that speech into audio files, **dictating** by
microphone, driving QUILL hands-free with **voice commands** and "Hey QUILL",
pulling text out of images and the screen with **OCR**, choosing how spoken
announcements are routed, and checking the **dictionary / spelling** status.
Finish **Part 0** first.

This is a **sibling** of `section-tools-ai.md` (AI writing/analysis) and
`section-tools-misc.md` (compare, keymap, macros). Those own the `tools.ai_*`
and utility commands; this section owns only speech, dictation, read-aloud, OCR,
and the announcement/dictionary tools listed below.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `tools.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/
Accessible boxes. The Read Aloud journey is also walked end-to-end in
`../qa-core-journeys.md` → **JOURNEY-007 (Read Aloud)**; use this section for the
per-command detail and that journey for the whole-feature flow.

**Read this before you begin — the three big preconditions**

- **A distinct TTS voice for Read Aloud.** Read Aloud speaks through QUILL's own
  chosen TTS engine/voice (SAPI5, Piper, Kokoro, DECtalk, eSpeak-NG, ElevenLabs,
  or the OS voice) — **not** your screen reader. Have at least one Windows/SAPI
  voice installed. When Read Aloud and your screen reader would talk at once, the
  point of the test is that you can tell the two voices apart.
- **A working microphone + the offline speech engine + a model** for anything
  that *listens* (Dictate, Locked Dictation, Voice Command, Conversation, Hey
  QUILL, Transcribe, Captions). QUILL uses an on-device (offline) engine plus a
  downloaded speech **model**; microphone capture needs the optional
  `sounddevice` package. If capture support, the engine, or a model is missing,
  QUILL says exactly what to install — mark those scenarios **Blocked** and note
  which piece was absent.
- **An OCR engine** for OCR. *OCR Image / Clipboard / Screen* use the **built-in
  Windows OCR engine** (Windows 10/11) — no extra install on Windows. The
  *document-conversion and services* path can additionally use **Tesseract**
  (free, local — install via **Install Local OCR Engine**) or a configured cloud
  service. If no OCR engine is available on the platform at all, mark **Blocked**.

Common inputs used below (copy `../qa-samples/` onto the machine first):
`plain.txt`, `formatting.md`. You will also need a short **audio or video clip**
with clear speech, an **image containing text** (a screenshot of a paragraph is
fine), and a quiet room to speak in.

Open the **Command Palette** with **Ctrl+Shift+P** wherever a scenario offers it.

---

## TSP-01 — Read Aloud: Start / Pause (`tools.read_aloud_start_pause`, Ctrl+Shift+Grave, R)

*What & why.* Read the document out loud in QUILL's TTS voice from the caret (or
from your selection), and pause/resume on the same key. The everyday "read this
back to me."

**Before you start**
- Open `formatting.md`. Put the caret at the very top (**Ctrl+Home**).
- At least one TTS voice installed (see preconditions).
- The chord is a two-step: press **Ctrl+Shift+Grave** (Grave is the backtick
  key), release, then **R**.

**Do this**
1. Trigger the chord **Ctrl+Shift+Grave, R**, or open **Tools menu (Alt, T) ▸
   Reading and Dictation ▸ Read Aloud ▸ Start / Pause**.
2. Let it read a few lines, then trigger the same chord again to **pause**.
3. Trigger it once more to **resume** from where it paused.

**You should see and hear**
- Reading begins from the caret in the **Read Aloud TTS voice** (audibly a
  different voice from your screen reader); the status bar shows **"Read aloud
  started"**. The second press pauses (status **"Read aloud paused"**) and the
  third resumes from the pause point, not the top. If a range was selected, only
  that range is read. If no TTS voice is available, a spoken/OK message says so
  rather than failing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-02 — Read Aloud: Stop (`tools.read_aloud_stop`, Ctrl+Shift+Grave, Shift+R)

*What & why.* Stop reading entirely (not pause) and reset to the top of the next
read.

**Before you start**
- Start a Read Aloud (TSP-01) so speech is playing.
- Chord: **Ctrl+Shift+Grave** then **Shift+R**.

**Do this**
1. Trigger **Ctrl+Shift+Grave, Shift+R**, or **Tools menu ▸ Reading and
   Dictation ▸ Stop Reading**.

**You should see and hear**
- Speech stops immediately; the status bar shows **"Read aloud stopped"**. A
  fresh **Start / Pause** afterwards begins from the caret/selection again (it
  does **not** resume the stopped position — that is what Pause is for).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-03 — Read Aloud: Voice… (`tools.read_aloud_voice`)

*What & why.* Choose which engine and voice Read Aloud uses (and its rate, pitch,
volume). This is where you pick a voice **distinct from your screen reader**.

**Before you start**
- Any document open.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Voice…**.
2. Tab through the engine/voice controls; pick a voice; adjust the rate; confirm
   with **OK**.

**You should see and hear**
- The Read Aloud configuration dialog opens (this is the **same dialog** as
  *Settings…* in TSP-04); every control is labelled and keyboard-reachable. The
  choice is saved and a subsequent **Start / Pause** (TSP-01) uses the new voice.
  **Escape** cancels with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-04 — Read Aloud: Settings… (`tools.read_aloud_settings`)

*What & why.* The full Read Aloud configuration surface (engine, voice, rate,
pitch, volume, sentence pause, pronunciation dictionaries).

**Before you start**
- Any document open.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Settings…**.
2. Change one setting (for example the rate), confirm, then do a short **Start /
   Pause** to hear the effect.

**You should see and hear**
- The same labelled, keyboard-complete configuration dialog as *Voice…* opens;
  changes are saved and take effect on the next read. **Note:** because *Voice…*
  and *Settings…* open one shared dialog, a difference between the two menu
  labels is a surface note, not a behavior fault.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-05 — Read Aloud: Generate Audio… (`tools.read_aloud_generate_audio`)

*What & why.* Synthesize the current document (or your selection) to an **audio
file** you can keep or share — a one-shot "save this as speech."

**Before you start**
- Open `formatting.md` (or select a paragraph in any document).
- For compressed formats (MP3, M4A, M4B, OGG, Opus, FLAC) you need **ffmpeg**
  installed (TSP-18); plain **WAV** always works without it.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Generate Audio…**.
2. In the Save dialog, choose a format (WAV, or a compressed format if offered),
   name it, and confirm.

**You should see and hear**
- If nothing is open/typed, QUILL says **"There is nothing to export…"** rather
  than writing an empty file. Otherwise it synthesizes off the UI thread and
  writes the chosen file; markup like `#`, `**`, and links is cleaned before
  synthesis so it is not spoken as symbols. The compressed formats appear in the
  type list **only** when ffmpeg is present. The written file plays back the
  document text in the Read Aloud voice. **Note:** the Tools ▸ Speech ▸ *Export to
  Speech Audio…* item is the same feature reached from the Speech menu.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-06 — Read in Browser (Experimental) (`tools.read_aloud_edge`) [GATED]

*What & why.* Open an accessible reader page in your real browser, where the full
online/natural voices (e.g. Edge's Online voices) are available — richer than the
embedded voices.

**Before you start**
- This is **experimental and opt-in**. It appears in the menu (and is runnable)
  **only** after you enable it under **Preferences ▸ Experimental**
  ("Read the document aloud in your browser") and acknowledge the experimental
  notice. If it is off, mark **N/A** (do not fail it for being missing).
- Some document text open.

**Do this**
1. Enable the setting under **Preferences ▸ Experimental** (takes effect at
   once), then **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Read in
   Browser (Experimental)**.

**You should see and hear**
- If the setting is off, running it (e.g. from the palette) shows a message
  telling you to turn it on under Preferences ▸ Experimental — it does not error.
  When on, QUILL writes a self-contained accessible reader page and opens it in
  your chosen browser; the status bar names the browser and says to pick a voice
  and press Play. The reader page itself has a labelled voice picker and
  Play/Pause/Stop.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-07 — Audiobook & Batch Speech… (`tools.speech_batch_export`)

*What & why.* The **Audio Studio** wizard: turn one or many documents (or a whole
folder) into speech audio in a batch — the audiobook/production path, beyond the
one-shot Generate Audio.

**Before you start**
- A TTS voice available (as for Read Aloud). Have `formatting.md` (or a folder of
  documents) ready as a source.

**Do this**
1. **Tools menu ▸ Speech ▸ Audiobook & Batch Speech…**.
2. Walk the wizard by keyboard: choose the source(s), the voice/engine, and the
   output; start the run.

**You should see and hear**
- The Audio Studio wizard opens as a keyboard-navigable, announced multi-step
  surface; each step's controls are labelled. Cancelling any step reports
  **"Audio Studio cancelled"** and writes nothing. On completion the batch
  produces the audio file(s) and your choices/source are remembered for next
  time. Progress is announced; the UI never blocks.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-08 — OCR Image… (`tools.ocr_image`)

*What & why.* Read the text out of an image file into an editable document.

**Before you start**
- An **image file that contains text** (PNG/JPG/TIF/BMP). On Windows this uses
  the built-in OCR engine; if OCR is unavailable on the platform, mark
  **Blocked**.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR Image…**.
2. Pick your image; when asked, **confirm** the local OCR run (**Yes**).

**You should see and hear**
- A labelled file picker opens. Before recognizing, QUILL asks to run OCR
  **locally with the built-in Windows engine** and lets you decline (declining
  says **"OCR cancelled"**). On **Yes**, progress is announced off-thread and the
  recognized text appears in a review dialog / new document. It never uploads
  your image.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-09 — OCR Clipboard Image (`tools.ocr_clipboard`)

*What & why.* OCR whatever image is on the clipboard right now — grab a picture,
copy it, read its text.

**Before you start**
- **Copy an image to the clipboard** first (e.g. Snip a region with
  Win+Shift+S). Same OCR-engine precondition as TSP-08.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR Clipboard Image**.

**You should see and hear**
- With no image on the clipboard, QUILL says **"There is no image on the
  clipboard. Copy an image first…"** and stops — no crash. With an image, the
  status shows **"Reading clipboard image…"** and the recognized text opens in
  the review pipeline (no extra confirmation, because you already chose to run
  it).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-10 — OCR Screen Capture… (`tools.ocr_screen`)

*What & why.* Capture the whole screen or just the active window and OCR it — read
text that is only on screen (a dialog, another app).

**Before you start**
- Some on-screen text visible in another window. Same OCR-engine precondition.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR Screen Capture…**.
2. In the choice dialog choose **The whole screen** or **The active window**
   (default is the active window); confirm.

**You should see and hear**
- A labelled two-choice dialog (whole screen / active window) that is keyboard
  operable. On confirm the status shows **"Reading screen capture…"** and the
  recognized text opens in the review pipeline. A capture error is reported in a
  message box, not swallowed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-11 — Install Local OCR Engine (Tesseract) (`tools.install_local_ocr`)

*What & why.* Download the free, local **Tesseract** OCR engine for the document
conversion path — verified and opened for you, never installed silently.

**Before you start**
- Network available. Note whether Tesseract is already installed.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR and Document Conversion ▸ Install
   Local OCR Engine (Tesseract)…**.
2. Read the confirmation (version, size, "runs on this computer, never uploads")
   and choose **Yes**.

**You should see and hear**
- A clear confirmation stating the version, the download size (~MB), and that
  Tesseract is free and local; **No** cancels ("Local OCR install cancelled").
  On **Yes**, the download runs behind an announced status, is verified
  byte-for-byte, and the installer is **opened** for you to complete. A
  download/launch failure is reported as an **install** problem (not a
  conversion error). Afterwards QUILL finds the engine automatically for
  Import / Convert.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-12 — OCR and Conversion Services (`tools.ocr_services`)

*What & why.* A read-only overview page of every OCR/conversion path and whether
each is ready (local engine installed? cloud service configured?).

**Before you start**
- Any state.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR and Document Conversion ▸ OCR and
   Conversion Services…**.

**You should see and hear**
- A readable page that states the **local OCR engine status** ("installed (path)"
  or "not installed — free download available") and the **cloud OCR status**
  (Ready / needs an API key / disabled). It is navigable by keyboard and closes
  back to the editor. It only reports status; it changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-13 — OCR Service Settings (`tools.ocr_service_settings`)

*What & why.* Configure the OCR/conversion services (e.g. a cloud provider's key
and options) used by the conversion path.

**Before you start**
- Any state.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR and Document Conversion ▸ OCR
   Service Settings…**.
2. Tab through the fields; if you enter a key, confirm; otherwise **Escape**.

**You should see and hear**
- A labelled, keyboard-complete settings surface for the OCR services; any secret
  (API key) is stored via the platform secret store, not printed in plain text.
  Escape cancels with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-14 — Delete OCR Temporary Files (`tools.delete_ocr_temp`)

*What & why.* Clear any leftover OCR job files (e.g. after a crash mid-conversion).

**Before you start**
- Any state (ideally after you have run at least one conversion).

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ OCR and Document Conversion ▸ Delete
   OCR Temporary Files**.

**You should see and hear**
- With nothing to clear, the status shows **"No OCR temporary files to delete"**.
  Otherwise QUILL announces **"Deleted N OCR temporary item(s)."** and the status
  shows **"OCR temporary files deleted"**. No confirmation prompt is needed
  because only QUILL's own temp folder is touched.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-15 — Speech and Dictation (Manage Speech Models) (`tools.speech_models`)

*What & why.* The unified **Speech Hub** where you download/manage offline speech
**models** and pick the dictation engine. Everything that *listens* depends on a
model being installed here.

**Before you start**
- Network available (to download a model). Note whether any model is installed.

**Do this**
1. **Tools menu ▸ Speech ▸ Speech and Dictation…**.
2. On the **Dictation (Offline)** tab, review the model list; download the
   recommended model if none is installed; set a default.

**You should see and hear**
- The Speech Hub opens on the Dictation (Offline) tab as a keyboard-navigable,
  announced dialog. Available and installed models are listed with sizes;
  downloading runs behind an announced progress and the model becomes selectable.
  This is the dialog other scenarios send you to when a model is missing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-16 — Transcribe Audio or Video (Offline) (`tools.speech_transcribe`)

*What & why.* Turn a recording (audio or video) into a text transcript entirely
on-device.

**Before you start**
- A short **audio/video clip** with clear speech. A speech model installed
  (TSP-15). For non-WAV inputs (MP3, MP4, M4A…) you need **ffmpeg** (TSP-18). If
  no model, mark **Blocked**.

**Do this**
1. **Tools menu ▸ Speech ▸ Transcribe Audio or Video (Offline)…**.
2. Choose the model and whether to label speakers (diarize); choose the output
   format (text / Markdown / HTML); pick the file; let it run.

**You should see and hear**
- If no model is installed, QUILL offers to open Manage Speech Models rather than
  failing. Otherwise it announces **"Transcribing <name>. This can take a while…"**
  behind a cancelable progress dialog; cancelling reports the cancel cleanly. On
  success a draft transcript opens in a new document and QUILL announces
  **"Transcription complete[ with speaker labels]. N words."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-17 — Generate Captions (Offline) (`tools.speech_captions`)

*What & why.* Produce timed captions (**.srt** / **.vtt**) from a recording.

**Before you start**
- A short clip with speech; a model installed (else **Blocked**); ffmpeg for
  non-WAV inputs.

**Do this**
1. **Tools menu ▸ Speech ▸ Generate Captions (Offline)…**.
2. Pick the clip; when it finishes, choose **SubRip (.srt)** or **WebVTT (.vtt)**;
   choose where to save.

**You should see and hear**
- Progress is announced (**"Captioning <name>"**). You are offered the two caption
  formats in a labelled choice dialog, then a Save dialog defaulting to
  `<name>.srt`/`.vtt`. On save QUILL announces **"Captions saved to <name>."** If
  the clip produced no timed segments, it says captions cannot be made rather
  than writing an empty file.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-18 — Download FFmpeg (`tools.speech_ffmpeg`)

*What & why.* Fetch an official ffmpeg build so QUILL can read compressed audio/
video (MP3, M4A, MP4…) and write compressed speech audio. ffmpeg is not bundled.

**Before you start**
- Network available. **Windows only** for the automatic download.
- Reach the command via **Command Palette (Ctrl+Shift+P) → "Download FFmpeg"**
  (it is also offered under **Help ▸ Download Optional Components**).

**Do this**
1. Run **Download FFmpeg**.
2. Read the confirmation (~110 MB, open-source, fetched from the official
   builder) and choose **Yes**.

**You should see and hear**
- On non-Windows, QUILL explains to install ffmpeg via Homebrew/your package
  manager instead — it does not error. If ffmpeg is already present it asks
  whether to fetch QUILL's own managed copy anyway. On **Yes** the download runs
  behind a cancelable, announced percentage; on success ffmpeg-only formats
  become available in TSP-05/16/17.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-19 — Hugging Face Token (`tools.speech_hf_token`)

*What & why.* Store an **optional** Hugging Face access token to raise model
download rate limits. Not required — QUILL's models work without one.

**Before you start**
- Optionally a Hugging Face account and a **Read**-role token.

**Do this**
1. **Tools menu ▸ Speech ▸ Hugging Face Token…**.
2. First time: read the numbered how-to and optionally let QUILL open the token
   page. Then paste the token into the **masked** field and confirm. To remove a
   saved token, leave the field **blank** and confirm.

**You should see and hear**
- Clear guidance that the token is optional. The entry field is a **password
  (masked)** field. On save QUILL announces **"Hugging Face token saved."**; a
  blank value announces **"Hugging Face token cleared."** The token is saved to
  the **OS credential store**, not to settings and never printed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-20 — Dictation Microphone (`tools.speech_microphone`)

*What & why.* Choose which microphone dictation and voice features record from.

**Before you start**
- At least one microphone connected. Capture support (`sounddevice`) installed.

**Do this**
1. **Tools menu ▸ Speech ▸ Dictation Microphone…**.
2. Arrow the device list; pick a microphone; confirm.

**You should see and hear**
- With no microphones (or no capture support) QUILL says so plainly in a message
  box. Otherwise a labelled, keyboard-navigable device list appears; selecting one
  saves it and QUILL announces **"Dictation microphone set to <name>."** That
  device is used by all the listening features below.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-21 — Dictate (Offline) (`tools.speech_dictate`, Ctrl+Shift+Grave, Shift+D)

*What & why.* Push-to-talk dictation: run it to start listening, run it again to
stop and insert the recognized text at the caret. The main "type with your voice"
feature.

**Before you start**
- Microphone + capture support + a speech model (TSP-15). If any is missing, mark
  **Blocked** — QUILL will tell you which.
- Chord: **Ctrl+Shift+Grave** then **Shift+D**.

**Do this**
1. Put the caret where the text should land. Trigger **Ctrl+Shift+Grave, Shift+D**
   (or **Tools menu ▸ Speech ▸ Dictate (Offline)**).
2. Speak a sentence clearly.
3. Trigger the same command again to stop and insert.

**You should see and hear**
- Without capture support QUILL explains what to install and does not record.
  With no model it offers to open Manage Speech Models. When it starts you hear a
  start earcon and **"Listening. Run Dictate (Offline) again to stop and
  insert."** After stopping you hear **"Transcribing dictation…"**, then the text
  is written at the caret and QUILL announces **"Inserted N words. Press Control+Z
  to undo."** If nothing was heard it says **"No speech detected."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-22 — Dictation (system) (`tools.dictation_toggle`, Ctrl+Shift+Grave, D)

*What & why.* The legacy **system** dictation toggle. Offline dictation (TSP-21)
and Locked Dictation (TSP-23) are the supported paths; this command is retained
for back-compat and is not in the Speech menu.

**Before you start**
- Reach it via the chord **Ctrl+Shift+Grave** then **D**, or **Command Palette →
  "Dictation"**.

**Do this**
1. Trigger **Ctrl+Shift+Grave, D**.

**You should see and hear**
- If system dictation is unavailable on the machine (expected on most builds), a
  clear message box says **"System dictation is unavailable on this system."** —
  it must not crash or fail silently. Where it *is* available, focus goes to the
  editor and the status shows it started/stopped. If it reports unavailable,
  record that and mark **Blocked** for the system path (offline dictation TSP-21
  is the one that must pass).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-23 — Locked Dictation start / finish (`tools.dictation_lock_toggle`, Ctrl+F9)

*What & why.* Hands-free **locked** dictation: start a session, speak as long as
you like, finish to transcribe and insert as one undoable edit. The primary
keyboard dictation workflow.

**Before you start**
- Microphone + capture + a model (else **Blocked**). The very first use speaks a
  one-time hint.

**Do this**
1. Press **Ctrl+F9** (or **Tools menu ▸ Speech ▸ Locked Dictation ▸ Locked
   Dictation (start/finish)**).
2. Speak a sentence or two.
3. Press **Ctrl+F9** again (or **Escape**) to finish and insert.

**You should see and hear**
- A preflight guards it: Safe Mode ("Dictation is disabled in Safe Mode."),
  missing capture, missing engine (offers the ~8 MB verified download), or no
  model (points you at Speech and Dictation) each give a spoken message and stop.
  On first successful start you hear the one-time hint ("Press Control F9 to
  start… Escape to finish and insert; Shift Escape cancels."). Finishing
  transcribes off-thread and inserts the text as one undoable block.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-24 — Pause or Resume Dictation (`tools.dictation_pause`, Ctrl+Shift+F9)

*What & why.* Temporarily pause a live Locked Dictation session (e.g. to think or
cough) and resume without losing what you have said.

**Before you start**
- A **live** Locked Dictation session (start one via TSP-23).

**Do this**
1. Press **Ctrl+Shift+F9** to pause; press it again to resume. (Also under
   **Tools ▸ Speech ▸ Locked Dictation ▸ Pause or Resume**.)

**You should see and hear**
- The session pauses and resumes; the state change is perceivable (spoken/earcon
  and status). With no session active the key does nothing harmful. Speak, Status
  (TSP-25) confirms the paused/recording state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-25 — Dictation Status (`tools.dictation_status`, Alt+F9)

*What & why.* Speak what dictation is doing right now — a perceivability check for
a feature whose state you cannot see.

**Before you start**
- Optional: start/pause a Locked Dictation session to compare states.

**Do this**
1. Press **Alt+F9** (or **Tools ▸ Speech ▸ Locked Dictation ▸ Speak Status**),
   both when idle and during a live session.

**You should see and hear**
- When nothing is running it says **"Dictation is off."** During a session it
  speaks the current state (recording / paused / transcribing). The message is
  **forced** so it is heard even while other speech is queued.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-26 — Stop Dictation, keep speech (`tools.dictation_emergency_stop`, Escape)

*What & why.* Stop a live dictation session immediately but **keep** what you have
already spoken (transcribe and insert it).

**Before you start**
- A **live** Locked Dictation session recording.

**Do this**
1. Press **Escape** while the session is active (or **Tools ▸ Speech ▸ Locked
   Dictation ▸ Stop (keep speech)**).

**You should see and hear**
- Recording stops and the captured speech is transcribed and inserted (not
  discarded). Crucially, **Escape only does this while a session is active** — at
  every other time Escape behaves normally (closes dialogs, etc.). Verify normal
  Escape still works with no session running.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-27 — Cancel Dictation, discard (`tools.dictation_cancel`, Shift+Escape)

*What & why.* Abandon a live dictation session and **discard** the audio — nothing
is inserted.

**Before you start**
- A **live** Locked Dictation session recording.

**Do this**
1. Press **Shift+Escape** while the session is active (or **Tools ▸ Speech ▸
   Locked Dictation ▸ Cancel (discard)**).

**You should see and hear**
- The session ends and **no text is inserted**; the discard is perceivable. Like
  Escape, **Shift+Escape is only consumed while a session is active**, so it does
  not interfere the rest of the time.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-28 — Voice Command (Offline) (`tools.voice_command`)

*What & why.* Push-to-talk **command by voice**: speak one command ("save file")
and QUILL runs it — offline, and only commands on a safety allowlist.

**Before you start**
- Voice commands are **off by default**; turn them on in **Settings** first (they
  are always off in Safe Mode). Microphone + capture + a model. Else **Blocked**.

**Do this**
1. **Tools menu ▸ Speech ▸ Voice Command (Offline)**.
2. Speak a simple command (e.g. "save file"); run the command again to stop and
   act.

**You should see and hear**
- If voice commands are off, QUILL says **"Voice commands are off. Turn them on in
  Settings (they are disabled in Safe Mode)."** When on, it announces **"Listening
  for a command. Run the command again to stop and act."** After you stop it
  recognizes the phrase and, **only if** the resolved command is on the safe
  allowlist, announces and runs it; an unrecognized or unsafe phrase is reported
  and **not** run. (If Conversation mode is enabled in Settings, one Voice Command
  hands off to Conversation — TSP-29.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-29 — Voice Conversation Mode (`tools.voice_conversation`)

*What & why.* Hands-free conversation loop: warm audio cues for each state, a
brief cancel window before a command runs, and a follow-up window so commands
chain without re-arming.

**Before you start**
- Voice commands enabled in Settings (off in Safe Mode); microphone + capture + a
  model. Else **Blocked**.

**Do this**
1. **Tools menu ▸ Speech ▸ Voice Conversation Mode** to start; run it again to
   stop.

**You should see and hear**
- Same off/Safe-Mode/capture guards as TSP-28 (with spoken reasons). When it
  starts you hear state cues (earcons, and spoken cues if you enabled them **and**
  no screen reader is running — QUILL will not talk over your reader). Each
  recognized command has a cancel window and follow-ups chain. Running it again
  stops the loop with a closing cue.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-30 — Listen for Hey QUILL (Wake Word) (`tools.voice_wakeword`)

*What & why.* Always-listening for the phrase "Hey QUILL". "Hey QUILL, save file"
runs a command inline; a bare "Hey QUILL" opens one command turn.

**Before you start**
- Voice commands enabled (off in Safe Mode); microphone + capture + a model. Else
  **Blocked**.

**Do this**
1. **Tools menu ▸ Speech ▸ Listen for Hey QUILL** to start; run it again to stop.
2. Say "Hey QUILL, save file" (with a document that can be saved).

**You should see and hear**
- Same guards as TSP-28/29 with spoken reasons. When on, the mic stays open in
  short windows; the live-mic state stays perceivable (visible status and a
  periodic reminder). An inline "Hey QUILL, <command>" runs the (allowlisted)
  command; a bare "Hey QUILL" opens one command turn. Running it again stops
  listening. **Speak Voice Status** (TSP-31) confirms it is live.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-31 — Speak Voice Status (`tools.voice_status`)

*What & why.* Say out loud what the voice features are doing right now — the
"is my mic live?" check.

**Before you start**
- Optionally start Conversation (TSP-29) or Hey QUILL (TSP-30) first to compare.

**Do this**
1. **Tools menu ▸ Speech ▸ Speak Voice Status**, both while idle and while a voice
   feature is listening.

**You should see and hear**
- When nothing is listening it says **"Voice is not listening right now."** When a
  wake/conversation/command session is active it speaks the live state(s) (e.g.
  "Listening for a command"). The same text also appears in the status bar.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-32 — Announcement Backend… (`tools.announcement_backend`)

*What & why.* Choose **how** QUILL routes its spoken announcements: **Auto**,
**Prism** (the screen-reader bridge), or **Status only** (no speech, status bar
text only).

**Before you start**
- A screen reader running so you can hear the difference.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Announcement Backend…**.
2. Arrow the three choices; pick one; confirm.

**You should see and hear**
- A labelled single-choice dialog with exactly three options (Auto / Prism /
  Status only), pre-selected on the current setting; **Escape** cancels
  ("Announcement backend selection cancelled"). On confirm the routing changes and
  subsequent announcements follow it — e.g. **Status only** shows announcements as
  status-bar text without speaking them.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-33 — Toggle Announcement Trace Capture (`tools.announcement_trace_toggle`)

*What & why.* Jump to where announcement-trace capture (a diagnostic log of what
QUILL announced) is turned on/off.

**Before you start**
- Any state.

**Do this**
1. **Tools menu ▸ Reading and Dictation ▸ Read Aloud ▸ Announcement Trace (in
   Settings)…** (or **Command Palette → "Toggle Announcement Trace Capture"**).

**You should see and hear**
- QUILL opens **Settings** and the status bar says **"Announcement trace setting
  is in Settings > Accessibility"** — it takes you to the toggle on the
  Accessibility tab rather than flipping it blindly. Settings is keyboard
  navigable and Escape closes it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-34 — Dictionary Status… (`tools.dictionary_status`)

*What & why.* Report the spell-check backend, the thesaurus availability, and how
many custom words are in each dictionary scope (Personal / Document / Project),
with where each is stored.

**Before you start**
- Optionally a **saved** document (so the Document-scope path can be shown).

**Do this**
1. **Tools menu ▸ Writing and Language ▸ Dictionary Status…** (or **Command
   Palette → "Dictionary Status"**).

**You should see and hear**
- A readable report naming the **spell-check backend** and its detail, whether the
  **thesaurus** is installed, and the **Personal / Document / Project** word
  counts with each file's path (or "not created yet" / "not available until the
  document is saved"). Navigable by keyboard; closes back to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-35 — Misspelling List… (`tools.misspelling_list`, Alt+Shift+L)

*What & why.* List every misspelling in the document and jump straight to any one.

**Before you start**
- Type a few obvious misspellings into a document (e.g. "teh", "recieve").

**Do this**
1. Press **Alt+Shift+L** (or **Tools menu ▸ Writing and Language ▸ Misspelling
   List…**).
2. Arrow the list; press **Enter** on one.

**You should see and hear**
- With none, the status shows **"No misspellings found"**. Otherwise a
  keyboard-navigable navigator lists the misspelled words; selecting one moves the
  caret and **selects** that word in the editor (status: `Jumped to misspelling
  "<word>"`). **Escape** cancels ("Misspelling list cancelled") and leaves the
  caret where it was.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-36 — Next Misspelling (`tools.next_misspelling`, Ctrl+F7)

*What & why.* Jump the caret to the next misspelled word after the cursor —
review-as-you-go without opening a list.

**Before you start**
- A document with at least one misspelling ahead of the caret.

**Do this**
1. Press **Ctrl+F7** (or **Tools menu ▸ Writing and Language ▸ Next
   Misspelling**).

**You should see and hear**
- The caret moves to the next misspelling and **selects** it; the status shows
  `Next misspelling: "<word>"`. When none remain ahead, QUILL announces a clear
  message (e.g. that there are none ahead, noting any behind the caret) rather
  than moving silently or erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-37 — Thesaurus… (`tools.thesaurus`, Shift+F7)

*What & why.* The classic (non-AI) thesaurus: look up synonyms for the word at the caret and replace it. Works with no AI provider and offline.

**Before you start**
- Open `plain.txt`; put the caret in a common word (e.g. "quick").

**Do this**
1. Press **Shift+F7**, or open **Tools ▸ Thesaurus…**.
2. Arrow the synonym list; pick one; confirm to replace, or Escape to cancel.

**You should see and hear**
- A keyboard-navigable, announced list of synonyms for the word; choosing one replaces the word in the document and says so; Escape leaves the word unchanged. If the word has no entry, it says so rather than staying silent. **Note:** verify exact wording.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TSP-38 — Review Last OCR Result (`tools.review_last_ocr`)

*What & why.* Reopen the text from your most recent OCR run to review or correct it, without re-scanning.

**Before you start**
- You have run an OCR command at least once this session (see the OCR scenarios above). If you have not, the command should say there is nothing to review — test that path too.

**Do this**
1. Run **Review Last OCR Result** (Tools, or Command Palette → "Review Last OCR").

**You should see and hear**
- The last OCR output opens for review (in a dialog or a document) and is announced; with no prior OCR this session, QUILL says there is no result to review rather than erroring. **Note:** verify exact wording and where the result opens.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 38
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
