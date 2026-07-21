# Speech runtime + model coverage (Windows / macOS), post self-hosting

Status: verification as of 2026-07-20, after mirroring models + ffmpeg to
`assets-v1`. Answers "are the *runtimes* handled as well as the models, on
Windows and Mac?" Records two engine gaps for follow-up.

## Models — all off Hugging Face now (except two noted cases)

| Model set | Hosted on assets-v1 | Cross-platform |
|---|---|---|
| whisper.cpp GGML | tiny, base, small, small.en-tdrz, medium | yes (`.bin` files) |
| Faster Whisper CT2 | tiny, base, small, medium, distil-large-v3 (zipped) | yes |
| Piper voices | all 39 catalog voices (per-voice zip) | yes |
| Kokoro | `kokoro-models.zip` (already hosted) | yes |
| Vosk | `vosk-*.whl` (already hosted) | yes |

Not mirrored, by design: whisper/FW **large-v3** (~3 GB, exceeds GitHub's
2 GiB/file release-asset limit -> manual-obtain / HF fallback), and the **gated
`pyannote` diarization** model (kept on Hugging Face, token-required, isolated).

## Runtimes (engines) — Windows vs macOS

| Runtime | Windows | macOS | Off Hugging Face? |
|---|---|---|---|
| **whisper.cpp** engine | assets-v1 `whisper-bin-x64.zip` (pinned) ✓ | **GAP** — upstream ships no standalone mac CLI (only an xcframework for app embedding); can't build from Windows | yes (never HF) |
| **Piper** engine | assets-v1 `piper` asset (pinned) ✓ | **GAP** — mac binaries *exist* upstream (`piper_macos_x64`/`aarch64`) but `piper_install_supported()` is win32-only, so they aren't offered | yes |
| **Kokoro** ONNX runtime | pip wheel (`onnxruntime` + `kokoro-onnx`) ✓ | ✓ pip wheels (macOS) | PyPI (never HF); models hosted |
| **Faster Whisper** runtime | pip wheel (`ctranslate2`) ✓ | ✓ pip wheels | PyPI; models mirrored |
| **Vosk** runtime | pip wheel / assets-v1 wheel ✓ | ✓ pip wheel | PyPI/assets-v1 |
| **DECtalk** | assets-v1 (pinned) ✓ | N/A — DECtalk is a Windows-native synth (no mac build exists) | yes |

Key point: the pip-installed engines (**Kokoro, Faster Whisper, Vosk**) are
already cross-platform — their wheels include macOS builds — so on macOS QUILL
has a complete offline TTS (Kokoro) + STT (Faster Whisper / Vosk) stack with
**no separate binary and no Hugging Face**. macOS offline speech does not depend
on the two engine gaps below.

## The two engine gaps

### 1. Piper engine on macOS — fixable, not yet done
Upstream `rhasspy/piper` `2023.11.14-2` publishes `piper_macos_x64.tar.gz` and
`piper_macos_aarch64.tar.gz`. To close this:
- Upload both tarballs to `assets-v1`, pin their SHA-256.
- Make `piper_install` platform-aware: `piper_install_supported()` returns true
  on darwin too; select the Windows zip vs the mac tarball by platform + arch;
  extract `.tar.gz` on mac (the current extractor is zip-only); and confirm the
  discover/resolve path finds `piper` in the managed mac dir.
Deferred here because it is platform-specific engine + extraction + resolver code
that cannot be exercised from this Windows environment; needs a mac to validate.

### 2. whisper.cpp engine on macOS — needs a build, not hostable as-is
Upstream ships **no** standalone macOS `whisper-cli` binary (the release's
`whisper-v1.9.1-xcframework.zip` is a library for embedding in an Xcode app, not
a runnable CLI). Options, all requiring a mac/CI build:
- Compile `whisper-cli` for macOS (arm64 + x64) in CI, host on `assets-v1`, add a
  platform-aware `whispercpp` asset + resolver entry; or
- Bundle a mac `whisper-cli` in the mac app at build time.
Until then, **Faster Whisper is the recommended offline STT engine on macOS**
(pip wheels + the mirrored CT2 models — fully working today, no binary, no HF).

## Recommendation

- macOS is already fully served for offline speech via Kokoro + Faster Whisper +
  Vosk (pip) and the mirrored models — nothing HF-bound.
- Close the Piper-mac gap by hosting the upstream mac tarballs + platform-aware
  install (a bounded change, best validated on a mac).
- Treat whisper.cpp-on-mac as a build task (CI-compiled `whisper-cli`), or accept
  Faster Whisper as the mac default and leave whisper.cpp Windows-only.
