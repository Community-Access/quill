"""The release-channel windows every app shares (release-channels plan 6.1, 7).

* :mod:`.release_channel_dialog` -- Help > Release Channel...: choose Stable,
  Beta or Dev, optionally moving your other QuillVille apps too.
* :mod:`.channel_risk_dialog` -- the plain-words warning before Beta or Dev.
* :mod:`.update_history_dialog` -- the read-only Update History.
* :mod:`.flow` -- the one entry point each app calls, which runs the windows
  above through :mod:`quill.core.updater.switch`.

The decisions live in :mod:`quill.core.updater`; these modules only ask.
"""
