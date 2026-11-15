"""Gravity Forms entries in the WordPress Workbench: notes, flags, notifications (10B.3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
(through :class:`quill.ui.wordpress_workbench_commands.WorkbenchRowCommands`):

- **Notes** (Ctrl+Alt+N): an entry's notes, oldest first, in a preview whose
  button adds one; the new note is signed as the connected account.
- **Star or Unstar** (Ctrl+Alt+F) and **Mark Read or Unread** (Ctrl+Alt+U):
  each selected entry read again and sent whole, Ctrl+Z puts the flag back.
- **Resend Notifications** (Ctrl+Alt+I): the form's notifications with the
  people each would reach for this entry, checked, then previewed, then sent.
- **Properties**: a Gravity Forms entry's sheet shows its notes, and its
  answers, Starred and Read save through the same whole-entry write. Changed
  answers are previewed old and new, checked against the response's
  ``date_updated`` and their own values just before
  (:mod:`quill.core.wordpress.workbench_gravity_answers`), and Ctrl+Z sends
  the old answers back.

:meth:`gravity_refusal` is the window's check before any of these runs: a
Gravity Forms row, and the Gravity Forms permission, which an administrator
holds as ``gform_full_access``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_forms_site as qaf_site
from quill.core.wordpress import workbench_gravity as gravity
from quill.core.wordpress import workbench_gravity_answers as gfa
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_gravity_actions import GRAVITY_ONLY, NEEDS, command
from quill.core.wordpress.workbench_permissions import tier_allowed
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

#: Gravity Forms rows that answer on a QUILL Accessible Forms response too.
_QAF_TOO = frozenset({command("toggle_starred"), command("toggle_read")})

__all__ = ["WorkbenchGravityEntryCommands"]

_FLAG_WORDS = {
    "is_starred": ("Starred", "Unstarred"),
    "is_read": ("Marked read", "Marked unread"),
}


def _ro(key: str, label: str, kind: FieldKind = FieldKind.TEXT) -> FieldSpec:
    return FieldSpec(key, label, kind, readonly=True, help=f"{label}, as Gravity Forms says it.")


GRAVITY_ENTRY_SHEET = SheetSpec(
    "form_entry",
    "Gravity Forms Entry",
    (
        PageSpec(
            "general",
            "General",
            (
                _ro("id", "Entry number"),
                _ro("form", "Form"),
                _ro("status", "Status"),
                _ro("date_created", "Received"),
                _ro("date_updated", "Last changed"),
                _ro("source_url", "Sent from", FieldKind.LINK),
                FieldSpec(
                    "is_starred",
                    "Starred",
                    FieldKind.CHECK,
                    help="Star an entry to find it again. Saving sends the whole entry back.",
                ),
                FieldSpec(
                    "is_read",
                    "Read",
                    FieldKind.CHECK,
                    help="Whether the entry has been read in Gravity Forms.",
                ),
            ),
        ),
        PageSpec("answers", "Answers", (_ro("answers", "Answers", FieldKind.MULTILINE),)),
        PageSpec("notes", "Notes", (_ro("notes", "Notes", FieldKind.MULTILINE),)),
    ),
)
"""A Gravity Forms entry's Properties; :func:`_entry_sheet` makes its answers editable."""


def _entry_sheet(answers: list[tuple[str, str, str]]) -> SheetSpec:
    """The entry sheet with one editable field an answer: (field id, label, value)."""
    if not answers:
        return GRAVITY_ENTRY_SHEET
    counts: dict[str, int] = {}
    for _fid, label, _value in answers:
        counts[label] = counts.get(label, 0) + 1
    fields = tuple(
        FieldSpec(
            gfa.answer_key(fid),
            label if counts[label] == 1 else f"{label} (field {fid})",
            FieldKind.MULTILINE if "\n" in value or len(value) > 80 else FieldKind.TEXT,
            help=(
                f"The visitor's answer to {label}. Saving previews the change, then sends the "
                "whole response back; Ctrl+Z puts the old answer back."
            ),
        )
        for fid, label, value in answers
    )
    pages = tuple(
        PageSpec("answers", "Answers", fields) if page.key == "answers" else page
        for page in GRAVITY_ENTRY_SHEET.pages
    )
    return SheetSpec(GRAVITY_ENTRY_SHEET.kind, GRAVITY_ENTRY_SHEET.title, pages)


def _plain_sheet(row: WbRow, fresh: dict[str, Any]) -> SheetSpec:
    fields = tuple(
        _ro(name, name.replace("_", " ").capitalize(), FieldKind.MULTILINE)
        for name in fresh
        if not name.startswith("_")
    )
    return SheetSpec(
        row.kind,
        row.kind.replace("_", " ").title(),
        (PageSpec("general", "General", fields or (_ro("id", "Number"),)),),
    )


