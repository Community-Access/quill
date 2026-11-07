"""Publish Form, Insert Form Into Page and Test on Site, for both editors (wordpress.md 17a.7).

:class:`FormsPublishCommands` is the one class to wire: it gathers every
command of the second half of Forms -- these three, the exports
(:mod:`forms_export_commands`), Responses (:mod:`forms_responses_commands`)
and the AI (:mod:`forms_ai_commands`) -- as a mixin of the shared
:class:`~quill.ui.forms_commands.FormsCommands`, so QUILL and QUILL Lite
reach the same handlers and nothing is written twice.

A form reaches a site only through QUILL Accessible Forms' own routes
(``qaf/v1``, or the older ``baf/v1`` on a site that offers only that), on a
site the person connected, through the shared WordPress client, and only after
a confirmation naming the site. Which site and form a document was published
to is kept on this computer
(:class:`~quill.core.forms.published.PublishedStore`), with the site's
``updated_at`` at that moment: a later Publish compares it, as pages do (5.4),
and keeps the site's copy as a previous version before replacing it (5.6).
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import published as pub
from quill.core.forms import qaf_site as bs
from quill.core.wordpress import local as lc
from quill.ui import wordpress_dialogs as dlg
from quill.ui.forms_ai_commands import FormsAiCommands
from quill.ui.forms_export_commands import FormsExportCommands
from quill.ui.forms_responses_commands import FormsResponsesCommands
from quill.ui.forms_site_base import FormsSiteBase

#: How a form is published: (QAF's status, what the person chooses).
STATUSES: tuple[tuple[str, str], ...] = (
    ("active", "Live: people can fill it in wherever it is placed"),
    ("draft", "Draft: on the site, but nobody can fill it in yet"),
)


class FormsPublishCommands(
    FormsExportCommands, FormsResponsesCommands, FormsAiCommands, FormsSiteBase
):
    # ------------------------------------------------------------------ #
    # Tools > Forms > Publish Form

    def cmd_publish_form(self) -> None:
        command = "Publish Form"
        found = self.form_in_front(command)
        if found is None or self.offline_only(command):
            return
        path, doc = found
        if not self.readable(command, doc):
            return
        link = self.published().link_for(path)
        profile = self.choose_site(command, link.site_id if link else "")
        if profile is None:
            return
        same_site = link is not None and link.site_id == profile.id

        def look(api: Any) -> tuple[Any, bs.SiteForm | None]:
            existing = bs.get_form(api, link.form_id) if same_site and link else None
            return api, existing

        self.with_qaf(
            command,
            profile,
            f"reading {profile.name}",
            look,
            lambda found: self._confirm_publish(
                path, doc, profile, link if same_site else None, *found
            ),
        )

    def _confirm_publish(
        self,
        path: Any,
        doc: Any,
        profile: Any,
        link: pub.Link | None,
        api: Any,
        existing: bs.SiteForm | None,
    ) -> None:
        model = doc.model
        title = str(model.get("title") or path.stem)
        if existing is None:
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Publish Form",
                prompt="&Publish as:",
                rows=[label for _status, label in STATUSES],
                initial=0,
                help_text="Live forms take responses wherever they are placed on the site. A "
                "draft waits until you make it live, here or in QUILL Accessible Forms.",
            )
            if picked is None:
                return
            status = STATUSES[picked][0]
            message = f"Publish {title} to {profile.name} as a new form?"
            yes = "Publish"
        else:
            status = existing.status
            changed = link is not None and existing.updated_at != link.updated_at
            message = (
                f"{title} was changed on {profile.name} at {existing.updated_at}, after you last "
                "published it. Publish yours over it? QUILL keeps the site's copy on this "
                "computer as a previous version."
                if changed
                else f"Update {title} on {profile.name}? People who fill it in see the new "
                "version at once."
            )
            yes = "Publish Over It" if changed else "Update"
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Publish Form",
            message=message + self._payment_publish_notice(model),
            yes_label=yes,
        ):
            return
        from quill.ui import forms_doc as fd

        bfl = fd.canonical(model)
        store = self.published()

        def send() -> bs.SiteForm:
            from quill.core.forms.payment_site import require_ready

            require_ready(api, model)
            if existing is None:
                return bs.create_form(api, bs.publish_body(model, bfl, status=status))
            store.keep_version(profile.id, existing.id, existing.bfl_source)
            body = bs.publish_body(model, bfl, status=status, existing=existing)
            return bs.update_form(api, existing.id, body)

        def sent(form: bs.SiteForm) -> None:
            if not form.id:
                self.host.announce(f"{profile.name} did not say whether it kept the form.")
                return
            store.set_link(
                path,
                pub.Link(profile.id, form.id, form.title or title, form.updated_at, form.status),
            )
            state = "live" if form.live else f"a {form.status}"
            verb = "Published" if existing is None else "Updated"
            self.host.announce(
                f"{verb} {form.title or title} on {profile.name}, form {form.id}, {state}. "
                "Insert Form Into Page puts it on a page."
            )

        self.site_work(f"publishing to {profile.name}", send, sent)

    @staticmethod
    def _payment_publish_notice(model: dict[str, Any]) -> str:
        from quill.core.forms.payments import payment_config, payment_fields

        config = payment_config(model)
        if config is None or not payment_fields(model):
            return ""
        mode = "test payments only" if config.test_mode else "LIVE payments: real money"
        return (
            f" Payment mode: {mode}, {config.currency.upper()}, {', '.join(config.providers)}. "
            "QUILL will first read the site's payment and webhook readiness."
        )

    # ------------------------------------------------------------------ #
    # Tools > Forms > Insert Form Into Page (a WordPress page in front)

    def cmd_insert_into_page(self) -> None:
        command = "Insert Form Into Page"
        local = lc.LocalStore(self.forms_data_dir())
        copy = local.copy_for_path(self.host.current_path())
        if copy is None:
            self.host.announce(
                f"{command} works in a WordPress page or post. Open one with File, WordPress, "
                "then try again."
            )
            return
        if self.offline_only(command):
            return
        profile = self.form_sites().get(copy.site_id)
        if profile is None:
            self.host.announce(
                "The site this page belongs to is no longer in your list of sites. Connect it "
                "again with Connect a Site."
            )
            return
        self.with_qaf(
            command,
            profile,
            f"listing the forms on {profile.name}",
            lambda api: (bs.list_forms(api), bs.plugin_prefix(api)),
            lambda found: self._insert_form(profile, copy.text_format, *found),
        )

    def _insert_form(
        self, profile: Any, text_format: str, forms: list[bs.SiteForm], prefix: str = "qaf"
    ) -> None:
        if not forms:
            self.host.announce(
                f"{profile.name} has no forms yet. Publish one with Publish Form, then insert it."
            )
            return
        mine = {link.form_id for link in self.published().links_on(profile.id)}
        initial = next((i for i, f in enumerate(forms) if f.id in mine), 0)
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Insert Form Into Page",
            prompt="&Form:",
            rows=[f.spoken() for f in forms],
            initial=initial,
            help_text="The forms on this site, with how many responses each has had. The one "
            "you published last from this computer is selected.",
        )
        if index is None:
            return
        form = forms[index]
        text, what = bs.placement(form.id, text_format, prefix)
        self.host.insert_text(text)
        note = "" if form.live else " It is a draft, so visitors see nothing until it is live."
        self.host.announce(
            f"Inserted the {form.title or 'untitled'} form, as {what}. It shows on the page once "
            f"the page is sent.{note}"
        )

    # ------------------------------------------------------------------ #
    # Tools > Forms > Test on Site

    def cmd_test_on_site(self) -> None:
        command = "Test on Site"
        found = self.form_in_front(command)
        if found is None or self.offline_only(command):
            return
        path, _doc = found
        link = self.published().link_for(path)
        profile = self.form_sites().get(link.site_id) if link else None
        if link is None or profile is None:
            self.host.announce(
                "This form is not on a site yet. Publish it with Publish Form, then Test on Site "
                "opens it there."
            )
            return

        from quill.core.forms.payments import payment_fields

        if payment_fields(_doc.model) and not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Test Payment on Site",
            message=f"Read the published payment form on {profile.name} and open its checkout "
            "in your browser? QUILL will refuse if the published form is not in test mode.",
            yes_label="Test Payment",
        ):
            return

        def work(api: Any) -> tuple[bs.SiteForm, list[tuple[str, str, str]], str]:
            form = bs.get_form(api, link.form_id)
            from quill.core.forms.payment_site import PaymentSiteError, require_ready
            from quill.core.forms.payments import payment_config

            remote = form.model() or {}
            if payment_fields(remote) or payment_fields(_doc.model):
                config = payment_config(remote)
                if config is None or not config.test_mode:
                    raise PaymentSiteError(
                        "The published form is not in payment test mode. Publish a test-mode "
                        "form to a test-configured site before trying checkout."
                    )
                require_ready(api, remote)
            remote_config = payment_config(remote) if payment_fields(remote) else None
            paid = remote_config.providers if remote_config else ()
            return form, bs.pages_showing(api, link.form_id), bs.plugin_prefix(api), paid

        self.with_qaf(
            command,
            profile,
            f"finding the form on {profile.name}",
            work,
            lambda found: self._open_test(profile, *found),
        )

    #: Said after Test on Site opens a test-mode payment form, per provider:
    #: the published test numbers, so nobody reaches for a real card.
    TEST_PAYMENT_HINTS = {
        "stripe": "Stripe's test card 4242 4242 4242 4242 with any future date and any "
        "three-digit code",
        "paypal": "a PayPal sandbox buyer account",
    }

    def _open_test(
        self,
        profile: Any,
        form: bs.SiteForm,
        pages: list[tuple[str, str, str]],
        prefix: str = "qaf",
        paid: tuple[str, ...] = (),
    ) -> None:
        draft = "" if form.live else " It is a draft, so only you can see it there."
        hints = [self.TEST_PAYMENT_HINTS[p] for p in paid if p in self.TEST_PAYMENT_HINTS]
        if hints:
            draft += " To pay in test mode, use " + ", or ".join(hints) + ". Never a real card."
        live = [p for p in pages if p[1]]
        if live:
            name, link, status = live[0]
            self.host.open_in_browser(link)
            state = "" if status == "publish" else f", a {status} page"
            self.host.announce(
                f"Opened {name or 'the page'}{state} on {profile.name}, where the form is.{draft}"
            )
            return
        self.host.open_in_browser(bs.builder_url(profile.site_url, form.id, prefix))
        self.host.announce(
            f"No page on {profile.name} shows {form.title or 'this form'} yet, so QUILL opened it "
            "in QUILL Accessible Forms on the site. Insert Form Into Page puts it on a page."
            f"{draft}"
        )


__all__ = ["STATUSES", "FormsPublishCommands"]
