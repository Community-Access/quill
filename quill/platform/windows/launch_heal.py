"""Repair a launch entry an older build wrote wrong (Run key, scheduled task).

Every build from the shared-runtime move (2026-08-17) until 3.0.1 wrote the
Run-key entry as the bare ``QuillVilleRuntime.exe`` -- no module -- so the
entry is on listeners' machines already, and fixing ``launch_command`` alone
would leave it broken until each of them happened to toggle the setting off
and on. The app therefore checks its own entry at launch and rewrites it.

Only an entry that exists is touched (the listener turned it on; nothing is
ever created), only when it differs by :func:`quill.core.app_command.should_replace`,
never from a portable copy, and never raising -- a locked-down registry costs
the heal, not the launch.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any
from xml.sax.saxutils import unescape

from quill.core.app_command import should_replace, to_command_line

logger = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def heal_run_value(winreg_module: Any, value_name: str, current: str) -> bool:
    """Rewrite ``HKCU\\...\\Run\\<value_name>`` to *current* when stale.

    True only when a value was rewritten.
    """
    if winreg_module is None:
        return False
    try:
        with winreg_module.OpenKey(winreg_module.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            stored, _kind = winreg_module.QueryValueEx(key, value_name)
    except OSError:
        return False  # no entry: the listener never asked to start with Windows
    except Exception:  # noqa: BLE001 - a heal must never cost the launch
        return False
    if not isinstance(stored, str) or not should_replace(stored, current):
        return False
    try:
        with winreg_module.OpenKey(
            winreg_module.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg_module.KEY_SET_VALUE
        ) as key:
            winreg_module.SetValueEx(key, value_name, 0, winreg_module.REG_SZ, current)
    except Exception:  # noqa: BLE001 - locked-down registry: keep going
        logger.info("Could not repair the %s startup entry.", value_name, exc_info=True)
        return False
    logger.info("Repaired the %s startup entry: %r -> %r", value_name, stored, current)
    return True


def heal_allowed(*, frozen: bool | None = None) -> bool:
    """Whether this run may repair entries at all.

    Only a packaged build (the runtime is a PyInstaller bundle), so a dev run
    or a test never rewrites the developer's own startup entries with a source
    interpreter; and never a portable copy, which leaves the host alone.
    """
    import sys

    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if not frozen:
        return False
    try:
        from quill.core.paths import portable_bundle_root

        return portable_bundle_root() is None
    except Exception:  # noqa: BLE001 - unsure means do not touch the host
        return False


def heal_in_background(task_manager: Any, *healers: Callable[[], bool]) -> None:
    """Run each app's healers once, off the UI thread, at launch.

    A scheduled-task heal spawns ``schtasks`` twice, which is not something a
    window that is still settling should wait on. Never raises; a healer that
    fails costs only itself.
    """

    def _work(**_kwargs: Any) -> None:
        for heal in healers:
            try:
                heal()
            except Exception:  # noqa: BLE001 - each heal is best effort
                logger.debug("A launch-entry heal failed.", exc_info=True)

    if task_manager is None:
        return
    try:
        task_manager.submit("launch-entry-heal", _work, on_success=None, on_failure=None)
    except Exception:  # noqa: BLE001 - no task manager: no heal this launch
        return


# -- scheduled tasks ----------------------------------------------------------
#
# The same builds registered Task Scheduler entries the same way (the weather
# check, the recording wake), and a task's command is only readable back as its
# XML definition, so these read just enough of it to compare.


def query_task_xml(schtasks: str, task_name: str) -> str:
    """The registered task's XML definition, or "" when there is none.

    Never raises: no task, no ``schtasks`` and a locked-down machine all mean
    "nothing to heal".
    """
    from quill.stability.safe_subprocess import run_subprocess_safely

    try:
        result = run_subprocess_safely(
            [schtasks, "/Query", "/TN", task_name, "/XML"], timeout_seconds=20.0
        )
    except Exception:  # noqa: BLE001 - nothing to heal
        return ""
    if getattr(result, "returncode", 1) != 0:
        return ""
    return str(getattr(result, "stdout", "") or "")


def task_element(xml: str, tag: str) -> str:
    """The text of the first ``<tag>`` in *xml*, unescaped, or ""."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.DOTALL)
    return unescape(match.group(1).strip()) if match else ""


def task_command(xml: str) -> str:
    """The task's ``<Exec>`` as one command line, in the form
    :func:`quill.core.app_command.to_command_line` writes, or ""."""
    executable = task_element(xml, "Command").strip('"')
    if not executable:
        return ""
    arguments = task_element(xml, "Arguments")
    head = to_command_line([executable])
    return f"{head} {arguments}" if arguments else head


def task_enabled(xml: str) -> bool:
    """False when any ``<Enabled>`` (the task's own, or its trigger's) is off:
    a listener who disabled the task in Task Scheduler meant it."""
    flags = re.findall(r"<Enabled>\s*(\w+)\s*</Enabled>", xml)
    return all(flag.lower() == "true" for flag in flags)


def task_needs_heal(xml: str, current: str) -> bool:
    """An existing, enabled task whose stored command should become *current*."""
    if not xml or not task_enabled(xml):
        return False
    stored = task_command(xml)
    return bool(stored) and should_replace(stored, current)
