# Groq Whisper Transcription

Adds **Groq Whisper** (whisper-large-v3-turbo) as a cloud transcription provider
in QUILL.

Once enabled and given a Groq API key, "Groq Whisper" appears as a provider in
**Tools -> Speech -> Whisperer** wherever you transcribe an audio or video file.
Groq runs Whisper on its own hardware, so transcription is very fast while keeping
Whisper-grade accuracy across 99+ languages.

## Privacy

This is a **cloud** provider. Audio is uploaded to Groq **only** when you
explicitly transcribe a file with this provider and have configured an API key --
never offline, never silently, and never without consent. It is excluded from
QUILL's offline paths (the Watch Folder "Transcribe audio (Whisperer)" action
only uses on-device engines), and it is unavailable in Safe Mode.

This extension is **purely declarative**: it ships no code and makes no network
calls itself. QUILL's host performs the upload using its built-in, egress-audited
transcription path, so the extension never handles your audio bytes or your API
key. (That is why it requests no `net` capability -- least privilege.)

## Requirements

- A Groq API key, stored in QUILL under the "Groq API key" credential label.
- Files up to 25 MB (Groq's limit).

## License

MIT. See `LICENSE`.
