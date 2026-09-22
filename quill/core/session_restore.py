"""What to do about the documents that were open last time.

Both editors have reopened last session's files since they shipped, and both did
it **silently**: a boolean said yes or no, four windows appeared, and a file that
had gone was skipped without a word. That is defensible for one file and wrong
for four -- four windows appearing unbidden is four things to identify before you
can start work, and the one you actually wanted is not necessarily the first.
QuillLite's crash-recovery prompt was written for exactly that reason and the
session list never got the same treatment.

So this module answers three questions, all of them wx-free so both editors get
the same answers:

* **Is this a case worth asking about?** (:func:`should_ask`) One file that is
  still where it was needs no conversation. Three do, and so does one that has
  moved, because "it did not reopen" and "it reopened and you have not found it
  yet" sound identical to somebody who cannot see the screen.
* **What is in the list?** (:func:`read_entries`) Including the entries whose
  files are gone, which the silent path dropped on the floor. A file deleted on
  purpose is not news; a file that *moved* is, and neither editor could tell you.
* **What do I say afterwards?** (:func:`describe_opened` and friends) A count is
  the one thing a listener cannot get by exploring the screen.

**Forgetting is not deleting.** :func:`forget` drops entries from the remembered
list and touches nothing on disk -- that is the whole of it, and the wording in
the dialog says so plainly rather than warning about it. A warning on a harmless
action is how people learn to click through the warnings that matter (decided
with Jeff, 2026-09-19).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ASK_ALWAYS",
    "ASK_MODES",
    "ASK_MODE_LABELS",
    "ASK_NEVER",
    "ASK_WHEN_IT_MATTERS",
    "A_CROWD",
    "SessionEntry",
    "describe_forgotten",
    "describe_opened",
    "describe_session_plan",
    "forget",
    "missing",
    "openable",
    "read_entries",
    "should_ask",
    "summarise",
]

#: Ask every time there is anything to ask about.
ASK_ALWAYS = "always"
#: Ask only when the answer is not obvious. The default: see :func:`should_ask`.
ASK_WHEN_IT_MATTERS = "when_it_matters"
#: Never ask -- reopen everything, which is what both editors did until now.
ASK_NEVER = "never"

#: Every value the setting takes, in the order a chooser should show them.
ASK_MODES: tuple[str, ...] = (ASK_ALWAYS, ASK_WHEN_IT_MATTERS, ASK_NEVER)

#: How each value is worded to a person. One table, so the two editors cannot
#: word the same choice two ways -- the same rule ``ACTION_FEEDBACK_LABELS``
#: follows for its enum.
ASK_MODE_LABELS: dict[str, str] = {
    ASK_ALWAYS: "Always ask which documents to reopen",
    ASK_WHEN_IT_MATTERS: "Ask when it matters (several documents, or one that has moved)",
    ASK_NEVER: "Never ask, just reopen them",
}

#: Three is a crowd. Two windows you can identify by arrowing between them; the
#: cost of the third is not one more window, it is having to build a map first.
A_CROWD = 3


@dataclass(frozen=True, slots=True)
class SessionEntry:
    """One remembered document, and whether it is still where it was."""

    #: The path as it was remembered, kept verbatim so forgetting can match it.
    path: str
    #: Whether a readable file is at that path right now.
    exists: bool

    @property
    def name(self) -> str:
        """The file name alone, which is how somebody refers to it out loud."""
        return Path(self.path).name or self.path

    @property
    def label(self) -> str:
        """One row of the list: the name, the full path, and the bad news if any.

        The name leads because that is what the person is looking for, and the
        full path follows because two files called ``notes.md`` in two folders is
        the ordinary case, not the exotic one.
        """
        if self.exists:
            return f"{self.name}  —  {self.path}"
        return f"{self.name}  —  {self.path}  (the file is no longer there)"


def read_entries(paths: object) -> tuple[SessionEntry, ...]:
    """The remembered list, each entry told whether its file is still there.

    Tolerant of what it is handed: the setting is a list of strings on disk and a
    damaged one must not stop a launch. Anything that is not a usable path is
    dropped, and a path that cannot even be tested (a permission error on the
    folder, a name the platform rejects) counts as missing rather than raising --
    the session list is a convenience, and no answer it can give is worth failing
    to start the editor over.
    """
    if not isinstance(paths, (list, tuple)):
        return ()
    entries: list[SessionEntry] = []
    seen: set[str] = set()
    for raw in paths:
        text = str(raw).strip() if raw is not None else ""
        if not text or text in seen:
            continue
        seen.add(text)
        try:
            exists = Path(text).is_file()
        except OSError:
            exists = False
        entries.append(SessionEntry(text, exists))
    return tuple(entries)


def openable(entries: tuple[SessionEntry, ...]) -> tuple[SessionEntry, ...]:
    """The entries something could actually open."""
    return tuple(entry for entry in entries if entry.exists)


def missing(entries: tuple[SessionEntry, ...]) -> tuple[SessionEntry, ...]:
    """The entries whose files have gone."""
    return tuple(entry for entry in entries if not entry.exists)


def should_ask(
    entries: tuple[SessionEntry, ...],
    *,
    mode: str = ASK_WHEN_IT_MATTERS,
    crowd: int = A_CROWD,
) -> bool:
    """Whether to put the chooser up, given the list and the preference.

    ``ASK_WHEN_IT_MATTERS`` asks on either of two triggers, and both are about
    the listener rather than the file count for its own sake:

    * **A crowd.** Three or more windows is a map to build before any work.
    * **Anything missing.** A file that has moved is the one case where silence
      is actively misleading: nothing was said, nothing appeared, and there is no
      way to tell that from "it opened and I have not found it".

    An empty list is never worth asking about, whatever the mode says.
    """
    if not entries:
        return False
    if mode == ASK_NEVER:
        return False
    if mode == ASK_ALWAYS:
        return True
    return len(entries) >= crowd or bool(missing(entries))


def forget(entries: tuple[SessionEntry, ...], paths: object) -> tuple[str, ...]:
    """The remembered list with *paths* dropped. Touches nothing on disk.

    Matching is on the remembered string, not on a resolved path: the entry is
    what the user is looking at in the list, and resolving could quietly fail to
    match the row they ticked (a substituted drive letter, a path that no longer
    resolves because the file is gone -- which is exactly the row most likely to
    be forgotten).
    """
    drop = (
        {str(path) for path in paths} if isinstance(paths, (list, tuple, set, frozenset)) else set()
    )
    return tuple(entry.path for entry in entries if entry.path not in drop)


def summarise(entries: tuple[SessionEntry, ...]) -> str:
    """The one sentence that opens the chooser, counts first.

    Names the problem if there is one. "Four documents" and "four documents, one
    of which has gone" want different answers, and the second fact is invisible
    until somebody arrows the whole list.
    """
    if not entries:
        return "Nothing was open last time."
    total = len(entries)
    noun = "document" if total == 1 else "documents"
    gone = len(missing(entries))
    if not gone:
        return f"{total} {noun} from last time."
    if gone == total:
        return f"{total} {noun} from last time, and none of the files are there any more."
    were = "is" if gone == 1 else "are"
    return f"{total} {noun} from last time, {gone} of which {were} no longer there."


def describe_opened(opened: int, total: int) -> str:
    """What to say after opening. Never silent, even when nothing opened.

    "Opened none of them" is a result; saying nothing is indistinguishable from a
    command that did not run.
    """
    if total <= 0:
        return "Nothing to reopen."
    if opened <= 0:
        return f"Opened none of the {total}."
    if opened == total:
        noun = "document" if total == 1 else "documents"
        return f"Reopened all {total} {noun}."
    return f"Reopened {opened} of {total}."


def describe_session_plan(
    entries: tuple[SessionEntry, ...],
    checked: tuple[bool, ...],
) -> str:
    """The whole window as a paragraph, kept in step with the checkboxes.

    The recovery chooser's twin (``quill/core/recovery_triage.py``), and it
    exists for the same reason: a list of checkboxes answers "what is here" one
    row at a time and never answers "what happens when I press the button".
    Sighted users assemble that by glancing down the list; by ear it costs a
    pass through every row, repeated after every tick. So it is written out and
    rewritten whenever a box changes.
    """
    lines: list[str] = []
    ticked = [entry for entry, on in zip(entries, checked, strict=False) if on]
    gone = missing(entries)

    lines.append(summarise(entries))
    lines.append("")
    for index, entry in enumerate(entries, start=1):
        on = checked[index - 1] if index - 1 < len(checked) else False
        mark = "Ticked" if on else "Not ticked"
        lines.append(f"{index}. {mark}. {entry.label}")
    lines.append("")

    openable_ticked = [entry for entry in ticked if entry.exists]
    lines.append("If you press a button now:")
    if openable_ticked:
        names = ", ".join(entry.name for entry in openable_ticked)
        lines.append(f"  Open Checked reopens {len(openable_ticked)}: {names}.")
    else:
        lines.append("  Open Checked opens nothing: no row that still has a file is ticked.")
    skipped = [entry for entry in ticked if not entry.exists]
    if skipped:
        names = ", ".join(entry.name for entry in skipped)
        lines.append(
            f"  {len(skipped)} ticked cannot be opened, because the files have gone: {names}."
        )
    still_there = [entry for entry in entries if entry.exists]
    lines.append(f"  Open All reopens the {len(still_there)} whose files are still there.")
    if ticked:
        lines.append(
            f"  Forget Checked removes {len(ticked)} from this list. "
            "No file is touched -- only what is offered next time."
        )
    else:
        lines.append("  Forget Checked does nothing: no rows are ticked.")
    lines.append(f"  Clear the List forgets all {len(entries)}. Again, no file is touched.")
    if gone:
        verb = "is" if len(gone) == 1 else "are"
        lines.append(
            f"  {len(gone)} of these files {verb} no longer where they were, which "
            "is what Forget is usually for."
        )
    lines.append("  Not Now changes nothing. The same list is offered next time.")
    return "\n".join(lines)


def describe_forgotten(forgotten: int, remaining: int) -> str:
    """What to say after forgetting, including that the files are still there.

    The reassurance is part of the sentence rather than a separate confirmation
    step: it is true, it is short, and it is the thing somebody would otherwise
    have to go and check.
    """
    if forgotten <= 0:
        return "Nothing was forgotten."
    noun = "document" if forgotten == 1 else "documents"
    kept = "The list is empty now." if remaining <= 0 else f"{remaining} still remembered."
    return f"Forgot {forgotten} {noun}. {kept} The files themselves are untouched."
