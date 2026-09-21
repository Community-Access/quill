"""GATE-14: within one window, every access key is claimed exactly once.

EdSharp's ``checkAccessKeysUnique``, imported 2026-08-27. Two controls in a
window sharing an Alt letter means the letter reaches one of them
unreliably -- Windows cycles focus between duplicates instead of pressing --
and nothing announces the loss; the first sweep found 128 such collisions
that had each shipped silently. The scanner and its scoping rules live in
``quill.tools.check_access_keys``.
"""

from __future__ import annotations

from quill.tools import check_access_keys


def test_the_live_tree_has_no_access_key_collisions() -> None:
    collisions = check_access_keys.scan()
    assert collisions == [], "\n".join(str(c) for c in collisions)


def test_mnemonic_extraction() -> None:
    assert check_access_keys.mnemonic_of("&Save") == "S"
    assert check_access_keys.mnemonic_of("Ca&ncel") == "N"
    assert check_access_keys.mnemonic_of("Fish && Chips") == ""
    assert check_access_keys.mnemonic_of("Fish && Chi&ps") == "P"
    assert check_access_keys.mnemonic_of("No key here") == ""
    assert check_access_keys.mnemonic_of("Trailing&") == ""


def test_a_translated_label_is_read_like_a_plain_one() -> None:
    """``label=_("&Save")`` counts, and so does ``label=str(_("&Save"))``.

    Only the bare literal used to. The gap was not academic: a module that
    translates its labels was invisible to this gate control by control, so
    whole windows reported clean while carrying duplicates -- the Chapter
    Workbench had five. The unwrap is shape-based, not name-based, so it
    covers ``_``, ``str(_(...))`` and ``lazy_gettext`` without a list.
    """
    import ast

    def label(source: str) -> str | None:
        return check_access_keys._label_of(ast.parse(source, mode="eval").body)

    assert label('wx.Button(self, label="&Save")') == "&Save"
    assert label('wx.Button(self, label=_("&Save"))') == "&Save"
    assert label('wx.Button(self, label=str(_("&Save")))') == "&Save"
    assert label('wx.StaticText(self, wx.ID_ANY, _("Chapter t&itle:"))') == "Chapter t&itle:"
    assert label("wx.Button(self, label=self._computed())") is None


def test_identical_repeated_labels_do_not_collide() -> None:
    """The same label constructed twice is one control rebuilt, not a clash."""
    sites = [(10, "&Refresh", "R"), (20, "&Refresh", "R")]
    assert check_access_keys._collisions_in_scope("f.py", "D", sites) == []


def test_distinct_labels_on_one_letter_collide() -> None:
    sites = [(10, "&Save", "S"), (20, "&Secret:", "S")]
    collisions = check_access_keys._collisions_in_scope("f.py", "D", sites)
    assert len(collisions) == 1
    assert collisions[0].letter == "S"
