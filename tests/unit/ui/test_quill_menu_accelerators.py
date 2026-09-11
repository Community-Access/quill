"""QUILL's own menu bar: every item reachable, no key wx cannot bind, none twice.

``test_menu_accelerators.py`` has walked Quill Radio's menu bar since 2026-08.
It only ever walked Radio's, and QUILL's bar -- 757 items, the largest in the
family -- was never looked at. It was carrying both faults that gate exists to
catch:

* **A key wx cannot bind.** ``view.split_preview`` was spelled
  ``"Ctrl+Shift+Backslash"``; wx has no name for that key, dropped the whole
  string, and left **View > Preview Side by Side** advertising a chord that
  could never fire. It announced itself only as one line in the startup log --
  "Unrecognized accel key 'Backslash', accel string ignored" -- which is the
  kind of evidence nobody is looking at.
* **A key claimed twice.** ``SIBLING_APP_ACCELERATORS`` moved onto F-keys to
  escape Quill Radio's quick-play favourites and put its third entry on
  ``power.count_occurrences``, so **Search > Count Occurrences** and
  **QuillVille > Open Quill Inkwell** shared Ctrl+Alt+Shift+F3 and one of them
  never fired.

**The third assertion is on as of 2026-09-10**, and two things had to change for
it to be true rather than merely enforced.

*A route is not always an accelerator.* 560 of QUILL's items had no chord and
were never going to get one: the one-level QUILL-key namespace is exhausted and
the plain-chord space went years ago. What they have instead is the **Alt path**
-- ``Alt+F, I, W`` reaches File > Import > Word Document -- advertised in
parentheses rather than after a tab, because wx parses post-tab text as a native
accelerator and an Alt path is not one (the same call #612 recorded for
QUILL-key chords). This gate used to look only for a tab, which is why it scored
44 already-complying QUILL-key items as gaps. It now accepts either.

*Every mnemonic in a popup has to be distinct*, or the path goes nowhere in
particular: Windows answers a duplicated letter by cycling rather than pressing.
There were **119 collisions across 30 popups** and GATE-14 could not see any of
them -- it scopes a ``wx.Dialog``/``wx.Frame`` subclass as one window, and this
menu bar is built across a dozen mixin methods, so every collision fell between
the scopes. The per-popup check below is that hole closed.

Both are held by ``quill/ui/menu_routes.py``, applied at the end of
``_build_menu_bar`` and again wherever a menu is rebuilt outside it. Radio's
fixture and QUILL's can merge now that both bars pass the same three rules; they
are still separate only because building the two frames costs different things.
"""

from __future__ import annotations

import collections
import re

import pytest

wx = pytest.importorskip("wx")

from tests.unit.ui.test_menu_accelerators import _items  # noqa: E402

#: Serialized onto one worker under ``-n --dist loadgroup``: this file uses
#: a real MainFrame: system-wide hotkeys and the screen-reader bridges.
#: See ``pytest_collection_modifyitems`` in ``tests/conftest.py``.
pytestmark = pytest.mark.machine_global

_TAB = chr(9)

#: A route advertised in the label rather than as a native accelerator:
#: "(Alt+F, I, W)", "(QUILL Key + S)", "(Alt+O, F, &R)". Anchored to the end so
#: a title that merely mentions a key in passing does not count.
_PARENTHESISED_ROUTE = re.compile(r"\((?:QUILL Key|Alt|Ctrl|Cmd|Shift)[^()]*\)\s*$")


def _advertises_a_route(label: str) -> bool:
    """Whether *label* tells the reader how to reach this item from the keyboard.

    Either half counts: a native accelerator after a tab, or an Alt path in
    parentheses. Both are global, both are typed rather than arrowed to, and the
    only reason there are two forms is that wx will not parse the second one as
    an accelerator.
    """
    if _TAB in label:
        return bool(label.split(_TAB, 1)[1].strip())
    return bool(_PARENTHESISED_ROUTE.search(label))


def _mnemonic(title: str) -> str:
    """The item's mnemonic letter, or "". ``&&`` is a literal ampersand."""
    index = 0
    while True:
        index = title.find("&", index)
        if index < 0 or index + 1 >= len(title):
            return ""
        if title[index + 1] == "&":
            index += 2
            continue
        return title[index + 1].upper()


