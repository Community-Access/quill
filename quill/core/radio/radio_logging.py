"""Debug-mode control for the radio logger subtree (observable radio, #5).

Quill Radio's diagnostics should be reconstructable from ``quill.log`` alone:
when a supporter turns on debug mode, the radio code logs what it did and why a
recording or stream lookup failed, without a live repro. This module owns the
one knob that turns that verbosity on and off.

The radio code logs under the ``quill.core.radio`` and ``quill.ui.radio``
namespaces (``logging.getLogger(__name__)`` in each module). Debug mode raises
just those subtrees to ``DEBUG`` -- never the root logger -- so it composes
cleanly when Quill Radio is embedded in full QUILL: the rest of the app keeps
its normal INFO level while the radio subtree gets chatty. The already-installed
rotating-file handler (see :mod:`quill.stability.logging_config`) writes the
extra records; nothing else is reconfigured.

wx-free, strict-typed. Default is off (the loggers inherit the root's INFO).
"""

from __future__ import annotations

import logging

#: The logger namespaces the radio feature logs under. Raising these to DEBUG
#: turns on verbose radio logging without touching any other subsystem.
RADIO_LOGGER_NAMES = ("quill.core.radio", "quill.ui.radio")


def set_radio_debug(enabled: bool) -> None:
    """Turn verbose radio logging on (``DEBUG``) or off (inherit root's INFO).

    Idempotent. Off restores ``NOTSET`` so the radio loggers fall back to the
    root level rather than being pinned at INFO, keeping behaviour identical to
    before the toggle ever existed.
    """
    level = logging.DEBUG if enabled else logging.NOTSET
    for name in RADIO_LOGGER_NAMES:
        logging.getLogger(name).setLevel(level)


def radio_debug_enabled() -> bool:
    """True when the radio subtree is currently pinned to ``DEBUG`` (#5)."""
    return all(logging.getLogger(name).level == logging.DEBUG for name in RADIO_LOGGER_NAMES)
