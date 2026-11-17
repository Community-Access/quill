"""Replace File on a Media row, and Tools > WXR Files (wp_missing.md, Media and Moving).

Split from :mod:`quill.core.wordpress.workbench_actions` and
:mod:`~quill.core.wordpress.workbench_window_menu` (GATE-11), which splice
these in. None has a chord: :data:`KEYLESS` says why for each (family rule 8).
Replace File is on the Media row's context menu (Applications key or
Shift+F10); the three import and export commands are in Tools > WXR Files, a
submenu whose rows are reached by their access letters (Alt+T, W, then E, I or
B). Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.menus import MenuRow, MenuSub

__all__ = ["KEYLESS", "MEDIA_ROWS", "WXR_SUB", "command"]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


MEDIA_ROWS: tuple[ActionRow, ...] = (
    ActionRow(
        command("replace_file"),
        "Replace File...",
        Tier.WRITE,
        "upload_files",
        "Put a new file in this one's place, after a preview of both. Where the site has a "
        "replace route the address stays the same; otherwise the new file is uploaded and "
        "every page, post and featured image that used the old one is pointed at it, which "
        "Ctrl+Z puts back.",
        False,
    ),
)

WXR_SUB = MenuSub(
    "&WXR Files",
    (
        MenuRow(
            command("export_wxr"),
            "&Export Site as WXR...",
            help="This site, or part of it, as a WordPress export file any WordPress imports.",
        ),
        MenuRow(
            command("archive_static"),
            "Archive a &Static Copy...",
            help=(
                "The published pages and posts as plain HTML files, with their pictures and "
                "files from this site's own host, in a folder you choose."
            ),
        ),
        MenuRow(
            command("import_wxr"),
            "&Import WXR as Drafts...",
            help="A WordPress export file from any site, previewed, then made here as drafts.",
        ),
        MenuRow(
            command("import_platform"),
            "Import from &Blogger, Medium, Substack or Squarespace...",
            help=(
                "Another platform's export file, read on this computer, previewed, then made "
                "here as drafts. Pictures keep showing from where they are now."
            ),
        ),
    ),
    help="WordPress export files (WXR), written and read on this computer.",
)

KEYLESS: dict[str, str] = {
    command("replace_file"): "Opens a file picker and a preview, now and then (rule 9).",
    command("export_wxr"): "Moving hosts or keeping a copy: a few times a site's life (rule 9).",
    command("archive_static"): "Archiving a site is done a few times in its life (rule 9).",
    command("import_wxr"): "Moving content in happens once per move (rule 9).",
    command("import_platform"): "Moving in from another platform happens once (rule 9).",
}
"""Why each command here has no chord (family rule 8)."""
