"""The Playback-menu items that only make sense for something with a timeline.

Extracted from ``quill/apps/radio.py`` under GATE-11 (extract, never rebaseline)
when the Transcript command arrived. It is a coherent group rather than an
arbitrary slice: every item here is a thing you can do to a **finished** video
and cannot do to a live broadcast -- move along its length, step through its
chapters, change its speed, ask where you are, read what it says.

None of them is hidden or greyed out on a live stream. Each says why it declined
instead, which is the rule ``bounded_playback_ui`` exists to enforce: a control
that silently does nothing is indistinguishable from a broken one, and a
listener cannot tell them apart by ear.

Wiring only -- every behaviour lives in ``ui/radio/bounded_playback_ui.py`` and
``ui/radio/transcript_command.py``.
"""

from __future__ import annotations

from typing import Any


def build_video_playback_items(app: Any, playback_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the timeline commands to *playback_menu* and bind them to *app*.

    Returns every id ref it created, because the caller must **pin** them:
    a menu id ref that is garbage-collected can be reissued to a different
    item, and the symptom is a random menu entry firing the wrong command.
    """
    from quill.ui.radio import bounded_playback_ui as video
    from quill.ui.radio import transcript_command as transcript

    frame = app.frame
    playback_menu.AppendSeparator()

    # Continue Listening: everything started and not finished, across every
    # provider that keeps a place. Appended here rather than in radio.py, which
    # is at its GATE-11 budget, and it belongs beside the timeline commands --
    # both are about recordings, which are the only thing Radio plays that has
    # somewhere to come back to.
    # Not Ctrl+Shift+Alt+C, which this shipped with: wx ignores the order the
    # modifiers are written in, so that is the same chord as View > Choose
    # Columns... (Ctrl+Alt+Shift+C) and one of the pair silently never fired.
    # Choose Columns keeps the C, because QUILL Cast binds it there too and a
    # family key that differs per app is worse than an unfamiliar one; this
    # takes L, for Listening.
    continue_id = wx.NewIdRef()
    playback_menu.Append(continue_id, "&Continue Listening...\tCtrl+Alt+Shift+L")
    frame.Bind(wx.EVT_MENU, lambda _e: _open_continue_listening(app), id=continue_id)

    # Chapter keys come from the shared transport table too. Next/Previous
    # were Ctrl+Alt+Right/Left, which is QUILL's table navigation -- a chapter
    # key that stops working the moment somebody is reading a table.
    chapters_id, next_ch_id, prev_ch_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
    playback_menu.Append(chapters_id, "C&hapters...\tCtrl+Shift+C")
    playback_menu.Append(next_ch_id, "Ne&xt Chapter\tCtrl+Shift+.")
    playback_menu.Append(prev_ch_id, "Pre&vious Chapter\tCtrl+Shift+,")
    frame.Bind(wx.EVT_MENU, lambda _e: video.open_chapters(app), id=chapters_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.next_chapter(app), id=next_ch_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.previous_chapter(app), id=prev_ch_id)

    # Every YouTube resolve already answers with the video's caption track;
    # until the shared reader existed, Quill Radio fetched it and discarded it
    # on every single play.
    transcript_id = wx.NewIdRef()
    playback_menu.Append(transcript_id, "&Transcript...\tCtrl+Shift+T")
    frame.Bind(wx.EVT_MENU, lambda _e: transcript.open_transcript(app), id=transcript_id)

    # Described audio, given its own two commands and placed beside the
    # transcript rather than buried in a submenu. A described track narrates
    # what is happening on screen; almost no desktop player offers a blind
    # listener a way to find one that is not a numbered guess. Both commands
    # answer even when a video has no described track, because "this video
    # published none" is exactly what the listener wanted to know.
    audio_tracks_id, described_id = wx.NewIdRef(), wx.NewIdRef()
    playback_menu.Append(audio_tracks_id, "&Audio and Described Audio...	Ctrl+Shift+A")
    playback_menu.Append(described_id, "Play &Described Audio	Ctrl+Alt+D")
    frame.Bind(wx.EVT_MENU, lambda _e: transcript.open_audio_tracks(app), id=audio_tracks_id)
    frame.Bind(wx.EVT_MENU, lambda _e: transcript.play_described_audio(app), id=described_id)

    # The picture. Every one of these is a menu item, on the Command Palette,
    # and rebindable -- there are deliberately no on-screen buttons in the Video
    # Window, because duplicating commands into an unlabelled button strip is how
    # video players become inaccessible. Captions sit here, beside Volume and
    # Audio, because Section 508's 503.4 requires exactly that placement.
    from quill.ui.radio import video_commands

    playback_menu.AppendSeparator()
    (
        show_video_id,
        captions_id,
        caption_settings_id,
        video_info_id,
        snapshot_id,
        full_screen_id,
    ) = (wx.NewIdRef() for _ in range(6))
    playback_menu.Append(show_video_id, "Show &Video	Ctrl+Shift+V")
    playback_menu.Append(captions_id, "&Captions	Ctrl+Shift+K")
    playback_menu.Append(caption_settings_id, "Caption Se&ttings...\tCtrl+Shift+Alt+T")
    playback_menu.Append(video_info_id, "Video &Information	Ctrl+Shift+I")
    playback_menu.Append(snapshot_id, "Take a Snaps&hot\tCtrl+Shift+Alt+H")
    playback_menu.Append(full_screen_id, "F&ull Screen	F11")
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.toggle_video(app), id=show_video_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.toggle_captions(app), id=captions_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.caption_settings(app), id=caption_settings_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.video_information(app), id=video_info_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.take_snapshot(app), id=snapshot_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video_commands.toggle_full_screen(app), id=full_screen_id)

    size_menu = wx.Menu()
    size_ids = []
    for label, percent in (
        ("&Fit\tCtrl+Alt+4", 100),
        ("&50%\tCtrl+Alt+5", 50),
        ("&100%\tCtrl+Alt+6", 100),
        ("&200%\tCtrl+Alt+7", 200),
    ):
        size_id = wx.NewIdRef()
        size_ids.append(size_id)
        size_menu.Append(size_id, label)
        frame.Bind(
            wx.EVT_MENU,
            lambda _e, p=percent: video_commands.set_video_size(app, p),
            id=size_id,
        )
    video_size_id = wx.NewIdRef()
    playback_menu.AppendSubMenu(size_menu, "Video Si&ze")

    faster_id, slower_id, normal_id, where_id = (
        wx.NewIdRef(),
        wx.NewIdRef(),
        wx.NewIdRef(),
        wx.NewIdRef(),
    )
    # These four moved off Ctrl+Alt+arrow in 2026-08 (reported: "the ctrl+alt
    # plus arrow keys is going to conflict with table nav"). They now read
    # their keys from quill.core.radio.transport_commands, which is the same
    # table every window's accelerators are built from -- so speed means the
    # same keystroke in Radio, in Cast, and in the browse window, and none of
    # them fights QUILL's table navigation.
    playback_menu.Append(faster_id, "Play &Faster\tCtrl+Shift+Up")
    playback_menu.Append(slower_id, "Play Slo&wer\tCtrl+Shift+Down")
    playback_menu.Append(normal_id, "&Normal Speed\tCtrl+Shift+0")
    playback_menu.Append(where_id, "Where &Am I?\tCtrl+Shift+W")
    goto_pos_id = wx.NewIdRef()
    playback_menu.Append(goto_pos_id, "&Go to Position...\tCtrl+Alt+J")
    frame.Bind(wx.EVT_MENU, lambda _e: video.go_to_position(app), id=goto_pos_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.speed_up(app), id=faster_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.slow_down(app), id=slower_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.reset_speed(app), id=normal_id)
    frame.Bind(wx.EVT_MENU, lambda _e: video.announce_position(app), id=where_id)
    return (
        continue_id,
        show_video_id,
        captions_id,
        caption_settings_id,
        video_info_id,
        snapshot_id,
        full_screen_id,
        video_size_id,
        *size_ids,
        chapters_id,
        next_ch_id,
        prev_ch_id,
        transcript_id,
        audio_tracks_id,
        described_id,
        faster_id,
        slower_id,
        normal_id,
        where_id,
        goto_pos_id,
    )


def _open_continue_listening(app: Any) -> None:
    """Quill Radio's route into the shared Continue Listening window."""
    from quill.ui.continue_listening_command import open_continue_listening

    open_continue_listening(app)
