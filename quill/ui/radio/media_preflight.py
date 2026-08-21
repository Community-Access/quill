"""Ask what the media tools are before the listener finds out the hard way.

The pure model is :mod:`quill.core.radio.media_health`; this is the half that
knows where the tools live and who to tell.

**Why the probe is here rather than in core.** ``mpv_output_device_available()``
is the exact predicate ``engine_selection.select`` uses to decide whether to
build the mpv engine at all. A health report that asked a *different* question
-- ``optional_components._libmpv_installed()``, say, which does not look at the
``QUILL_LIBMPV`` override or beside the executable -- would eventually describe
a machine nobody has, and be believed. So the resolution sits in the UI layer
beside the code it describes, and core keeps only the meaning.

**Why the notice is spoken and not modal.** Two reasons. A modal at launch
fights a screen reader for the focus a launching app has not settled yet
(#259), and this is a courtesy rather than a decision the listener has to make
before continuing. It follows exactly the shape of
``data_folder_dialog.surface_data_folder_startup``: deferred through
``wx.CallAfter``, announced once, and incapable of raising -- a courtesy that
breaks a launch is not a courtesy.

**Why it is remembered by signature and not by a flag.** ``MediaHealth``
answers with a key naming which tools are missing, so a machine that later
loses a *second* tool is told again, and a machine told once about the same
state is not told on every launch forever.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.core.radio.media_health import MediaHealth, stream_needs_mpv

_log = logging.getLogger(__name__)


def current_health() -> MediaHealth:
    """What this machine actually has, asked the way the player asks it."""
    ffmpeg = False
    mpv = False
    try:
        from quill.core.speech.ffmpeg import ffmpeg_available

        ffmpeg = bool(ffmpeg_available())
    except Exception:  # noqa: BLE001 - a probe must never be the thing that fails
        _log.exception("ffmpeg probe failed; reporting it missing")
    try:
        from quill.ui.radio.mpv_radio_engine import mpv_output_device_available

        mpv = bool(mpv_output_device_available())
    except Exception:  # noqa: BLE001
        _log.exception("libmpv probe failed; reporting it missing")
    return MediaHealth(ffmpeg=ffmpeg, mpv=mpv)


def _is_lite_install() -> bool:
    """True on the thin installer, whose runtime download carries no media tools.

    Resolution belongs on this side of the line for the same reason the probes
    do: :mod:`quill.core.radio.media_health` is pure and takes booleans, and the
    repair advice is only true if it matches the edition the listener actually
    has. A failure to tell answers False -- the full-installer advice is the
    right guess for the common case, and a probe must never be the thing that
    breaks a courtesy.
    """
    try:
        from quill.core import install_edition

        return install_edition.detect() == install_edition.INSTALLER_LITE
    except Exception:  # noqa: BLE001 - never let edition detection break a notice
        _log.exception("install edition probe failed; assuming the full installer")
        return False


def surface_media_health_startup(host: Any) -> None:
    """Say once, at launch, what this installation cannot do and why.

    Called deferred (``wx.CallAfter``) once *host* can announce. Never raises.

    A healthy installation says nothing at all. That is not politeness, it is
    the rule the rest of this app follows: a launch that reports "all is well"
    every time is a launch nobody can listen past.
    """
    try:
        health = current_health()
        if health.healthy:
            # Healthy again after a repair: forget the old signature so a later
            # loss is news rather than a repeat.
            _remember(host, "")
            return
        signature = health.signature()
        if _remembered(host) == signature:
            return
        _remember(host, signature)
        host._announce(health.notice(lite=_is_lite_install()))
    except Exception:  # noqa: BLE001 - a courtesy must not break a launch
        _log.exception("media health surfacing failed")


def refusal_for(station_name: str, url: str) -> str:
    """Why *this* station will not play, when the missing engine is the reason.

    Returns "" when the missing engine is not the reason, so the caller keeps
    its ordinary error. That direction matters: telling somebody to reinstall
    because an MP3 station happened to be off the air sends them to repair a
    machine that is fine.
    """
    if not stream_needs_mpv(url):
        return ""
    health = current_health()
    if health.mpv:
        return ""
    return health.format_refusal(station_name, lite=_is_lite_install())


# -- where the "already said" mark lives ---------------------------------------


def _remembered(host: Any) -> str:
    return str(getattr(getattr(host, "_radio_history", None), "media_notice_signature", ""))


def _remember(host: Any, signature: str) -> None:
    """Record *signature* on the radio history and persist it.

    Through the host's own saver rather than a direct write: the history file is
    the one the rest of the app is also holding, and two writers is how a
    favorite disappears.
    """
    history = getattr(host, "_radio_history", None)
    if history is None or getattr(history, "media_notice_signature", None) == signature:
        return
    history.media_notice_signature = signature
    saver = getattr(host, "_save_radio_history", None)
    if callable(saver):
        saver()
