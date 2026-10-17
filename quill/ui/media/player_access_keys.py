"""The Quill Media Player's access keys for its transport buttons (todo 49).

The shared :class:`~quill.ui.audio_studio.player_panel.PlayerPanel` names its
buttons for the Chapter Workbench, where &Play, Pre&vious chapter, Re&wind and
&Forward are free. In the Media Player they were not: its menu bar is &File,
&Navigation, &Playback, &View, &QuillVille, &Help and &Window, and on Windows
an Alt+letter that a control and a top-level menu share goes to the control.
So Alt+P pressed Play instead of opening Playback, Alt+V, Alt+W and Alt+F did
the same to View, Window and File, and the Audio page's Normalize loudness took
Alt+N from Navigation. GATE-15's rule is that the menu bar wins and the control
moves (GATE-14: to a free letter, and to none when no letter is free).

Every letter in the window, after the move (``tests/unit/ui/
test_menu_bar_versus_controls.py`` builds the real window and checks it):

* menus: F N P V Q H W;
* the transport row: Play and Pause A, Stop T, Previous chapter C, Next
  chapter X, Rewind R, Forward O, Where am I? I, Speed D, Mute and Unmute U;
* the Bookmarks page: Add Bookmark M, Remove Bookmark K;
* the Audio page: Equalizer preset E, Volume boost B, Normalize loudness L,
  Skip silence S.

Play and Pause keep one letter between them, and so do Mute and Unmute, so the
key a listener learns does not change with the state.
"""

from __future__ import annotations

__all__ = ["PLAYER_PANEL_LABELS"]

#: Button name -> label, handed to ``PlayerPanel(labels=...)``.
PLAYER_PANEL_LABELS: dict[str, str] = {
    "player.play": "Pl&ay",
    "player.pause": "P&ause",
    "player.prev": "Previous &chapter",
    "player.rewind": "&Rewind",
    "player.forward": "F&orward",
    "player.mute": "M&ute",
    "player.unmute": "&Unmute",
}