@pytest.fixture(scope="module")
def quill_menu_bar():
    app = wx.App()
    from unittest.mock import patch

    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.main_frame import MainFrame

    # Startup runs the silent update check when auto_check_updates is on, which
    # is the shipped default -- so building the frame reaches api.github.com and
    # then lands its callback on a wx.App this fixture has already torn down.
    # A menu bar is not worth a network call; patch the one method rather than
    # reaching into settings, so nothing else about startup changes.
    with patch.object(MainFrame, "check_for_updates", lambda self, **_kwargs: None):
        frame = MainFrame()
    yield frame.frame.GetMenuBar()
    frame.frame.Destroy()
    # Building the frame installs a process-global dialog-transition policy;
    # leaving it set leaks this app's preference into every later test.
    set_transition_announcement_policy(None)
    del app


def test_every_enabled_menu_item_advertises_a_keyboard_route(quill_menu_bar) -> None:
    """The house rule, finally true of the biggest bar in the family.

    Walking a menu to discover there is no faster way in is a cost a listener
    pays on every visit. A disabled row is exempt -- there is nothing to reach.
    """
    missing = [
        where
        for where, label, enabled in _items(quill_menu_bar)
        if enabled and not _advertises_a_route(label)
    ]
    assert missing == [], "menu items with no keyboard route: " + "; ".join(missing)


def test_every_advertised_key_is_one_wx_can_actually_bind(quill_menu_bar) -> None:
    unparsable = []
    for where, label, _enabled in _items(quill_menu_bar):
        if _TAB not in label:
            continue
        entry = wx.AcceleratorEntry()
        with wx.LogNull():
            if not entry.FromString(label):
                unparsable.append(f"{where} ({label.split(_TAB, 1)[1]})")
    assert unparsable == [], "wx cannot bind these: " + "; ".join(unparsable)


def test_no_two_menu_items_claim_the_same_key(quill_menu_bar) -> None:
    """Compared canonically -- wx ignores the order the modifiers are written in."""
    from quill.core.keymap_query import canonical_binding

    claimed = collections.defaultdict(list)
    for where, label, _enabled in _items(quill_menu_bar):
        if _TAB in label:
            accel = label.split(_TAB, 1)[1].strip()
            claimed[canonical_binding(accel) or accel].append(where)
    duplicated = {key: where for key, where in claimed.items() if len(where) > 1}
    assert duplicated == {}, f"accelerators claimed twice: {duplicated}"


def test_no_popup_claims_one_alt_letter_twice(quill_menu_bar) -> None:
    """The hole GATE-14's per-class scoping leaves.

    An Alt path is only a route if each letter along it resolves to one item.
    Windows cycles focus between duplicates instead of pressing, so one of the
    pair silently cannot be reached and nothing announces the loss -- and the
    access-key gate cannot see it, because a menu bar built across a dozen mixin
    methods is a dozen scopes to that checker and one window to the user.
    """
    collisions: list[str] = []

    def walk(menu, path: str) -> None:
        claimed: dict[str, list[str]] = collections.defaultdict(list)
        for item in menu.GetMenuItems():
            if item.IsSeparator():
                continue
            title = item.GetItemLabel().split(_TAB, 1)[0]
            letter = _mnemonic(title)
            if letter:
                claimed[letter].append(title)
            submenu = item.GetSubMenu()
            if submenu is not None:
                walk(submenu, f"{path} > {title}")
        for letter, titles in sorted(claimed.items()):
            if len(titles) > 1:
                collisions.append(f"{path} :: {letter} -> {titles}")

    top: dict[str, list[str]] = collections.defaultdict(list)
    for index in range(quill_menu_bar.GetMenuCount()):
        label = quill_menu_bar.GetMenuLabel(index)
        letter = _mnemonic(label)
        if letter:
            top[letter].append(label)
        walk(quill_menu_bar.GetMenu(index), label)
    for letter, labels in sorted(top.items()):
        if len(labels) > 1:
            collisions.append(f"(menu bar) :: {letter} -> {labels}")

    assert collisions == [], "one Alt letter, two items: " + "; ".join(collisions)


def test_every_menu_item_has_a_mnemonic_at_all(quill_menu_bar) -> None:
    """166 had none -- the fonts, the point sizes, the colours, the languages.

    Rows of data rather than commands, which is why nobody wrote a mnemonic for
    them, and a row you cannot type a letter at is a row you have to arrow to.
    """
    missing: list[str] = []

    def walk(menu, path: str) -> None:
        for item in menu.GetMenuItems():
            if item.IsSeparator():
                continue
            title = item.GetItemLabel().split(_TAB, 1)[0]
            if not _mnemonic(title):
                missing.append(f"{path} > {title}")
            submenu = item.GetSubMenu()
            if submenu is not None:
                walk(submenu, f"{path} > {title}")

    for index in range(quill_menu_bar.GetMenuCount()):
        walk(quill_menu_bar.GetMenu(index), quill_menu_bar.GetMenuLabel(index))
    assert missing == [], "menu items with no Alt letter: " + "; ".join(missing)
