"""Add or remove a reaction, chosen by name from GitHub's eight.

Shared by the pull-request review window and the GitHub Items viewer. The
chooser lists "thumbs up", "heart" and the rest, and says which ones are
already yours; choosing one of yours removes it, choosing another adds it.
Both the read of your reactions and the change run off the UI thread, and
what is said afterwards is only what GitHub confirmed.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.reactions import reaction_choices
from quill.ui.dialog_contract import dialog_alive, show_modal_dialog


def start_reaction_flow(
    parent: object,
    provider: object,
    repo: str,
    kind: str,
    target_id: int,
    *,
    what: str,
    announce: Callable[[str], None],
    on_done: Callable[[], None] | None = None,
) -> None:
    """Read your reactions, ask which to add or remove, then make the change."""
    import wx

    if not getattr(provider, "is_authenticated", False):
        announce("Sign in to GitHub to react.")
        return

    def failed(message: str) -> None:
        if dialog_alive(parent):
            announce(message)

    def changed(message: str) -> None:
        if not dialog_alive(parent):
            return
        announce(message)
        if on_done is not None:
            on_done()

    def apply(content: str, remove: bool) -> None:
        def worker() -> None:
            try:
                if remove:
                    message = provider.remove_reaction(repo, kind, target_id, content)
                else:
                    message = provider.add_reaction(repo, kind, target_id, content)
            except GitHubItemsError as exc:
                wx.CallAfter(failed, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - visible, never swallowed
                wx.CallAfter(failed, f"Could not change the reaction: {exc}")
                return
            wx.CallAfter(changed, message)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: reaction write.

    def choose(mine: frozenset[str]) -> None:
        if not dialog_alive(parent):
            return
        rows = reaction_choices(mine)
        dialog = wx.SingleChoiceDialog(
            parent,
            f"Choose a reaction for {what}. Choosing one of yours removes it.",
            "React",
            [label for _content, label in rows],
        )
        try:
            if show_modal_dialog(dialog, "React", announce=announce) != wx.ID_OK:
                return
            index = dialog.GetSelection()
        finally:
            dialog.Destroy()
        if 0 <= index < len(rows):
            content = rows[index][0]
            apply(content, content in mine)

    def read_mine() -> None:
        try:
            mine = provider.fetch_my_reactions(repo, kind, target_id)
        except GitHubItemsError as exc:
            wx.CallAfter(failed, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - visible, never swallowed
            wx.CallAfter(failed, f"Could not read your reactions: {exc}")
            return
        wx.CallAfter(choose, mine)

    threading.Thread(target=read_mine, daemon=True).start()  # GATE-40-OK: reaction read.


__all__ = ["start_reaction_flow"]
