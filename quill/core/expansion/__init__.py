"""System-wide abbreviation expansion -- the engine behind Quill Inkwell.

QUILL's editor expands abbreviations against the document text it already owns
(``quill.core.abbreviations.try_expand``). Expanding *anywhere else* -- a
browser, a mail client, a form -- means there is no document to read, so the
typed characters have to be remembered as they arrive and matched against the
same library. That is all this package does:

- :mod:`ring_buffer` -- the bounded, privacy-conscious memory of recent keys.
- :mod:`matcher` -- the same library, matched against that buffer.
- :mod:`targets` -- where expansion must never fire (password fields and the
  like), decided from the foreground window alone.

Everything here is pure and wx-free; the Windows keyboard hook and text
injection that drive it live in :mod:`quill.platform.windows`.
"""

from __future__ import annotations

from quill.core.expansion.matcher import GlobalMatch, match_buffer
from quill.core.expansion.ring_buffer import RingBuffer
from quill.core.expansion.targets import is_denied_target

__all__ = ["GlobalMatch", "RingBuffer", "is_denied_target", "match_buffer"]
