"""QUILL offline speech-to-text platform (#617).

A provider-neutral, offline-first speech layer: a typed provider protocol and
data model (:mod:`provider`), output formatters for TXT/SRT/VTT/JSON
(:mod:`formatters`), an installed-model store (:mod:`models`), a lazy provider
registry (:mod:`registry`), and the curated model catalog (:mod:`catalog`).

Everything here is pure and wx-free so it can run on a worker thread. Heavy
engines (whisper.cpp, Faster Whisper) are optional providers imported only when
activated; none is imported at QUILL startup.
"""
