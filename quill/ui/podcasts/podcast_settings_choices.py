"""The fixed choice lists behind Podcast Settings, and what each one stores.

Split out of ``podcast_settings_dialog`` (GATE-11) rather than because they had
grown complicated: a wx ``Choice`` control speaks in *positions*, the settings
record speaks in *values*, and every one of these pairs exists to keep those two
in step. Keeping them together, away from four hundred lines of sizer code, is
what makes it obvious that a label and its value must be added in the same
place -- a labels tuple that grew a row its values tuple did not is a control
that silently stores the wrong answer.

Names stay underscore-prefixed so the dialog reads exactly as it did before.
No wx here, and nothing that touches a settings file.
"""

from __future__ import annotations

_PLAYBACK_MODES = ("download", "stream")
_PLAYBACK_LABELS = ("Download episodes", "Stream episodes")
# "Delete after playing" used to be a third *mode* here, so choosing it gave up
# "keep only the most recent" -- two answers to different questions sharing one
# control. It is a checkbox below now; an old file carrying the mode arrives
# with that checkbox ticked (PodcastSettings.from_dict).
_RETENTION_MODES = ("keep_all", "keep_last_n")
_RETENTION_LABELS = (
    "Keep every episode",
    "Keep only the most recent episodes",
)
_DELETE_POLICIES = ("ask", "always", "never")
_DELETE_LABELS = ("Ask me each time", "Always delete them", "Never delete them")
#: Auto-download (1.1.0): the acquisition policy every new show starts with.
_AUTO_DOWNLOAD_LABELS = (
    "None -- download by hand",
    "The newest episode",
    "The newest 3",
    "The newest 5",
    "The newest 10",
    "Every episode (full catalog)",
)
_AUTO_DOWNLOAD_VALUES = (0, 1, 3, 5, 10, -1)
#: Which node the library tree lands on at launch.
_LAUNCH_VIEW_LABELS = (
    "The top of the library",
    "New Episodes",
    "Continue Listening",
    "Inbox",
    "Favorites",
    "Recently Expired",
)
#: How long a listening history is kept. -1 is "do not keep one at all", which
#: is short-circuited at the write rather than pruned afterwards; 0 is forever.
_HISTORY_LABELS = (
    "Do not keep a history",
    "30 days",
    "90 days",
    "1 year",
    "Keep forever",
)
_HISTORY_VALUES = (-1, 30, 90, 365, 0)

_LAUNCH_VIEW_VALUES = (
    "",
    "new_episodes",
    "continue_listening",
    "inbox",
    "favorites",
    "recently_expired",
)
