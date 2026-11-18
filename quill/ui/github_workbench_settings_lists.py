"""Repository > Settings > Webhooks, Deploy Keys and Autolinks: what each row can do (PRD 14.3).

The lists are Explore views (:mod:`quill.core.github.repo_settings_lists`).
New Here in each adds one; on a row: Ping, Recent Deliveries... (with
redelivery), Change Address or Secret... and Delete for a webhook, and Delete
for a deploy key or an autolink. A webhook secret is asked for in a password
box and is never said, shown or kept.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["SETTINGS_LIST_REASONS", "SETTINGS_LIST_VERBS", "GitHubWorkbenchSettingsListsMixin"]

SETTINGS_LIST_VERBS: dict[str, frozenset[str]] = {
    "new_webhook": frozenset({"view"}),
    "ping_webhook": frozenset({"webhook"}),
    "webhook_deliveries": frozenset({"webhook"}),
    "change_webhook": frozenset({"webhook"}),
    "delete_webhook": frozenset({"webhook"}),
    "new_deploy_key": frozenset({"view"}),
    "delete_deploy_key": frozenset({"deploy_key"}),
    "new_autolink": frozenset({"view"}),
    "delete_autolink": frozenset({"autolink"}),
}

SETTINGS_LIST_REASONS: dict[str, str] = {
    "new_webhook": "New Here in Webhooks adds a webhook, for the repository's administrators.",
    "ping_webhook": "Ping is for a webhook.",
    "webhook_deliveries": "Recent Deliveries is for a webhook.",
    "change_webhook": "Change Address or Secret is for a webhook.",
    "delete_webhook": "Delete Webhook is for a webhook.",
    "new_deploy_key": "New Here in Deploy Keys adds a key, for the repository's administrators.",
    "delete_deploy_key": "Delete Deploy Key is for a deploy key.",
    "new_autolink": "New Here in Autolinks adds one, for the repository's administrators.",
    "delete_autolink": "Delete Autolink is for an autolink.",
}

_EVENT_CHOICES = ("Just the push event", "Everything", "Let me choose the events")


class GitHubWorkbenchSettingsListsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    # -- where each fits -------------------------------------------------------------

    def _on_node(self, key: str) -> bool:
        return self.signed_in and getattr(getattr(self.frame, "current", None), "key", "") == key

    @staticmethod
    def _of(row: object, kind: str) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == kind and bool(row.key)
        return row if found and isinstance(row, ExploreRow) else None

    def _fits_new_webhook(self, _row: object) -> bool:
        return self._on_node("webhooks") or self._on_node("organization_webhooks")

    def _fits_new_deploy_key(self, _row: object) -> bool:
        return self._on_node("deploy_keys")

    def _fits_new_autolink(self, _row: object) -> bool:
        return self._on_node("autolinks")

    def _fits_ping_webhook(self, row: object) -> bool:
        return self.signed_in and self._of(row, "webhook") is not None

    _fits_webhook_deliveries = _fits_ping_webhook
    _fits_change_webhook = _fits_ping_webhook
    _fits_delete_webhook = _fits_ping_webhook

    def _fits_delete_deploy_key(self, row: object) -> bool:
        return self.signed_in and self._of(row, "deploy_key") is not None

    def _fits_delete_autolink(self, row: object) -> bool:
        return self.signed_in and self._of(row, "autolink") is not None

    # -- helpers ---------------------------------------------------------------------

    def _secret(self, title: str, prompt: str) -> str | None:
        """A password box: the secret is never shown, said or kept. None means Cancel."""
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        with wx.PasswordEntryDialog(self.frame.frame, prompt, title) as box:
            box.SetName("Secret")
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return str(box.GetValue())

    def _then_reload(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _choose_events(self) -> list[str] | None:
        from quill.core.github.repo_settings_lists import COMMON_EVENTS
        from quill.ui.dialog_contract import show_modal_dialog

        picked = self._choose(
            "New Webhook", "Which events send it a message?", list(_EVENT_CHOICES)
        )
        if picked < 0:
            return None
        if picked == 0:
            return ["push"]
        if picked == 1:
            return ["*"]
        wx = self.frame._wx
        labels = list(COMMON_EVENTS)
        with wx.MultiChoiceDialog(self.frame.frame, "Check the events:", "Events", labels) as box:
            box.SetSelections([0])
            if show_modal_dialog(box, "Events") != wx.ID_OK:
                return None
            return [labels[i] for i in box.GetSelections()]

    # -- webhooks --------------------------------------------------------------------

    def _do_new_webhook(self, ref: Any, _row: object) -> None:
        from quill.core.github.repo_settings_lists import add_webhook

        url = self._ask_text("New Webhook", "The address GitHub sends to, starting https://:")
        if not url:
            return
        kind = self._choose("New Webhook", "Send it as:", ["JSON (application/json)", "Form"])
        if kind < 0:
            return
        events = self._choose_events()
        if not events:
            return
        secret = self._secret(
            "New Webhook",
            "A secret GitHub signs each message with, or leave it empty. It is never shown again.",
        )
        if secret is None:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "add the webhook",
            lambda: add_webhook(api, repository, url, events=events, json=kind == 0, secret=secret),
            self._then_reload,
        )

    def _do_ping_webhook(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import ping_webhook

        found = self._of(row, "webhook")
        if found is None:
            return
        api, repository = self.github_api(), ref.instance
        self._background("ping it", lambda: ping_webhook(api, repository, found.key), self._say)

    def _do_webhook_deliveries(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import fetch_deliveries

        found = self._of(row, "webhook")
        if found is None:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "read the deliveries",
            lambda: fetch_deliveries(api, repository, found.key),
            lambda deliveries: self._pick_delivery(repository, found.key, list(deliveries)),
        )

    def _pick_delivery(self, repository: str, hook: str, deliveries: list[Any]) -> None:
        from quill.core.github.repo_settings_lists import redeliver

        if not deliveries:
            self._say("GitHub has sent this webhook nothing yet.")
            return
        picked = self._choose(
            "Recent Deliveries",
            "Newest first. Choose one to deliver it again, or Cancel.",
            [delivery.label for delivery in deliveries],
        )
        if picked < 0:
            return
        delivery = deliveries[picked]
        if not self._confirm("Redeliver", f"Deliver {delivery.label} again?"):
            return
        api = self.github_api()
        self._background(
            "redeliver it", lambda: redeliver(api, repository, hook, delivery), self._say
        )

    def _do_change_webhook(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import change_webhook

        found = self._of(row, "webhook")
        if found is None:
            return
        address = found.label.split(": ", 1)[0]
        url = self._ask_text("Change Webhook", "The address, or leave it as it is:", value=address)
        if not url:
            return
        secret = self._secret(
            "Change Webhook", "A new secret, or leave it empty to keep the old one."
        )
        if secret is None:
            return
        api, repository = self.github_api(), ref.instance
        new_url = "" if url == address else url
        self._background(
            "change the webhook",
            lambda: change_webhook(api, repository, found.key, url=new_url, secret=secret),
            self._then_reload,
        )

    def _do_delete_webhook(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import delete_webhook

        found = self._of(row, "webhook")
        if found is None or not self._confirm(
            "Delete Webhook",
            f"Delete the webhook to {found.label.split(': ', 1)[0]}? GitHub stops sending it "
            "anything, and its delivery history goes too.",
        ):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "delete the webhook",
            lambda: delete_webhook(api, repository, found.key),
            self._then_reload,
        )

    # -- deploy keys and autolinks -----------------------------------------------------

    def _do_new_deploy_key(self, ref: Any, _row: object) -> None:
        from quill.core.github.repo_settings_lists import add_deploy_key

        how = self._choose(
            "New Deploy Key",
            "Where is the public key?",
            ["In a file on this computer", "I will paste it"],
        )
        if how < 0:
            return
        reader = getattr(self, "_read_key_file", None)
        text = (
            reader("ssh")
            if how == 0 and reader is not None
            else self._ask_text("New Deploy Key", "Paste the public key:", multiline=True)
        )
        if not text:
            return
        title = self._ask_text("New Deploy Key", "A name for it, such as the server it is on:")
        if not title:
            return
        access = self._choose(
            "New Deploy Key",
            "What may it do?",
            ["Read only: clone and pull", "Read and write: push too"],
        )
        if access < 0:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "add the deploy key",
            lambda: add_deploy_key(api, repository, title, text, read_only=access == 0),
            self._then_reload,
        )

    def _do_delete_deploy_key(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import delete_deploy_key

        found = self._of(row, "deploy_key")
        if found is None or not self._confirm(
            "Delete Deploy Key",
            f"Delete {found.label.rstrip('.')}? Whatever uses it can no longer reach the "
            "repository.",
        ):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "delete the deploy key",
            lambda: delete_deploy_key(api, repository, found.key),
            self._then_reload,
        )

    def _do_new_autolink(self, ref: Any, _row: object) -> None:
        from quill.core.github.repo_settings_lists import add_autolink

        prefix = self._ask_text("New Autolink", "The prefix that starts a reference, such as BUG-:")
        if not prefix:
            return
        template = self._ask_text(
            "New Autolink",
            f"The address it links to, with <num> where the part after {prefix} goes:",
        )
        if not template:
            return
        kind = self._choose(
            "New Autolink", f"What may follow {prefix}?", ["Numbers only", "Letters and numbers"]
        )
        if kind < 0:
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "add the autolink",
            lambda: add_autolink(api, repository, prefix, template, alphanumeric=kind == 1),
            self._then_reload,
        )

    def _do_delete_autolink(self, ref: Any, row: object) -> None:
        from quill.core.github.repo_settings_lists import delete_autolink

        found = self._of(row, "autolink")
        if found is None or not self._confirm("Delete Autolink", f"Delete: {found.label}"):
            return
        api, repository = self.github_api(), ref.instance
        self._background(
            "delete the autolink",
            lambda: delete_autolink(api, repository, found.key),
            self._then_reload,
        )
