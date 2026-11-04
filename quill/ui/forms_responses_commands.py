"""Tools > Forms > Responses: what people sent, read and exported (wordpress.md 17a.8).

A mixin of :class:`~quill.ui.forms_publish_commands.FormsPublishCommands`.
Responses are personal data. They are read from the site only when this
window opens (``GET /baf/v1/entries``), held in memory while it is open, never
written to a log, and written to a file only where the person chooses. Nothing
in this window sends them anywhere else; Summarise asks first, every time.

The window is the WordPress list window (Comments, Media Library), so it is
learned once: the responses, newest first, and buttons -- Read (Enter does the
same), View, Find, Mark, the exports, Summarise and Delete.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from quill.core.forms import baf_site as bs
from quill.core.forms import responses as rs
from quill.core.storage import write_text_atomic
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_route_dialogs as rdlg

CSV_WILDCARD = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
WORD_WILDCARD = "Word documents (*.docx)|*.docx|All files (*.*)|*.*"


def _noun(count: int) -> str:
    return f"{count} {'response' if count == 1 else 'responses'}"


class FormsResponsesCommands:
    # Provided by FormsSiteBase and the commands class.
    host: Any

    def cmd_form_responses(self) -> None:
        command = "Responses"
        if self.offline_only(command):  # type: ignore[attr-defined]
            return
        from quill.core.forms.menu import is_form_path

        path = self.host.current_path()
        link = self.published().link_for(path) if is_form_path(path) else None  # type: ignore[attr-defined]
        profile = self.choose_site(command, link.site_id if link else "")  # type: ignore[attr-defined]
        if profile is None:
            return
        if link is not None and link.site_id == profile.id:
            self._load_responses(profile, link.form_id)
            return
        self.with_baf(  # type: ignore[attr-defined]
            command,
            profile,
            f"listing the forms on {profile.name}",
            bs.list_forms,
            lambda forms: self._pick_form(profile, forms),
        )

    def _pick_form(self, profile: Any, forms: list[bs.SiteForm]) -> None:
        if not forms:
            self.host.announce(f"{profile.name} has no forms yet, so there are no responses.")
            return
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Responses",
            prompt="&Form:",
            rows=[f.spoken() for f in forms],
            initial=0,
            help_text="Whose responses to read. Each form says how many it has had.",
        )
        if index is not None:
            self._load_responses(profile, forms[index].id)

    def _load_responses(self, profile: Any, form_id: int) -> None:
        def work(api: Any) -> tuple[Any, bs.SiteForm, list[bs.Response]]:
            return api, bs.get_form(api, form_id), bs.list_responses(api, form_id)

        self.with_baf(  # type: ignore[attr-defined]
            "Responses",
            profile,
            f"reading responses on {profile.name}",
            work,
            lambda found: self._show_responses(profile, *found),
        )

    def _show_responses(  # noqa: C901 - one window, one closure per button
        self, profile: Any, api: Any, form: bs.SiteForm, live: list[bs.Response]
    ) -> None:
        self.published().mark_seen(profile.id, form.id, max(form.entry_count, len(live)))  # type: ignore[attr-defined]
        title = form.title or "Untitled form"
        labels = form.question_labels()
        if not live:
            self.host.announce(f"{title} on {profile.name} has no responses yet.")
            return
        state: dict[str, Any] = {"view": "list", "find": "", "marked": set()}
        shown: list[rs.Row] = []

        def rows() -> list[str]:
            chosen = rs.find(live, state["find"])
            shown[:] = rs.view_rows(state["view"], chosen, labels, title)
            return [
                ("Marked, " if r.response and r.response.id in state["marked"] else "") + r.text
                for r in shown
            ]

        def at(index: int | None) -> bs.Response | None:
            if index is None or index >= len(shown):
                return None
            found = shown[index].response
            if found is None:
                self.host.announce("That is a heading. Choose a response under it.")
            return found

        def visible() -> list[bs.Response]:
            return [r.response for r in shown if r.response is not None]

        def read(index: int | None) -> object:
            response = at(index)
            if response is not None:
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title=f"Response {response.id}",
                    text=rs.one_at_a_time(response, labels, title),
                    help_text="One response, a question and its answer on each line.",
                )
            return None

        def view(_index: int | None) -> object:
            names = [label for _key, label in rs.VIEWS]
            current = [key for key, _label in rs.VIEWS].index(state["view"])
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="View Responses",
                prompt="&View:",
                rows=names,
                initial=current,
                help_text="The list, newest first; or grouped under a heading for each day, "
                "or for each place the responses gave.",
            )
            if picked is None:
                return None
            state["view"] = rs.VIEWS[picked][0]
            return rows()

        def find(_index: int | None) -> object:
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Find in Responses",
                prompt="&Find:",
                value=state["find"],
                help_text="Words to find in any answer. Leave it empty to show every response.",
            )
            if text is None:
                return None
            state["find"] = text.strip()
            count = len(rs.find(live, state["find"]))
            self.host.announce(
                f"{_noun(count)} with {state['find']}." if state["find"] else "Every response."
            )
            return rows()

        def mark(index: int | None) -> object:
            response = at(index)
            if response is not None:
                state["marked"].symmetric_difference_update({response.id})
            return rows()

        def export_csv(_index: int | None) -> object:
            self._export_responses_csv(title, visible(), labels, open_after=False)
            return None

        def open_table(_index: int | None) -> object:
            self._export_responses_csv(title, visible(), labels, open_after=True)
            return dlg.CLOSE

        def export_word(index: int | None) -> object:
            selected = shown[index].response if index is not None and index < len(shown) else None
            self._export_responses_word(title, visible(), labels, selected)
            return None

        def summarise(_index: int | None) -> object:
            self.summarise_responses(title, visible(), labels)  # type: ignore[attr-defined]
            return None

        def delete(index: int | None) -> object:
            chosen = [r for r in live if r.id in state["marked"]]
            if not chosen:
                one = at(index)
                chosen = [one] if one is not None else []
            if not chosen:
                return None
            count = len(chosen)
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Delete Responses",
                message=f"Delete {_noun(count)} to {title} on {profile.name}? They go to the "
                "Trash in BITS Accessible Forms.",
                yes_label=f"Delete {count}",
            ):
                return None
            ids = [r.id for r in chosen]
            self.site_work(  # type: ignore[attr-defined]
                f"deleting responses on {profile.name}",
                lambda: bs.delete_responses(api, ids),
                lambda n: self.host.announce(f"{_noun(n)} moved to the Trash on {profile.name}."),
            )
            live[:] = [r for r in live if r.id not in ids]
            state["marked"].difference_update(ids)
            return rows()

        def toggle_count(_index: int | None) -> object:
            store = self.form_sites()  # type: ignore[attr-defined]
            fresh = store.get(profile.id) or profile
            turned = not getattr(fresh, "announce_new_responses", True)
            store.upsert(replace(fresh, announce_new_responses=turned))
            from quill.core.wordpress import sites as st

            st.save_sites(store, self.forms_data_dir())  # type: ignore[attr-defined]
            self.host.announce(
                f"QUILL will {'now' if turned else 'no longer'} say how many new responses "
                f"there are when you first use {profile.name} in a session."
            )
            return None

        actions = [
            dlg.Action("&Read", "Read the selected response, one answer a line.", read),
            dlg.Action("&View...", "List, or group by date or by place.", view, needs_row=False),
            dlg.Action(
                "&Find...", "Show only responses with some words in them.", find, needs_row=False
            ),
            dlg.Action("Mar&k", "Mark or unmark the selected response, to delete several.", mark),
            dlg.Action(
                "Export to &CSV...",
                "Save the responses shown as a CSV file, where you choose.",
                export_csv,
                needs_row=False,
            ),
            dlg.Action(
                "Open as &Table...",
                "Save the responses shown as CSV where you choose, and open it as a table.",
                open_table,
                needs_row=False,
            ),
            dlg.Action(
                "Export to &Word...",
                "Save the selected response, or all of those shown, as a Word document.",
                export_word,
                needs_row=False,
            ),
            dlg.Action(
                "Su&mmarise...",
                "Ask your chosen AI for a summary. It asks first, and says how many it sends.",
                summarise,
                needs_row=False,
            ),
            dlg.Action("&Delete...", "Delete the marked responses, or the selected one.", delete),
            dlg.Action(
                "Say &New Count",
                "Turn on or off the count of new responses said when you first use this site.",
                toggle_count,
                needs_row=False,
            ),
        ]
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Responses to {title}",
            purpose=f"{_noun(len(live))} to {title} on {profile.name}, newest first. They stay "
            "on this computer only while this window is open.",
            list_label="&Responses:",
            list_help="Each response: its number, when it was sent, who sent it and the form. "
            "Press Enter to read one.",
            rows=rows(),
            actions=actions,
            on_enter=read,
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # exports: only where the person chooses

    def _export_responses_csv(
        self, title: str, chosen: list[bs.Response], labels: dict[str, str], *, open_after: bool
    ) -> None:
        if not chosen:
            self.host.announce("There are no responses to export.")
            return
        target = rdlg.save_as(
            self.host.parent,
            self.host.show_modal,
            title="Export Responses to CSV",
            name=f"{title} responses.csv",
            wildcard=CSV_WILDCARD,
        )
        if target is None:
            return
        if target.suffix.lower() != ".csv":
            target = target.with_name(target.name + ".csv")
        try:
            # A byte-order mark, so Excel reads the file as UTF-8.
            write_text_atomic(target, rs.csv_text(chosen, labels), encoding="utf-8-sig")
        except OSError as exc:
            self.host.announce(f"QUILL could not save {target.name}: {exc.strerror or exc}.")
            return
        self.host.announce(f"Saved {_noun(len(chosen))} to {target.name}.")
        if open_after:
            self.host.open_path(Path(target))

    def _export_responses_word(
        self,
        title: str,
        chosen: list[bs.Response],
        labels: dict[str, str],
        selected: bs.Response | None,
    ) -> None:
        if not chosen:
            self.host.announce("There are no responses to export.")
            return
        which = chosen
        if selected is not None and len(chosen) > 1:
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Export to Word",
                prompt="&Export:",
                rows=[f"Response {selected.id} only", f"All {_noun(len(chosen))} shown"],
                initial=0,
                help_text="One response, or every response the window is showing.",
            )
            if picked is None:
                return
            which = [selected] if picked == 0 else chosen
        elif selected is not None:
            which = [selected]
        name = f"{title} response {which[0].id}" if len(which) == 1 else f"{title} responses"
        target = rdlg.save_as(
            self.host.parent,
            self.host.show_modal,
            title="Export Responses to Word",
            name=name + ".docx",
            wildcard=WORD_WILDCARD,
        )
        if target is None:
            return
        if target.suffix.lower() != ".docx":
            target = target.with_name(target.name + ".docx")
        from quill.core.forms import export_word as ew

        laid_out = [(f"Response {r.id}, sent {rs.sent_at(r)}", rs.pairs(r, labels)) for r in which]
        try:
            ew.write_responses(f"Responses to {title}", laid_out, target)
        except (OSError, ew.FormWordExportError) as exc:
            self.host.announce(f"QUILL could not save {target.name}: {exc}".rstrip(".") + ".")
            return
        self.host.announce(f"Saved {_noun(len(which))} to {target.name}.")


__all__ = ["FormsResponsesCommands"]
