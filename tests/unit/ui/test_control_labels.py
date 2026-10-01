"""GATE-CTLLABEL: a control announces by the static text built before it.

``SetName`` is not an accessible name on wxMSW. The MSAA/UIA bridge NVDA and
JAWS read takes a plain control's name from the ``wx.StaticText`` created
immediately before it in z-order, and z-order is creation order. Two edit
fields in ``quill/ui/podcasts/add_podcast_dialog.py`` shipped announcing as bare
"edit" with careful ``SetName`` calls on both of them (``ba69898``).

These tests do two separate jobs, and both are needed.

The **ratchet** tests hold the tree: no new silent control may land, and the
backlog of 165 that existed when the gate was written may only shrink.

The **detector** tests hold the gate itself, against source snippets of the
exact shapes it was written for. A gate that has stopped detecting anything
passes, silently and forever, and looks like success -- which is the same class
of mistake as a name nobody hears.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

from quill.tools.check_control_labels import (
    SNAPSHOT_PATH,
    apply_snapshot,
    counts,
    grandfathered_keys,
    high_water_mark,
    load_snapshot,
    new_offenders,
    offenders,
    worst_files,
)
from quill.tools.control_label_scan import (
    LABELLED,
    NAMED_ONLY,
    UNLABELLED,
    classify_source,
    safe_parse,
    scan_control_sites,
)

_REGEN = "Regenerate with 'python -m quill.tools.check_control_labels --write'."


@cache
def _live() -> tuple:
    """The whole-tree scan, once per session.

    Cached because ``source_cache`` releases its ASTs when each scan's scope
    closes, so six tests meant six full walks of ``quill/ui`` and
    ``quill/apps`` -- 42 seconds, and the note in CLAUDE.md about whole-tree
    gate tests brushing pytest's timeout on a loaded machine is not
    hypothetical. The tree does not change during a run.
    """
    return tuple(apply_snapshot(scan_control_sites(), load_snapshot()))


def test_no_control_ships_with_a_name_no_screen_reader_will_read() -> None:
    """A new control without a preceding static text must fail the build.

    This is the whole gate. The bug it stops is not "somebody forgot" -- it is
    "somebody wrote the name, the reviewer read the name, and the listener heard
    a bare role", which nothing else in the tree can see: the existing
    ``accessible_name_audit`` counts a bare ``SetName`` as named, because it was
    written for macOS VoiceOver where the window name really is the name.
    """
    snapshot = load_snapshot()
    fresh = new_offenders(offenders(_live()), snapshot)
    listing = "\n".join(f"  {site.key}  ({site.qualname})" for site in fresh)
    assert not fresh, (
        f"{len(fresh)} control(s) carry no label a screen reader can see. On "
        "wxMSW the accessible name comes from the wx.StaticText constructed "
        "immediately BEFORE the control -- not from SetName, and not from the "
        "sizer. Add a real label built before the control, or classify the "
        f"site in {SNAPSHOT_PATH.name} under 'reviewed' with a reason.\n{listing}"
    )


def test_the_grandfathered_backlog_never_grows() -> None:
    """The backlog is a one-way ratchet, like the module size budgets.

    Two halves, because either alone can be slipped past. The live count must
    fit inside the reviewed ceiling, so a new offender cannot hide among the old
    ones; and the stored list must not be longer than that ceiling, so nobody
    can quietly append an entry to silence the gate without raising a number a
    reviewer will see in the diff.
    """
    snapshot = load_snapshot()
    stored = grandfathered_keys(snapshot)
    ceiling = high_water_mark(snapshot)
    live = len(offenders(_live()))

    assert len(stored) <= ceiling, (
        f"the grandfathered list holds {len(stored)} entries against a ceiling "
        f"of {ceiling}. Entries were appended without raising 'high_water_mark' "
        f"-- which is the review this ratchet exists to force. {_REGEN}"
    )
    assert live <= ceiling, (
        f"{live} unnamed control(s) live against a grandfathered ceiling of "
        f"{ceiling}. The backlog may only shrink: fix a control rather than "
        f"widening the allowance. {_REGEN}"
    )


def test_every_reviewed_site_states_why_it_is_exempt() -> None:
    """A reviewed exemption without a reason is not a review, it is a silence.

    The reason is the entire value of the classification: "this list's column
    header is its name" is a claim somebody can check, and an empty string is a
    claim nobody can.
    """
    reviewed = load_snapshot().get("reviewed")
    entries = reviewed if isinstance(reviewed, dict) else {}
    empty = sorted(key for key, value in entries.items() if not str(value).strip())
    assert not empty, f"reviewed entries with no reason: {empty}"


def test_the_snapshot_holds_no_duplicate_grandfathered_entry() -> None:
    """A duplicate entry silently widens the allowance by one.

    The ratchet spends allowance per ``(file, control class)``, so a key listed
    twice buys a free offender in that file -- exactly the leak the ceiling
    count is meant to close, and invisible in a 165-line diff.
    """
    stored = grandfathered_keys(load_snapshot())
    duplicates = sorted({key for key in stored if stored.count(key) > 1})
    assert not duplicates, f"duplicated grandfathered entries: {duplicates}"


def test_the_committed_snapshot_is_not_stale() -> None:
    """Every grandfathered entry still names a control that exists.

    Entries that no longer match anything are fixes nobody banked -- the backlog
    reads as 165 when the real number is lower, and the ceiling stops applying
    pressure. This tolerates line drift (the ratchet matches on file and control
    class, not line) and fails only when the file has fewer offenders of that
    kind than the snapshot claims.
    """
    snapshot = load_snapshot()
    stored = grandfathered_keys(snapshot)
    live = offenders(_live())
    slack = len(stored) - len(live)
    assert slack <= 0, (
        f"the grandfathered list is {slack} entr(y/ies) longer than the live "
        f"scan: {len(live)} offenders remain against {len(stored)} entries. "
        f"Bank the fixes so the ceiling keeps applying pressure. {_REGEN}"
    )


def test_the_report_names_the_worst_files_so_a_fixer_knows_where_to_start() -> None:
    """The scorecard has to be actionable, not only correct.

    A gate that prints 165 unsorted lines is a gate whose output gets skipped.
    """
    worst = worst_files(_live(), limit=10)
    assert worst, "no offenders at all -- delete the backlog and this assertion"
    assert len(worst) <= 10
    assert [count for _path, count in worst] == sorted(
        (count for _path, count in worst), reverse=True
    )


# -- the detector itself ---------------------------------------------------


def test_a_field_with_setname_and_no_preceding_label_is_the_reported_bug() -> None:
    """The exact shape that shipped in Add Podcast: a name nobody hears.

    ``named-only`` rather than ``unlabelled`` on purpose. The distinction is
    what makes the report worth reading: somebody has already written the
    sentence, so the fix is to move it into a label, not to invent wording.
    """
    sites = classify_source(
        "def build(self):\n"
        "    self._url = wx.TextCtrl(self.dialog)\n"
        "    self._url.SetName('The podcast feed URL')\n"
    )
    assert [site.status for site in sites] == [NAMED_ONLY]
    assert sites[0].kind == "wx.TextCtrl"


def test_a_field_with_a_static_text_built_before_it_is_labelled() -> None:
    """The fix shape from ``ba69898``: a real label, created first.

    Created first, not merely placed first -- the association is by creation
    order, so a label added to the sizer above a field that was constructed
    earlier still leaves the field silent.
    """
    sites = classify_source(
        "def build(self):\n"
        "    row.Add(wx.StaticText(self.dialog, label='&Feed address:'))\n"
        "    self._url = wx.TextCtrl(self.dialog)\n"
    )
    assert [site.status for site in sites] == [LABELLED]


def test_one_label_cannot_vouch_for_two_controls() -> None:
    """The second field is on its own, which is why Add Podcast had two bugs.

    The combo box in that dialog announced correctly and the two fields below it
    did not. A rule that let a label reach past the control immediately after it
    would have called all three fine.
    """
    sites = classify_source(
        "def build(self):\n"
        "    box.Add(wx.StaticText(self.dialog, label='&Directory:'))\n"
        "    self._source = wx.Choice(self.dialog)\n"
        "    self._query = wx.TextCtrl(self.dialog)\n"
        "    self._query.SetName('Podcast name to search for')\n"
    )
    assert [(site.kind, site.status) for site in sites] == [
        ("wx.Choice", LABELLED),
        ("wx.TextCtrl", NAMED_ONLY),
    ]


def test_a_field_with_neither_a_label_nor_a_name_is_unlabelled() -> None:
    """The plainer half of the bug: it announces as a bare role.

    Kept as its own classification because the two want different fixes and the
    counts want reporting separately -- and because a branch no test exercises
    is a branch that can rot into unreachable code without anybody noticing.
    """
    sites = classify_source("def build(self):\n    ctrl = wx.ComboBox(self.dialog)\n")
    assert [site.status for site in sites] == [UNLABELLED]


def test_a_label_in_another_function_does_not_vouch_for_this_one() -> None:
    """Scope is the enclosing function, deliberately.

    Widening it to the module would let a label in one dialog vouch for a field
    in another, which is how a gate quietly stops finding anything. The cost is
    a false positive on a cross-function form, and that is what the ``reviewed``
    classification is for.
    """
    sites = classify_source(
        "def labels(self):\n"
        "    box.Add(wx.StaticText(self.dialog, label='Host:'))\n"
        "def fields(self):\n"
        "    self.host = wx.TextCtrl(self.dialog)\n"
    )
    assert [site.status for site in sites] == [UNLABELLED]


def test_a_label_helper_counts_as_the_label_it_builds() -> None:
    """``add_label`` then a field is correct, and must not be reported.

    ``StudioPage.add_label`` builds the static text two modules away from the
    pages that call it. Eighteen already-correct fields in
    ``audio_studio/pages_documents.py`` alone read as broken before the scan
    learned to follow it, and a report that sends a fixer to eighteen correct
    files is a report nobody uses twice.
    """
    sites = classify_source(
        "def add_label(self, text):\n"
        "    self.sizer.Add(wx.StaticText(self, label=text))\n"
        "def build(self):\n"
        "    self.add_label('&Source folder:')\n"
        "    self.source = wx.ComboBox(self)\n"
    )
    assert [site.status for site in sites] == [LABELLED]


def test_a_row_factory_labels_the_control_its_lambda_builds() -> None:
    """The other shape that is already correct: label first, factory second.

    ``ssh_dialogs.py`` and the preferences pages both use it, several with a
    comment citing the z-order contract by name. The helper call sorts before
    the lambda's construction, which is also the order Python evaluates them
    and therefore the order wx creates the windows.
    """
    sites = classify_source(
        "def build(self):\n"
        "    def row(label_text, make_ctrl):\n"
        "        grid.Add(wx.StaticText(self.dialog, label=label_text))\n"
        "        return make_ctrl()\n"
        "    self.host = row('Host', lambda: wx.TextCtrl(self.dialog))\n"
    )
    assert [site.status for site in sites] == [LABELLED]


def test_a_helper_that_builds_a_control_of_its_own_is_not_a_label_helper() -> None:
    """``add_ms_spin`` builds a label *and* its spin, so it vouches for nothing.

    The last child such a helper creates is the control, not the label, so
    letting a call to it label the *next* field would be a lie -- and one that
    would hide a real offender behind a correct-looking neighbour.
    """
    sites = classify_source(
        "def add_ms_spin(self, text):\n"
        "    grid.Add(wx.StaticText(self, label=text))\n"
        "    return wx.SpinCtrl(self)\n"
        "def build(self):\n"
        "    self.add_ms_spin('Gap')\n"
        "    self.rate = wx.Slider(self)\n"
    )
    assert [(site.kind, site.status) for site in sites] == [
        ("wx.SpinCtrl", LABELLED),
        ("wx.Slider", UNLABELLED),
    ]


def test_a_button_is_not_audited_because_it_carries_its_own_label() -> None:
    """Scope discipline: the rule does not apply to self-labelling controls.

    A ``wx.Button``, ``wx.CheckBox``, ``wx.RadioButton`` and ``wx.StaticBox``
    announce from their own label, so demanding a static text before them would
    fill the backlog with hundreds of non-problems and bury the real 165.
    """
    sites = classify_source(
        "def build(self):\n"
        "    self.go = wx.Button(self.dialog, label='&Search')\n"
        "    self.opt = wx.CheckBox(self.dialog, label='&Follow redirects')\n"
    )
    assert sites == []


def test_a_constructor_name_keyword_is_a_written_name_too() -> None:
    """``wx.TextCtrl(..., name='Host')`` is just as invisible as SetName.

    wxWidgets stores both in the same place, and the accessibility bridge reads
    neither. Counting only the method call would classify this as
    ``unlabelled`` and lose the fact that the wording already exists.
    """
    sites = classify_source(
        "def build(self):\n    self.host = wx.TextCtrl(self.dialog, name='Host')\n"
    )
    assert [site.status for site in sites] == [NAMED_ONLY]


def test_an_unparseable_file_is_skipped_and_named_rather_than_crashing() -> None:
    """One bad file must not silence the report on the other thirteen hundred.

    This is not hypothetical. The gate's first whole-tree run aborted on a module
    another process was halfway through writing -- on Windows that is a file full
    of NUL bytes, and ``compile`` raises. Reported rather than swallowed, because
    a file the scan could not read is one it cannot vouch for.
    """
    assert safe_parse(Path(__file__)) is not None
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        bad = root / "quill" / "ui" / "half_written.py"
        bad.parent.mkdir(parents=True)
        bad.write_bytes(b"def build(self):\n    ctrl = wx.Tex\x00tCtrl(self)\n")
        good = root / "quill" / "apps" / "fine.py"
        good.parent.mkdir(parents=True)
        good.write_text("def build(self):\n    ctrl = wx.ComboBox(self)\n", encoding="utf-8")

        skipped: list[str] = []
        sites = scan_control_sites(root=root, skipped=skipped)

    assert skipped == ["quill/ui/half_written.py"]
    assert [site.status for site in sites] == [UNLABELLED]


def test_the_live_tree_still_has_labelled_controls_in_the_majority() -> None:
    """A sanity floor on the scan: it must still be classifying, not crashing.

    If a refactor broke ``_wx_class`` or the scan globs, every count would go to
    zero and every ratchet test above would pass. Asserting that the tree is
    mostly fine is the cheapest way to notice that the scan found nothing at
    all.
    """
    tally = counts(_live())
    total = sum(tally.values())
    assert total > 500, f"the scan found only {total} control sites -- it is broken, not clean"
    assert tally[LABELLED] > total // 2
