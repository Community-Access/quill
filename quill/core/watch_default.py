"""The default watch folder: the Watch Folders page's own folder (question 38).

Settings has carried a **Default watch folder** with three switches beside it --
*Include subfolders*, *Process existing files on start* and *Start watching
automatically* -- since watch folders first shipped, and nothing read any of
them: every watched folder was a profile, and the profiles keep their own
copies of those switches. A switch that does nothing is worse than no switch,
because a screen-reader user cannot see that nothing happened.

So the page's folder is now a real watch: a built-in rule that opens each
new supported file dropped into it, the same as a new profile does out of the
box. It is described here as an ordinary :class:`WatchProfile`, so it runs
through the same manager, queue and worker as every profile and inherits their
de-duplication, schedule and failure isolation instead of a second copy of them.

Profiles are untouched: a profile's own *Include subfolders* and *Process
existing files* still decide for that profile. The page's switches decide for
the default folder only.

wx-free, strict-typed.
"""

from __future__ import annotations

from .watch_profiles import WatchProfile

#: The id the default folder's rule runs under. A fixed id (not a uuid) so a
#: queue item from an earlier session still resolves to the rule after restart.
DEFAULT_WATCH_PROFILE_ID = "default-watch-folder"

#: The name the queue and diagnostics show for the default folder's rule.
DEFAULT_WATCH_PROFILE_NAME = "Default watch folder"


def default_watch_profile(settings: object | None) -> WatchProfile | None:
    """The rule the Watch Folders page describes, or ``None`` when it has no folder.

    Reads ``watch_folder_path``, ``watch_folder_include_subfolders`` and
    ``watch_folder_process_existing``. An empty path means "no default folder",
    which is the shipped default, so nothing new is watched until somebody
    chooses a folder.
    """
    if settings is None:
        return None
    path = str(getattr(settings, "watch_folder_path", "") or "").strip()
    if not path:
        return None
    return WatchProfile(
        profile_id=DEFAULT_WATCH_PROFILE_ID,
        name=DEFAULT_WATCH_PROFILE_NAME,
        enabled=True,
        folder_path=path,
        include_subfolders=bool(getattr(settings, "watch_folder_include_subfolders", False)),
        process_existing=bool(getattr(settings, "watch_folder_process_existing", False)),
        action_id="open",
    ).normalized()


def wants_default_watch(settings: object | None) -> bool:
    """True when the default folder should be watched (*Start watching automatically*).

    The folder must be chosen and the switch on. Whether the folder exists is
    the manager's question (an invalid rule is skipped with a logged reason),
    not this one.
    """
    if settings is None:
        return False
    if not bool(getattr(settings, "watch_folder_auto_start", False)):
        return False
    return default_watch_profile(settings) is not None


def launch_plan(settings: object | None, *, safe_mode: bool) -> tuple[bool, bool]:
    """What to start when QUILL launches: ``(profiles, default_folder)``.

    *Enable folder watching by default* starts the enabled profiles; *Start
    watching automatically* starts the default folder. Safe Mode starts
    neither -- it disables the watch folder outright.
    """
    if safe_mode or settings is None:
        return (False, False)
    profiles = bool(getattr(settings, "watch_folder_enabled", False))
    return (profiles, wants_default_watch(settings))


__all__ = [
    "DEFAULT_WATCH_PROFILE_ID",
    "DEFAULT_WATCH_PROFILE_NAME",
    "default_watch_profile",
    "launch_plan",
    "wants_default_watch",
]
