# Self-hosting: HuggingFace removal + ffmpeg pin (prepared, activate on upload)

Status: code prepared and merged; inert until assets are uploaded. 2026-07-20.

Goal: stop depending on external hosts for redistributable components -- serve
them from QUILL's own SHA-pinned `assets-v1` release -- to cut complexity and
fragility. The **gated** `pyannote/speaker-diarization-3.1` diarization model
stays on Hugging Face (it requires a token and is isolated in
`quill/core/ai/diarization.py`); everything below is the *public* models only.

The code is written so that **each cut-over is a data change, not a code change**,
and rolls out one component at a time with a safe fallback to the current host.

## ffmpeg (assets-v1 pin)

`quill/core/speech/ffmpeg_install.py` -> `ffmpeg_download_source()` returns the
moving Gyan.dev upstream URL (unpinned) today, and the pinned `assets-v1` mirror
the moment three constants are filled:

1. Download the exact Gyan "essentials" zip to pin.
2. Upload it to the `assets-v1` release; note the asset filename.
3. Set `FFMPEG_PINNED_FILENAME`, `FFMPEG_PINNED_VERSION`, `FFMPEG_PINNED_SHA256`
   (a real 64-hex digest). A blank/placeholder SHA is ignored.

No fallback needed once pinned: a pinned mirror is a single self-hosted URL, SHA
verified, like the eSpeak/Tesseract installers.

## whisper.cpp + Faster Whisper (the two `huggingface_hub` library call sites)

The only two library uses of `huggingface_hub` are
`whispercpp._download_to_file` (`hf_hub_download`, single GGML file) and
`fasterwhisper._download_repo` (`snapshot_download`, CT2 repo). Both now consult
one shared manifest before touching Hugging Face:

- `quill/core/speech/model_mirrors.py` -- `_MIRRORS: dict[str, MirrorAsset]`
  keyed `"<provider_id>:<model_id>"` (`whispercpp:small`, `fasterwhisper:small`).
  `mirror_for(provider, model)` returns a validly-pinned entry or `None`.
- Each provider: if a mirror is configured, fetch it through the shared,
  SHA-verified download core; on any `ReleaseAssetError` it **falls back to
  Hugging Face**. So a not-yet-uploaded or transiently-failing mirror never
  blocks a download during rollout.

### Activation, per model (no code change)

1. Upload to the `assets-v1` release:
   - whisper.cpp: the single `ggml-<id>.bin` (byte-identical to the HF file --
     its SHA-256 is already the one pinned in `catalog.py`, so you can reuse it).
   - Faster Whisper: a **zip of the CT2 model directory** (the multi-file repo).
2. Add a `MirrorAsset(filename, sha256[, archive_member])` entry to `_MIRRORS`.
   For a Faster Whisper zip set `archive_member` (e.g. `"model.bin"`) so a
   malformed archive is caught.

whisper.cpp SHAs are already known (in `catalog.py`); Faster Whisper zip SHAs
must be computed from the archives you build and upload.

### Final cut-over (once every whisper.cpp + FW model is mirrored and proven)

1. Remove the Hugging Face fallback branch in `_download_to_file` and
   `_download_repo` (and their `huggingface_hub` imports).
2. Demote `huggingface_hub` from a base dependency to the `fasterwhisper` /
   diarization extra in `pyproject.toml` (it is still needed transitively by
   `pyannote` for gated diarization).
3. Update `tests/unit/test_packaging_dependencies.py::`
   `test_huggingface_hub_is_a_base_runtime_dependency` to reflect the demotion.

## Piper voices (follow-up, separate from the library dependency)

Piper voices are already fetched by plain `urllib` from
`huggingface.co/rhasspy/piper-voices/resolve/main/...` (not the `huggingface_hub`
library), in two duplicated `_download_piper_voice` methods
(`quill/ui/main_frame.py`, `quill/apps/studio.py`) with **no SHA pinning**.

To fully sever `huggingface.co`: re-host each voice's `.onnx` + `.onnx.json` (or
a per-voice zip) on `assets-v1`, add per-voice SHAs, consolidate the duplicated
download into one helper, and route it through `model_mirrors.fetch_mirror_file`
/ `fetch_mirror_archive`. Deferred here because it is UI-duplicated code and adds
checksums that do not exist today; the mechanism already supports it.
