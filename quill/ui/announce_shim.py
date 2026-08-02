"""Turn a legacy ``_announce`` call into an :class:`Announcement` (#1298-#1300).

Every shell has hundreds of ``self._announce("Saved")`` call sites and a single
``force`` boolean. Rewriting them all would be a large, risky diff for no user
benefit, so the boolean is translated here instead: ``force=True`` means the
user explicitly asked and the confirmation must be heard, which is a WARNING in
severity terms -- it interrupts, but it is not the never-suppressible ERROR that
should be reserved for something actually going wrong.

Call sites that want the richer model can build an :class:`Announcement`
directly and hand it to the service; this shim exists so they do not have to.
"""

from __future__ import annotations

from quill.core.announce import Announcement, Severity


def build_announcement(
    message: str,
    *,
    force: bool = False,
    sound_event: str = "",
    severity: Severity | None = None,
) -> Announcement:
    """The announcement a legacy ``_announce(message, force=...)`` call means."""
    if severity is None:
        severity = Severity.WARNING if force else Severity.ROUTINE
    return Announcement(text=message, severity=severity, sound_event=sound_event)