class WorkbenchGravityEntryCommands:
    """Notes, Star, Read and Resend Notifications on Gravity Forms entries."""

    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    selected_rows: Callable[[], list[WbRow]]
    history: Any
    parent: Any
    access_for: Callable[[str], Any]
    account_for: Callable[[str], Any]

    # -- the check before running ---------------------------------------------------

    def gravity_refusal(self, command_id: str, row: WbRow) -> str:
        """Why a Gravity Forms command may not run on *row* ("" when it may)."""
        delete_feed = row.kind == "gravity_feed" and command_id == command("delete_permanently")
        if command_id not in GRAVITY_ONLY and not delete_feed:
            return ""
        if row.subkind == "qaf" and command_id in _QAF_TOO:
            return ""  # Star and Mark Read answer on QAF responses too (Package 13)
        if row.subkind != "gravity":
            return (
                "That is a Gravity Forms command. Choose a Gravity Forms form, entry or feed; "
                "QUILL Accessible Forms keeps no notes, feeds or notifications."
            )
        need = "edit_forms" if delete_feed else NEEDS.get(command_id, "")
        if not need:
            return ""
        capability, words = gravity.CAPABILITIES[need]
        account = self.account_for(row.site)
        if gravity.gravity_can(account, capability):
            return ""
        return (
            f"{words} needs the Gravity Forms permission {capability.replace('_', ' ')}. "
            f"You are {account.role_name} on {row.site}."
        )

    def _entries(self, row: WbRow | None) -> list[WbRow]:
        rows = self.selected_rows() or ([row] if row is not None else [])
        return [r for r in rows if r.kind == "form_entry" and r.subkind == "gravity"]

    def _one_entry(self, row: WbRow | None) -> WbRow | None:
        rows = self._entries(row)
        if not rows:
            self.say("Choose a Gravity Forms entry first.")
            return None
        return rows[0]

    def _may_write(self, site: str, need: str) -> str:
        if not tier_allowed(Tier.WRITE, self.access_for(site)):
            return f"Workbench access on {site} only reads. Site > Workbench Access changes it."
        capability, words = gravity.CAPABILITIES[need]
        account = self.account_for(site)
        if gravity.gravity_can(account, capability):
            return ""
        return f"{words} needs the Gravity Forms permission {capability.replace('_', ' ')}."

    # -- notes ----------------------------------------------------------------------

    def do_entry_notes(self, _ref: Any, row: WbRow | None) -> None:
        entry = self._one_entry(row)
        if entry is None:
            return
        api = self.ctx(entry.site).api

        def shown(notes: list[gravity.Note]) -> None:
            lines = gravity.note_lines(notes)
            count = len(notes)
            summary = f"{count} note{'s' if count != 1 else ''} on {entry.title} on {entry.site}."
            why_not = self._may_write(entry.site, "edit_notes")
            if why_not:
                dlg.show_report(
                    self.parent,
                    self.show_modal,
                    title=f"Notes - {entry.title}",
                    text="\n".join([summary, *lines, why_not]),
                    help_text="This entry's notes, oldest first, as Gravity Forms keeps them.",
                )
                return
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Notes - {entry.title}",
                summary=summary,
                lines=lines,
                yes="Add a Note...",
            ):
                return
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Add a Note - {entry.title}",
                prompt="&Note:",
                help_text=(
                    f"A note on this entry, kept by Gravity Forms on {entry.site} and signed "
                    "as you. Visitors never see it."
                ),
                multiline=True,
            )
            if not text or not text.strip():
                return
            self._add_note(entry, text.strip())

        self.background(
            f"reading notes on {entry.title}",
            lambda: gravity.read_notes(api, entry.object_id),
            shown,
        )

    def _add_note(self, entry: WbRow, text: str) -> None:
        ctx = self.ctx(entry.site)

        def added(answer: Any) -> None:
            said = f"Added a note to {entry.title} on {entry.site}."
            note_id = answer.get("id") if isinstance(answer, dict) else answer
            undo = None
            if isinstance(note_id, (int, str)) and str(note_id).isdigit():
                undo = lambda: (  # noqa: E731
                    ctx.api.delete(f"{gravity.NS}/notes/{note_id}"),
                    f"Removed the note from {entry.title}.",
                )[1]
            self.history.record(Change(f"{entry.site}: {entry.title}", said, undo=undo))
            self.say(said)

        self.background(
            "adding a note",
            lambda: gravity.add_note(ctx.api, entry.object_id, text, ctx.account),
            added,
        )

    # -- starred and read -----------------------------------------------------------

    def _toggle_flag(self, row: WbRow | None, flag: str) -> None:
        chosen = self.selected_rows() or ([row] if row is not None else [])
        plugin = next((r.subkind for r in chosen if r.kind == "form_entry"), "")
        rows = [r for r in chosen if r.kind == "form_entry" and r.subkind == plugin]
        if plugin not in ("gravity", "qaf") or not rows:
            self.say("Choose a Gravity Forms or QUILL Accessible Forms response first.")
            return
        setter = qaf_site.set_entry_flag if plugin == "qaf" else gravity.set_entry_flag
        named = "QUILL Accessible Forms" if plugin == "qaf" else "Gravity Forms"
        site = rows[0].site
        if any(r.site != site for r in rows):
            self.say("Change entries from one site at a time.")
            return
        on = not gravity.truthy(rows[0].raw.get(flag, 0))
        api = self.ctx(site).api

        def work() -> dict[str, bool]:
            return {r.route: setter(api, r.route, flag, on) for r in rows}

        def done(before: dict[str, bool]) -> None:
            word = _FLAG_WORDS[flag][0 if on else 1]
            count = len(rows)
            said = f"{word} {count} entr{'ies' if count != 1 else 'y'} on {site}."
            self.history.record(
                Change(
                    f"{site}: {count} {named} entries",
                    said,
                    undo=lambda: (
                        [setter(api, route, flag, was) for route, was in before.items()],
                        f"Put {count} entr{'ies' if count != 1 else 'y'} back as they were.",
                    )[1],
                )
            )
            self.say(said)
            self.refresh()

        self.background("changing entries", work, done)

    def do_toggle_starred(self, _ref: Any, row: WbRow | None) -> None:
        self._toggle_flag(row, "is_starred")

    def do_toggle_read(self, _ref: Any, row: WbRow | None) -> None:
        self._toggle_flag(row, "is_read")

    # -- notifications --------------------------------------------------------------

    def do_resend_notifications(self, _ref: Any, row: WbRow | None) -> None:
        entry = self._one_entry(row)
        if entry is None:
            return
        api = self.ctx(entry.site).api
        form_id = str(entry.raw.get("form_id", "") or "")

        def read() -> list[gravity.Notification]:
            form = api.get(f"{gravity.NS}/forms/{form_id}")
            fresh = api.get(entry.route)
            if not isinstance(form, dict):
                return []
            return gravity.entry_notifications(
                form, fresh if isinstance(fresh, dict) else entry.raw
            )

        def chosen(found: list[gravity.Notification]) -> None:
            if not found:
                self.say(f"The form behind {entry.title} has no notifications to send.")
                return
            picked = wdlg.ask_checks(
                self.parent,
                self.show_modal,
                title=f"Resend Notifications - {entry.title}",
                prompt="&Notifications to send again:",
                rows=[n.line for n in found],
                checked=[
                    i for i, n in enumerate(found) if n.active and n.event == "form_submission"
                ],
                help_text=(
                    "The form's notifications, with who each one reaches for this entry. "
                    "Checked ones are sent again."
                ),
            )
            if not picked:
                return
            notes = [found[i] for i in picked]
            count = len(notes)
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Resend Notifications",
                summary=(
                    f"Send {count} notification{'s' if count != 1 else ''} again for "
                    f"{entry.title} on {entry.site}?"
                ),
                lines=[
                    *(n.line for n in notes),
                    "Each person listed gets the email again, as if the form had just been sent.",
                ],
                yes="Resend",
            ):
                return

            def sent(ids: list[str]) -> None:
                names = [n.name for n in notes if n.id in ids] or [n.name for n in notes]
                if ids:
                    said = (
                        f"Gravity Forms sent {len(ids)} notification{'s' if len(ids) != 1 else ''} "
                        f"again for {entry.title}: {', '.join(names)}."
                    )
                else:
                    said = (
                        f"Gravity Forms sent none for {entry.title}. A notification's own "
                        "conditions may not match this entry."
                    )
                self.history.record(Change(f"{entry.site}: {entry.title}", said))
                self.say(said)

            self.background(
                "resending notifications",
                lambda: gravity.resend_notifications(api, entry.object_id, [n.id for n in notes]),
                sent,
            )

        self.background(f"reading the notifications for {entry.title}", read, chosen)

    # -- Properties -----------------------------------------------------------------

    def gravity_sheet(
        self, row: WbRow
    ) -> tuple[SheetSpec, dict[str, Any], dict[str, Any], Any, dict[str, Any]]:
        """Off the UI thread: a Gravity Forms entry's, feed's or result's sheet."""
        api = self.ensure(self.ctx(row.site)).api
        fresh: dict[str, Any] = dict(row.raw)
        if row.route:
            got = api.get(row.route)
            fresh = dict(got) if isinstance(got, dict) else fresh
        if row.kind != "form_entry":
            values = {k: v if isinstance(v, (str, int, bool)) else str(v) for k, v in fresh.items()}
            return _plain_sheet(row, fresh), values, fresh, {}, {}
        try:
            notes = gravity.note_lines(gravity.read_notes(api, row.object_id))
        except Exception as exc:  # noqa: BLE001 - notes are a page, not the sheet
            notes = [getattr(exc, "plain", "") or "Gravity Forms did not return the notes."]
        try:
            form = api.get(f"{gravity.NS}/forms/{fresh.get('form_id', '')}")
        except Exception:  # noqa: BLE001 - labels are words, not the sheet
            form = {}
        labels = gfa.answer_labels(form if isinstance(form, dict) else {})
        answers = [
            (fid, labels.get(fid, f"Field {fid}"), "" if fresh[fid] is None else str(fresh[fid]))
            for fid in gfa.answer_ids(fresh)
        ]
        values: dict[str, Any] = {
            "id": str(fresh.get("id", "")),
            "form": row.cell("form"),
            "status": str(fresh.get("status", "") or ""),
            "date_created": str(fresh.get("date_created", "") or ""),
            "date_updated": str(fresh.get("date_updated", "") or ""),
            "source_url": str(fresh.get("source_url", "") or ""),
            "is_starred": gravity.truthy(fresh.get("is_starred", 0)),
            "is_read": gravity.truthy(fresh.get("is_read", 0)),
            "answers": "No answers.",
            "notes": "\n".join(notes),
            **{gfa.answer_key(fid): value for fid, _label, value in answers},
        }
        return _entry_sheet(answers), values, fresh, {}, {}

    def gravity_entry_save(self, row: WbRow, state: Any) -> bool:
        """Save a Gravity Forms entry's answers, Starred and Read through the whole-entry write."""
        pending = list(state.pending())
        changes = [c for c in pending if c.key in ("is_starred", "is_read")]
        edits = [c for c in pending if gfa.field_of(c.key)]
        if not changes and not edits:
            self.say("Nothing changed on this entry.")
            return True
        why_not = self._may_write(row.site, "edit_entries")
        if why_not:
            self.say(why_not)
            return False
        seen = {gfa.field_of(c.key): str(c.before or "") for c in edits}
        wanted = {gfa.field_of(c.key): str(c.after or "") for c in edits}
        if edits and not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Change Answers",
            summary=(
                f"Change {len(edits)} answer{'s' if len(edits) != 1 else ''} in {row.title} on "
                f"{row.site}? Gravity Forms keeps no earlier version, so Ctrl+Z is the way back."
            ),
            lines=[
                f"{c.label}: {seen[gfa.field_of(c.key)] or '(empty)'} becomes "
                f"{wanted[gfa.field_of(c.key)] or '(empty)'}"
                for c in edits
            ],
            yes="Change",
        ):
            return False
        api = self.ctx(row.site).api
        updated = str(state.loaded.get("date_updated", "") or "")

        def work() -> tuple[dict[str, str], list[tuple[str, bool]]] | EditConflict:
            try:  # answers first: a flag's write would move date_updated on
                was = gfa.set_answers(
                    api, row.route, seen=seen, changed=wanted, seen_updated=updated
                )
            except EditConflict as exc:
                return exc
            flags = [
                (c.key, gravity.set_entry_flag(api, row.route, c.key, bool(c.after)))
                for c in changes
            ]
            return was, flags

        def undo(was: dict[str, str], flags: list[tuple[str, bool]]) -> str:
            gfa.set_answers(api, row.route, seen=wanted, changed=was)
            for key, flag_was in flags:
                gravity.set_entry_flag(api, row.route, key, flag_was)
            return f"Put {row.title} back as it was."

        def done(result: tuple[dict[str, str], list[tuple[str, bool]]] | EditConflict) -> None:
            if isinstance(result, EditConflict):
                self.say(str(result.args[0]))
                return
            was, flags = result
            count = len(edits) + len(changes)
            noun = "change" if count == 1 else "changes"
            said = f"Saved {count} {noun} to {row.title} on {row.site}."
            self.history.record(
                Change(f"{row.site}: {row.title}", said, undo=lambda: undo(was, flags))
            )
            self.say(said)
            self.refresh()

        self.background(f"saving {row.title}", work, done)
        return True
