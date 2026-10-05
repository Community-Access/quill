"""The family updater's wx-free core (release-channels plan, section 6.1).

Phase 0 and Phase 1 live here today:

* :mod:`.channels` -- Stable, Beta and Dev, what each means, and the family's
  ``channels.json`` (which channel every app on this computer is on).
* :mod:`.profiles` -- one :class:`~.profiles.UpdaterProfile` per app, the seam a
  new app joins through.
* :mod:`.runtime_rule` -- the interim rule for apps that share the QuillVille
  Runtime (plan 6.5): Beta only when alone on the runtime, or all together.
* :mod:`.snapshots` -- the copy of an app's settings saved when it joins Beta.
* :mod:`.switch` -- moving an app between channels, step by step, with every
  side effect injected so the whole flow is testable without wx.
* :mod:`.policy` -- which release an update check may offer on each channel.
* :mod:`.history` -- the read-only Update History log.

Phase 2, the signed v2 feed:

* :mod:`.feed` -- the per-app release list, its signature and rollback rule.
* :mod:`.feed_fetch` -- fetching it (sequence high-water mark, expiry, cache).
* :mod:`.feed_publish` -- listing, promoting and withdrawing builds (the scripts).
* :mod:`.download` -- resumable downloads checked against the signed SHA-256.
* :mod:`.background` -- when Beta and Dev may download in the background.

Phase 3, :mod:`.runtime_slots` -- each channel's own shared-runtime folder.

Phase 4, going back safely:

* :mod:`.going_back` -- "back to Stable only if safe", decided from the ledger.
* :mod:`.apply` and :mod:`.apply_script` -- the update helper's health check,
  the kept installer and the portable ``.previous`` swap that undo an update
  that did not start.

The only network calls are ``feed_fetch.http_get`` and the download opener.
"""
