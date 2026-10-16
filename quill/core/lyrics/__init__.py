"""Song lyrics, shared by every QUILL app that plays music.

Quill Radio shows the plain words of the song on the air; Quill Media Player
shows the timed words of the file it is playing. One client serves both
(:mod:`quill.core.lyrics.lrclib`), because a capability two apps need lives in
the shared package in the same change that creates it -- ``musicbrainz.py``
sitting under ``core/radio`` is why Audio Studio grew a second MusicBrainz
client, and this package exists so lyrics never do that.
"""
