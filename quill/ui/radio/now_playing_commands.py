"""What's Playing: copy it, or open it for review (#1134, fixed in #1282).

Reported by a listener: with a station playing, **Copy What's Playing** and
**What's Playing - Review and Copy...** "do nothing except return to the main
window", while with nothing playing they speak a sensible message. Three
defects behind that, all of them here now:

* **A missing title was treated as "nothing is playing."** Both commands read a
  *cached* track title and gave up when it was empty -- which is the normal
  state for the first few seconds of a station, for a stream whose ICY tap is
  refused, and for every station when track announcements are off. The review
  window never opened at all in that case; it fell back to the speak-only
  command.
* **That fallback is asynchronous.** It starts a background fetch and returns,
  so the palette closes and nothing else happens on screen -- and if the fetch
  failed, its ``on_failure`` swallowed the error, so nothing was ever spoken
  either. Silence, exactly as reported. With nothing playing the same code
  answers immediately ("Nothing is playing."), which is why the bug looked
  inverted -- it "worked" only when stopped.
* **The Copy result was reported from a value that isn't always a bool.**
  ``MainFrame._copy_to_clipboard`` returns True/False; the standalone apps'
  shell returned None, so in Quill Radio a successful copy announced "Could not
  copy to the clipboard." (The shell now returns a bool; this module no longer
  depends on which host it is talking to.)

The fix in one sentence: if a station is playing, these commands always finish
the job -- fetching the title first when it isn't known yet -- and always say
what happened.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: Spoken while a title fetch is in flight, so a command never looks dead.
CHECKING_MESSAGE = "Checking what's playing..."

#: Spoken/shown when the station simply does not broadcast track titles.
NO_TITLE_MESSAGE = "This stream doesn't share track titles."

#: Spoken when nothing is on air at all.
NOTHING_PLAYING_MESSAGE = "Nothing is playing."


def resolve_now_playing_text(host: Any, then: Callable[[str], None]) -> None:
    """Hand *then* the current now-playing text, fetching it first if needed.

    ``then`` is always called exactly once, on the UI thread, with the text or
    with "" when the station has no title to give. Nothing is playing is
    reported here rather than handed on, because every caller says the same
    thing about it.
    """
    text = host._radio_now_playing_text()
    if text:
        then(text)
        return
    controller = getattr(host, "_radio_controller", None)
    station = controller.state.station if controller is not None else None
    if station is None:
        host._announce(NOTHING_PLAYING_MESSAGE)
        return
    host._announce(CHECKING_MESSAGE)
    host._radio_fetch_track_title(on_resolved=lambda: then(host._radio_now_playing_text()))


def copy_whats_playing(host: Any) -> None:
    """Copy the current now-playing text, fetching the title first if needed."""

    def _copy(text: str) -> None:
        if not text:
            host._announce(NO_TITLE_MESSAGE)
            return
        if host._copy_to_clipboard(text):
            host._announce(f"Copied: {text}.")
        else:
            host._announce("Could not copy to the clipboard.")

    resolve_now_playing_text(host, _copy)


def show_whats_playing_details(host: Any) -> None:
    """Open the reviewable, copyable What's Playing window.

    With a station playing the window always opens -- with the track when there
    is one, and with the station's name plus a plain "no track titles" line when
    there is not. A listener who asked to *review* what is playing should get a
    window they can arrow through, not a one-shot announcement.
    """

    def _show(text: str) -> None:
        from quill.ui.radio.now_playing_dialog import NowPlayingDialog

        controller = getattr(host, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if not text:
            if station is None:
                host._announce(NOTHING_PLAYING_MESSAGE)
                return
            text = f"{station.display_name}\n\n{NO_TITLE_MESSAGE}"
        title = f"Now Playing: {station.display_name}" if station is not None else "Now Playing"
        NowPlayingDialog(
            host.frame,
            text,
            host._show_modal_dialog,
            host._copy_to_clipboard,
            host._announce,
            title=title,
            transport_host=host,
            windows=getattr(host, "_windows", None),
        ).show()

    resolve_now_playing_text(host, _show)
