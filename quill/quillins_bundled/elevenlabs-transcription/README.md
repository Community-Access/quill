# ElevenLabs Scribe Transcription

Adds **ElevenLabs Scribe** (scribe_v1) as a cloud transcription provider in QUILL,
with optional **speaker diarization**.

Once enabled and given an ElevenLabs API key, "ElevenLabs Scribe" appears as a
provider in **Tools -> Speech -> Whisperer** wherever you transcribe an audio or
video file. When you request diarization, Scribe marks who spoke each segment.

## Privacy

This is a **cloud** provider. Audio is uploaded to ElevenLabs **only** when you
explicitly transcribe a file with this provider and have configured an API key --
never offline, never silently, and never without consent. It is excluded from
QUILL's offline paths (the Watch Folder "Transcribe audio (Whisperer)" action
only uses on-device engines), and it is unavailable in Safe Mode.

This extension is **purely declarative**: it ships no code and makes no network
calls itself. QUILL's host performs the upload using its built-in, egress-audited
transcription path, so the extension never handles your audio bytes or your API
key. (That is why it requests no `net` capability -- least privilege.)

## Requirements

- An ElevenLabs API key, stored in QUILL under the "ElevenLabs API key" credential label.
- Files up to 100 MB.

## License

MIT. See `LICENSE`.
