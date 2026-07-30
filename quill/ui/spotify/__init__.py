"""wxPython surfaces for Spotify (the hidden Web Playback engine).

Kept apart from the pure ``quill.core.spotify`` package because playback needs a
``wx.html2.WebView`` to host Spotify's Web Playback SDK. The rest of the feature
stays wx-free and strict-typed.
"""

from __future__ import annotations
