"""Security and privacy services for QUILL Social (PRD 31).

Two wx-free building blocks:

- ``credentials``: a credential store that keeps only *references* in the local
  database -- never raw tokens -- and resolves the real secret through the OS
  credential manager at the boundary (PRD 31.1). Includes a redaction helper for
  logs and diagnostics.
- ``diagnostics``: assembles a diagnostic bundle that excludes credentials and
  private content by default, lists what it contains, and offers redaction
  (PRD 31.4).

The invariant these modules exist to protect: the database and any exported
artifact hold references and redacted text only. Real secrets live in the OS
credential store and are never persisted by QUILL.
"""

from __future__ import annotations
