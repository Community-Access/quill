"""Tell the listener FFmpeg is missing, before a feature silently does nothing.

The pure model is :mod:`quill.core.podcasts.media_health`; this is the half
that knows where the tool lives and who to tell.

**Why the probe is here.** It asks ``ffmpeg_available()`` -- the same predicate
``audio_processing`` and the chapter analysers call before they do anything --
so the report and the features agree by construction. A health check that
asked a different question would eventually describe a machine nobody has, and
be believed.

**Why it is spoken and not modal.** A modal at launch fights a screen reader
for focus the app has not settled yet (#259), and this is a courtesy rather
than a decision anybody has to make before continuing. Same shape as Quill
Radio's ``media_preflight`` and ``data_folder_dialog``: deferred through
``wx.CallAfter``, said once, and incapable of raising -- a courtesy that
breaks a launch is not a courtesy.

**Why it is remembered by signature rather than by a flag.** So a machine
repaired and later broken again is told again, and a machine in the same state
is not told every launch forever.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.core.podcasts.media_health import CastMediaHealth

_log = logging.getLogger(__name__)

__all__ = ["current_health", "surface_media_health_startup", "readout"]


def current_health() -> CastMediaHealth:
    """What this machine actually has, asked the way the features ask it."""
    ffmpeg = False
    try:
        from quill.core.speech.ffmpeg import ffmpeg_available

        ffmpeg = bool(ffmpeg_available())
    except Exception:  # noqa: BLE001 - a probe must never be the thing that fails
        _log.exception("ffmpeg probe failed; reporting it missing")
    return CastMediaHealth(ffmpeg=ffmpeg)


def _is_lite_install() -> bool:
    """True on the thin installer, whose runtime carries no media tools.

    Resolution belongs on this side of the line because the repair advice is
    only true if it matches the edition the listener has. A failed probe
    answers False: the full-installer advice is right for the common case, and
    a probe must never be the thing that breaks a courtesy.
    """
    try:
        from quill.core import install_edition

        return install_edition.detect() == install_edition.INSTALLER_LITE
    except Exception:  # noqa: BLE001 - never let edition detection break a notice
        _log.exception("install edition probe failed; assuming the full installer")
        return False


def readout() -> str:
    """The answer to Help > Media Tools. Never empty -- somebody asked."""
    return current_health().readout(lite=_is_lite_install())


def surface_media_health_startup(host: Any) -> None:
    """Say once, at launch, what this installation cannot do. Never raises.

    A healthy installation says nothing at all, and forgets any previous
    notice so that a later loss is news rather than a repeat.
    """
    try:
        health = current_health()
        if health.healthy:
            _remember(host, "")
            return
        signature = health.signature()
        if _remembered(host) == signature:
            return
        _remember(host, signature)
        host._announce(health.notice(lite=_is_lite_install()))
    except Exception:  # noqa: BLE001 - a courtesy must not break a launch
        _log.exception("media health surfacing failed")


# -- where the "already said" mark lives ---------------------------------------


def _remembered(host: Any) -> str:
    return str(getattr(getattr(host, "_podcast_history", None), "media_notice_signature", ""))


def _remember(host: Any, signature: str) -> None:
    """Record *signature* on the podcast history and persist it.

    Through the host's own saver rather than a direct write: the history file
    is one the rest of the app is also holding, and two writers is how a
    setting disappears.
    """
    history = getattr(host, "_podcast_history", None)
    if history is None or getattr(history, "media_notice_signature", None) == signature:
        return
    history.media_notice_signature = signature
    saver = getattr(host, "_save_podcast_history", None)
    if callable(saver):
        saver()
