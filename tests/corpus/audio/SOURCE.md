# Chaptered audio sample

`chaptered-sample.mp3` is a real 4:14 MP3 for exercising the Audio Studio
against genuine audio: President Reagan's Challenger address (a public-domain
United States government recording), carried over from the ChapterForge
project's sample set when its features were consolidated into QUILL.

The chapter markers and tags on it were written by QUILL's own writers
(`quill.core.speech.chapters.write_mp3_chapters` +
`quill.core.speech.book_file.save_mp3_book`), so the file doubles as a
known-good artifact of those code paths:

- 3 chapters (Opening / Address / Closing) as ID3v2.3 CHAP frames with an
  ordered CTOC,
- book tags (title, artist, album, album artist, genre, year).

`cover.jpg` is a small companion cover image for cover-discovery and
attached-picture tests.

Intended for tests that want real decodable audio (player, ffmpeg probes,
round trips); tests that only need tag surgery should keep using the tiny
synthetic silent-frame fixtures instead of this 1.7 MB file.
