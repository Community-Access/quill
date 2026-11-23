"""The Scribe for Documents live regression run (docs/qa/scribe-live-regression.md).

After Jeff signs in to Scribe in QUILL, ``python -m quill.tools.scribe_live_run``
converts test documents through the real service, saves every output outside
the repository in the corpus layout the replay tests read, deletes the test
documents from the account, replays the outputs through every app's Scribe
entry point and compares them with the previous run.

It tests QUILL, not Scribe: that QUILL asks correctly, collects everything
that comes back, can use it, and copes with whatever shape it arrives in.
The comparison flags changes in what comes back that could break collecting
or using a file, never the quality of the conversion.

* :mod:`.sources` -- the test documents: ours (made by
  ``tests/corpus/scribe_live/build_scribe_live_sources.py``) and Pneuma's four.
* :mod:`.plan` -- the profiles, every conversion, and the credit they use.
* :mod:`.facts` -- what each returned file is, and whether QUILL can open it.
* :mod:`.execute` -- the uploads, through QUILL's own queue runner and client.
* :mod:`.layout` -- the run folder: corpus layout, ``validation.json``,
  ``README.md`` and ``run.json``.
* :mod:`.compare` -- this run against the previous one (or Pneuma's corpus).

Every call to Scribe goes through :class:`quill.core.scribe.client.ScribeClient`
and :class:`quill.core.scribe.channel.DocumentChannel`, the reviewed egress
sites (GATE-9); nothing here opens a connection of its own, and nothing here
reads, prints or stores a token.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError


class LiveRunError(CodedError):
    """The live run stopped before or between uploads; the message says why."""

    code = "QUILL-TOOLS-SCRIBELIVE-STOPPED"


__all__ = ["LiveRunError"]
