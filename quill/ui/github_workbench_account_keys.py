"""People > My Keys: adding and deleting your SSH, GPG and signing keys (GitHub PRD 14.3).

The list is an Explore view (``my_keys``, from
:mod:`quill.core.github.account_keys`). **New Here** there adds a key, read
from a file (``~/.ssh`` first) or pasted; **Delete Key...** removes one
after saying what stops working without it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["ACCOUNT_KEY_REASONS", "ACCOUNT_KEY_VERBS", "GitHubWorkbenchAccountKeysMixin"]

ACCOUNT_KEY_VERBS: dict[str, frozenset[str]] = {
    "new_key": frozenset({"view"}),
    "delete_key": frozenset({"key"}),
}

ACCOUNT_KEY_REASONS: dict[str, str] = {
    "new_key": "New Here in My Keys adds a key, while you are signed in.",
    "delete_key": "Delete Key is for one of your keys, while you are signed in.",
}

_KIND_CHOICES = (
    ("ssh", "SSH key, for pushing and pulling over SSH"),
    ("signing", "SSH signing key, to mark your commits Verified"),
    ("gpg", "GPG key, to mark your commits Verified"),
)
_WHAT_STOPS = {
    "ssh": "git on any computer using this key can no longer push or pull over SSH.",
    "signing": "commits signed with it will no longer show as Verified.",
    "gpg": "commits signed with it will no longer show as Verified.",
}
#: A public key is a few kilobytes at most; anything bigger is not one.
_MOST = 64 * 1024


class GitHubWorkbenchAccountKeysMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_new_key(self, _row: object) -> bool:
        current = getattr(self.frame, "current", None)
        return self.signed_in and getattr(current, "key", "") == "my_keys"

    def _fits_delete_key(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and row.kind == "key"

    def _read_key_file(self, kind: str) -> str | None:
        """The text of a public key file the person chooses; None when they cancel."""
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        wildcard = (
            "GPG public keys (*.asc;*.gpg;*.txt)|*.asc;*.gpg;*.txt|All files (*.*)|*.*"
            if kind == "gpg"
            else "SSH public keys (*.pub)|*.pub|All files (*.*)|*.*"
        )
        folder = Path.home() / ".ssh"
        with wx.FileDialog(
            self.frame.frame,
            "Choose the public key file",
            defaultDir=str(folder if folder.is_dir() else Path.home()),
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as box:
            if show_modal_dialog(box, "Choose the public key file") != wx.ID_OK:
                return None
            path = Path(box.GetPath())
        try:
            if path.stat().st_size > _MOST:
                self._say(f"{path.name} is too big to be a public key.")
                return None
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._say(f"Could not read {path.name}: {exc}")
            return None

    def _do_new_key(self, _ref: Any, _row: object) -> None:
        from quill.core.github.account_keys import add_key

        picked = self._choose(
            "New Key", "Which kind of key?", [label for _kind, label in _KIND_CHOICES]
        )
        if picked < 0:
            return
        kind = _KIND_CHOICES[picked][0]
        how = self._choose(
            "New Key", "Where is the public key?", ["In a file on this computer", "I will paste it"]
        )
        if how < 0:
            return
        text = (
            self._read_key_file(kind)
            if how == 0
            else self._ask_text("New Key", "Paste the public key:", multiline=True)
        )
        if not text:
            return
        comment = text.split()[2] if kind != "gpg" and len(text.split()) > 2 else ""
        title = self._ask_text(
            "New Key", "A name for it, such as the computer it is on:", value=comment
        )
        if not title:
            return
        api = self.github_api()
        self._background(
            "add the key",
            lambda: add_key(api, kind, title, text),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_delete_key(self, _ref: Any, row: object) -> None:
        from quill.core.github.account_keys import delete_key

        if not isinstance(row, ExploreRow):
            return
        kind = row.key.partition(":")[0]
        if not self._confirm(
            "Delete Key",
            f"Delete {row.label.rstrip('.')}? Once it is gone, {_WHAT_STOPS.get(kind, '')}",
        ):
            return
        api = self.github_api()
        self._background(
            "delete the key",
            lambda: delete_key(api, row.key),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )
