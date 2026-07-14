# OpenAI Whisper Transcription

Adds **OpenAI Whisper** as a cloud transcription provider in QUILL.

Once enabled and given an OpenAI API key, "OpenAI Whisper" appears as a provider
in **Tools → Speech → Whisperer** wherever you transcribe an audio or video file.
It is best-in-class for accuracy across 99+ languages.

## Privacy

This is a **cloud** provider. Audio is uploaded to OpenAI **only** when you
explicitly transcribe a file with this provider and have configured an API key —
never offline, never silently, and never without consent. It is excluded from
QUILL's offline paths (the Watch Folder "Transcribe audio (Whisperer)" action
only uses on-device engines), and it is unavailable in Safe Mode.

This extension is **purely declarative**: it ships no code and makes no network
calls itself. QUILL's host performs the upload using its built-in, egress-audited
transcription path, so the extension never handles your audio bytes or your API
key. (That is why it requests no `net` capability — least privilege.)

## Requirements

- An OpenAI API key, configured in QUILL's AI Hub.
- Files up to 25 MB (OpenAI's limit).

## License

MIT. See `LICENSE`.
