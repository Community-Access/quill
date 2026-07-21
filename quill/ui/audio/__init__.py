"""Shared audio playback layer for the QuillVille family.

The ``AudioEngine`` protocol, the default ``WxMediaEngine`` (wx.media / WMP)
backend, ``create_engine``, and the optional libmpv backend (``mpv_engine``)
live here and are used by every app that plays media: Radio, Cast, Audio
Studio, and Beacon. Kept in a neutral ``quill.ui.audio`` package (not under any
one app) so no app owns the shared engine.
"""
