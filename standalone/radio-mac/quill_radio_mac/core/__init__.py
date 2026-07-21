"""wx-free core logic for Quill Radio for Mac.

Everything under ``quill_radio_mac.core`` is importable without wxPython
and without a display: data models, path resolution, atomic JSON
persistence, log redaction, the background task manager, and (in later
modules) the network clients, recorder, and schedulers.

Threading contract: modules here may create worker threads of their own
(the task manager's pool, the recorder), but none of them ever touch a
widget. Results are marshalled back to the UI thread via
``quill_radio_mac.core.tasks`` (wx.CallAfter when wx is present, direct
call otherwise), which is what keeps the core testable headless on any
platform.

macOS notes: nothing in this package is macOS-specific except path
defaults (see :mod:`quill_radio_mac.core.paths`); the same code runs the
test suite on Windows.
"""
