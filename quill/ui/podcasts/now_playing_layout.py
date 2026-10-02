"""Now Playing's controls, built in the order a screen reader meets them.

Split from :mod:`quill.ui.podcasts.now_playing_window` under GATE-11: that
module is what the window *does*; this is what it is made of. Every label is
created immediately before the control it names (wxMSW's accessible name), every
control carries its help inline (GATE-CAST-HELP), and no two controls share an
access key with each other or with the window's own menu bar (Now &Playing,
&Window): the letters used are U S B F V X D M E I 5 C O N L R Y A K H T.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.notes_reader import NotesReader

__all__ = ["SPEEDS", "TITLE", "build_controls"]

TITLE = "Now Playing"
#: The nine speeds the chooser offers; Custom... takes any other.
SPEEDS: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)


def _button(panel: Any, label: str, help_text: str) -> Any:
    button = wx.Button(panel, label=label)
    button.SetHelpText(help_text)
    return button


def build_controls(self: Any, host: Any) -> None:
    """Create every widget on *self*, the :class:`NowPlayingWindow`."""
    self.frame = wx.Frame(host.frame, title=TITLE, size=(760, 720))
    panel = wx.Panel(self.frame)
    self.panel = panel
    root = wx.BoxSizer(wx.VERTICAL)

    self._podcast = wx.StaticText(panel, label="Nothing is playing.")
    self._episode = wx.StaticText(panel, label="")
    self._source = wx.StaticText(panel, label="")
    for line in (self._podcast, self._episode, self._source):
        root.Add(line, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    # -- position -------------------------------------------------------
    row = wx.BoxSizer(wx.HORIZONTAL)
    wx.StaticText(panel, label="Position:")  # the slider's name: created just before it
    caption = panel.GetChildren()[-1]
    self._slider = wx.Slider(panel, value=0, minValue=0, maxValue=1000)
    self._slider.SetHelpText(
        "Where you are in the episode. Left and Right move five seconds, Page Up "
        "and Page Down thirty, Home and End to the ends. The time beside it says "
        "minutes and seconds of the whole."
    )
    self._time = wx.StaticText(panel, label="0:00 of 0:00")
    row.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    row.Add(self._slider, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    row.Add(self._time, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(row, 0, wx.EXPAND | wx.ALL, 8)

    # -- transport ------------------------------------------------------
    transport = wx.BoxSizer(wx.HORIZONTAL)
    self._play = _button(panel, "Pa&use", "Pauses, or resumes, the episode.")
    self._stop = _button(panel, "&Stop", "Stops the episode and remembers your place.")
    self._back = _button(panel, "&Back 30 Seconds", "Moves back thirty seconds.")
    self._forward = _button(panel, "&Forward 30 Seconds", "Moves forward thirty seconds.")
    self._prev_chapter = _button(
        panel, "Pre&vious Chapter", "Jumps to the start of the previous chapter."
    )
    self._next_chapter = _button(panel, "Ne&xt Chapter", "Jumps to the start of the next chapter.")
    for button in (
        self._play,
        self._stop,
        self._back,
        self._forward,
        self._prev_chapter,
        self._next_chapter,
    ):
        transport.Add(button, 0, wx.RIGHT, 6)
    root.Add(transport, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- speed, volume, mute ----------------------------------------------
    levels = wx.BoxSizer(wx.HORIZONTAL)
    wx.StaticText(panel, label="Spee&d:")
    speed_caption = panel.GetChildren()[-1]
    self._speeds: list[float] = list(SPEEDS)
    self._speed = wx.Choice(
        panel, choices=[*(f"{value:g}x" for value in self._speeds), "Custom..."]
    )
    self._speed.SetHelpText(
        "Playback speed, for this show or for every podcast, as the Speed keys "
        "choose it. The status bar and the keys change the same setting."
    )
    wx.StaticText(panel, label="Volume:")
    volume_caption = panel.GetChildren()[-1]
    self._volume = wx.Slider(panel, value=100, minValue=0, maxValue=100)
    self._volume.SetHelpText("Playback volume, from silent to full. Arrow keys change it.")
    self._mute = _button(
        panel, "&Mute", "Silences playback without stopping it; press again to unmute."
    )
    levels.Add(speed_caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    levels.Add(self._speed, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
    levels.Add(volume_caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    levels.Add(self._volume, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    levels.Add(self._mute, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(levels, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- sleep timer ----------------------------------------------------------
    sleep = wx.BoxSizer(wx.HORIZONTAL)
    self._sleep = wx.StaticText(panel, label="Sleep timer: off")
    self._sleep_set = _button(panel, "S&et...", "Type a number of minutes for the sleep timer.")
    self._sleep_end = _button(panel, "At End of Ep&isode", "Stops playback when this episode ends.")
    self._sleep_extend = _button(
        panel, "Extend by &5 Minutes", "Pushes a running sleep timer back five minutes."
    )
    sleep.Add(self._sleep, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
    for button in (self._sleep_set, self._sleep_end, self._sleep_extend):
        sleep.Add(button, 0, wx.RIGHT, 6)
    root.Add(sleep, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- chapters -------------------------------------------------------------
    self._chapters_caption = wx.StaticText(panel, label="&Chapters:")
    self._chapters = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    for index, (name, width) in enumerate((
        ("#", 48),
        ("Title", 360),
        ("Start", 90),
        ("Status", 90),
    )):
        self._chapters.InsertColumn(index, name, width=width)
    self._chapters.SetMinSize((-1, 120))
    self._chapters.SetHelpText(
        "This episode's chapters. Enter jumps to the selected one; the playing "
        "chapter says so in its Status column and the list follows playback "
        "without moving your cursor."
    )
    root.Add(self._chapters_caption, 0, wx.LEFT | wx.RIGHT, 8)
    root.Add(self._chapters, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- show notes -------------------------------------------------------
    history = getattr(host, "_podcast_history", None)
    self.notes = NotesReader(
        panel,
        root,
        announce=host._announce,
        on_seek=self._seek_from_notes,
        show_modal=getattr(host, "_show_modal_dialog", None),
        copy_format=lambda: str(getattr(history, "notes_copy_format", "plain") or "plain"),
        set_copy_format=self._remember_copy_format,
        min_height=140,
    )

    # -- your note --------------------------------------------------------
    self._note_caption = wx.StaticText(panel, label="&Your note:")
    self._note = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
    self._note.SetMinSize((-1, 60))
    self._note.SetHelpText(
        "A note of your own about this episode, kept with your episode notes. "
        "Saved when you leave the field; empty removes it."
    )
    root.Add(self._note_caption, 0, wx.LEFT | wx.RIGHT, 8)
    root.Add(self._note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- the bottom row ------------------------------------------------------
    bottom = wx.BoxSizer(wx.HORIZONTAL)
    self._favorite = _button(
        panel, "Add to F&avorites", "Adds this podcast to Favorites, or removes it."
    )
    self._played = _button(
        panel,
        "Mar&k as Played",
        "Marks this episode finished and moves to the next in the queue.",
    )
    self._share = _button(
        panel, "S&hare...", "Copies a sentence and a link to this moment in the episode."
    )
    self._about = _button(
        panel,
        "Abou&t This Episode...",
        "Everything the feed says about this episode, as a reviewable report.",
    )
    for button in (self._favorite, self._played, self._share, self._about):
        bottom.Add(button, 0, wx.RIGHT, 6)
    root.Add(bottom, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    panel.SetSizer(root)
