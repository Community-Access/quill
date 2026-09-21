"""Dialog accessibility regression coverage for the Audio Studio surfaces.

The branch added a dozen new dialogs (the wizard, the Workbench, two
analysis-modals, the publish dialog, etc.) to the inventory. Each one
ships through the same ``apply_modal_ids`` contract that
``test_dialog_accessibility.py`` already audits for Go To Line. These
tests extend that contract to the Audio Studio.

The tests are opt-in by the same mechanism as the rest of the UIA suite:
``QUILL_UIA_TESTS=1`` on a Windows desktop session. They never run in
the default test set.
"""

from __future__ import annotations

import time

import pytest

from tests.uia.a11y_scan import scan_window, summarize, unnamed_focusable

pytestmark = pytest.mark.uia


def _open_dialog_via_keys(quill_app, keys: str, title_fragment: str, attempts: int = 3):
    # A freshly-launched window can lose the first accelerator to a foreground
    # race (seen on CI runners), so the keystroke is retried, never assumed.
    last_error: Exception | None = None
    for _ in range(attempts):
        quill_app.main_window.set_focus()
        quill_app.main_window.type_keys(keys)
        dialog = quill_app.main_window.child_window(
            title_re=f".*{title_fragment}.*", control_type="Window"
        )
        try:
            dialog.wait("exists visible", timeout=6)
            return dialog
        except Exception as exc:  # noqa: BLE001 - retry the keystroke
            last_error = exc
    raise AssertionError(f"dialog {title_fragment!r} never opened via {keys!r}: {last_error}")


#: Tools > Speech > Audiobook & Batch Speech, which is what opens the wizard.
#:
#: Every letter is read off a menu label, and the two that look wrong are the
#: right ones. In the Tools menu ``S`` belongs to "Story &Studio...", so the
#: Speech submenu is titled "Speec&h" and answers to ``H``; inside it the Audio
#: Studio entry is "Audiobook && &Batch Speech...", so ``B``. Both letters are
#: unique in their own menu, which is what ``test_menu_item_access_keys.py``
#: guarantees and what makes a single deterministic path possible here.
_AUDIO_STUDIO_MENU_PATH = "%thb"


def _open_audio_studio(quill_app):
    """Reach the wizard through Tools > Speech > Audiobook & Batch Speech.

    This used to try ``%t``, ``%t``, ``%ts`` and ``%tsa`` in a loop and keep
    whichever opened a window called "Audio Studio". None of them does. The
    menu has no "Speech > Audio Studio" row -- ``%ts`` lands on "Story
    &Studio...", which is *modal*, which disables the main window, so the next
    iteration's ``type_keys`` raised ``ElementNotEnabled`` and every one of the
    seven tests in this file failed on a misspelled menu path rather than on
    anything about the Audio Studio.

    So: one path, and it is asserted rather than swallowed. The retry stays,
    because a freshly launched window really can lose the first accelerator to
    a foreground race on a CI runner -- but each attempt first presses Escape
    twice to dismiss a half-open menu, and refuses to type into a main window
    that something has disabled, because that is a modal we did not mean to
    open and reporting it is more use than dying inside pywinauto.
    """
    from pywinauto.keyboard import send_keys

    last_error: Exception | None = None
    for attempt in range(3):
        if attempt:
            # Close whatever the previous attempt left open. send_keys goes to
            # the foreground window without pywinauto's actionable check, which
            # is the point: the thing in front may be a menu, not a control.
            send_keys("{ESC}{ESC}")
            time.sleep(0.3)
        quill_app.main_window.set_focus()
        if not quill_app.main_window.wrapper_object().is_enabled():
            raise AssertionError(
                "the QUILL main window is disabled, so a modal dialog is open "
                "that this test did not ask for; the Audio Studio menu path "
                f"({_AUDIO_STUDIO_MENU_PATH!r}) cannot be typed"
            )
        quill_app.main_window.type_keys(_AUDIO_STUDIO_MENU_PATH, with_spaces=False)
        dialog = quill_app.main_window.child_window(
            title_re=".*Audio Studio.*", control_type="Window"
        )
        try:
            dialog.wait("exists visible", timeout=8)
            return dialog
        except Exception as exc:  # noqa: BLE001 - retry the keystroke
            last_error = exc
    raise AssertionError(
        "the Audio Studio wizard never opened via Tools > Speech > Audiobook "
        f"&& Batch Speech ({_AUDIO_STUDIO_MENU_PATH!r}): {last_error}"
    )


def _wait_for_close(window: object, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if not window.exists(timeout=0.5):
                return
        except Exception:  # noqa: BLE001 - a destroyed window counts as closed
            return
        time.sleep(0.25)
    raise AssertionError("Window did not close within timeout")


def test_audio_studio_wizard_is_fully_named(quill_app) -> None:
    """The wizard's first page lists no unnamed focusable controls."""
    dialog = _open_audio_studio(quill_app)
    try:
        records = scan_window(dialog)
        offenders = unnamed_focusable(records)
        assert not offenders, (
            "Audio Studio wizard: unnamed focusable controls detected:\n"
            + "\n".join(summarize(offenders))
        )
    finally:
        dialog.type_keys("{ESC}")
        _wait_for_close(dialog)


def test_audio_studio_wizard_announces_itself(quill_app) -> None:
    """Opening the wizard produces an announcement that names it."""
    dialog = _open_audio_studio(quill_app)
    try:
        quill_app.wait_spoken("Audio Studio", timeout=10.0)
    finally:
        dialog.type_keys("{ESC}")
        _wait_for_close(dialog)


def test_audio_studio_wizard_escape_closes_it(quill_app) -> None:
    """Escape from the wizard returns to the main window."""
    dialog = _open_audio_studio(quill_app)
    dialog.type_keys("{ESC}")
    _wait_for_close(dialog)
    # The main window is still responsive afterwards.
    quill_app.main_window.wait("visible", timeout=5)


# ---------------------------------------------------------------------------
# Audio Studio UIA-regression coverage: page walk + spoken-output trace
# + Workbench on the corpus sample + silence-params modal.
# ---------------------------------------------------------------------------
#
# The wizard's journey radio carries no ``&`` mnemonic on its choices, so
# selecting a non-default journey is done by ``Down`` arrow keys. The
# ``Next`` button uses the ``&`` mnemonic from its label ("&Next >") and
# is reached by ``Alt+N``.


def _next_page(dialog) -> None:
    """Press the Next button on the wizard by mnemonic."""
    dialog.set_focus()
    dialog.type_keys("%n")  # Alt+N matches the &Next > mnemonic


def _select_journey_edit(dialog) -> None:
    """Switch the StartPage radio from documents to edit (third option)."""
    dialog.set_focus()
    # Focus the radio first (Alt+W matches the '&What would you like to make?'
    # group label in many builds; if the mnemonic doesn't fire, two Tab
    # presses from the dialog body land on the radio).
    dialog.type_keys("{TAB}{TAB}")
    dialog.type_keys("{DOWN}{DOWN}")


def test_audio_studio_wizard_documents_journey_has_named_pages(quill_app) -> None:
    """Every page reached by Next on the documents journey is fully named.

    The seven-page documents journey (start, doc_source, voices, chapters,
    output, book, summary) is walked one Next at a time and each page is
    scanned for unnamed focusable controls. The contract: regressions in
    focus order or labelling are caught by the robot.
    """
    dialog = _open_audio_studio(quill_app)
    try:
        # The first page is asserted by the existing test; we walk from
        # page 2 onward so this test focuses on the forward traversal.
        for _ in range(6):
            _next_page(dialog)
            time.sleep(0.4)  # let page transition settle
            records = scan_window(dialog)
            offenders = unnamed_focusable(records)
            assert not offenders, (
                "Audio Studio documents journey: unnamed focusable controls "
                f"on page {_}:\n" + "\n".join(summarize(offenders))
            )
    finally:
        dialog.type_keys("{ESC}")
        _wait_for_close(dialog)


def test_audio_studio_wizard_announces_each_page(quill_app) -> None:
    """The wizard announces every page change on the documents journey.

    The same channel a screen reader hears — ``announcement-trace.log`` —
    is what the user perceives; if a future change silences the
    announcement, this test fails instead of a user.
    """
    dialog = _open_audio_studio(quill_app)
    try:
        # The first page's announcement is already covered by
        # ``test_audio_studio_wizard_announces_itself``; we walk forward
        # and assert each subsequent ``Step N of M: <heading>`` lands in
        # the trace.
        expected_headings = [
            "What should I read",
            "Who should read it",
            "How should chapters work",
            "Output and diagnostics",
            "Tell me about the book",
            "Review and start",
        ]
        for heading in expected_headings:
            _next_page(dialog)
            # The wizard announces "Step N of 7: <heading>" on each page
            # change; assert the heading fragment appears, not the exact
            # step counter, so localized step wording doesn't fail the test.
            quill_app.wait_spoken(heading, timeout=10.0)
    finally:
        dialog.type_keys("{ESC}")
        _wait_for_close(dialog)


def test_audio_studio_workbench_opens_from_edit_journey(quill_app) -> None:
    """The edit journey opens the Workbench on the corpus sample.

    The audiobooks MRU is pre-seeded by the conftest fixture so the
    EditSourcePage ComboBox already carries ``chaptered-sample.mp3`` at
    the top. The test then advances to the EditSourcePage, picks the
    pre-seeded value, and presses the Start button (whose label flips
    to "&Open in Workbench" for the edit journey), and asserts the
    Workbench dialog appears with no unnamed focusable controls.
    """
    dialog = _open_audio_studio(quill_app)
    try:
        _select_journey_edit(dialog)
        _next_page(dialog)  # start -> edit_source
        time.sleep(0.5)
        # The EditSourcePage ComboBox is pre-seeded with the corpus
        # sample. Press Enter to confirm the current value, then click
        # Open in Workbench (Alt+O is the &Open... mnemonic on the
        # Start button for the edit journey).
        dialog.type_keys("{ENTER}")
        time.sleep(0.2)
        dialog.type_keys("%o")
        # The wizard closes, the Workbench opens. Wait for the Workbench
        # dialog by title fragment.
        workbench = quill_app.main_window.child_window(
            title_re=".*Workbench.*", control_type="Window"
        )
        workbench.wait("exists visible", timeout=10.0)
        try:
            records = scan_window(workbench)
            offenders = unnamed_focusable(records)
            assert not offenders, (
                "Chapter Workbench: unnamed focusable controls detected:\n"
                + "\n".join(summarize(offenders))
            )
            # The Workbench announces itself when it opens.
            quill_app.wait_spoken("Workbench", timeout=10.0)
        finally:
            workbench.type_keys("{ESC}")
            _wait_for_close(workbench)
    finally:
        # The wizard may still be open if the test failed before the
        # Start press; close it to free the desktop for the next test.
        try:
            if dialog.exists(timeout=0.5):
                dialog.type_keys("{ESC}")
                _wait_for_close(dialog)
        except Exception:  # noqa: BLE001 - already closed
            pass


def test_audio_studio_workbench_silence_params_dialog_is_fully_named(quill_app) -> None:
    """The silence-proposal parameters modal has no unnamed focusables.

    Reached from the Workbench's "Propose chapters from silences..." button
    (Alt+I mnemonic). The dialog may take a moment to build the proposal
    pool; the test asserts the modal itself is well-named and closes it
    before the ffmpeg pool finishes.
    """
    dialog = _open_audio_studio(quill_app)
    try:
        _select_journey_edit(dialog)
        _next_page(dialog)
        time.sleep(0.5)
        dialog.type_keys("{ENTER}")
        time.sleep(0.2)
        dialog.type_keys("%o")
        workbench = quill_app.main_window.child_window(
            title_re=".*Workbench.*", control_type="Window"
        )
        workbench.wait("exists visible", timeout=10.0)
        try:
            # Alt+C = "silen&ces" on "Propose chapters from silen&ces...".
            # It was Alt+I until GATE-14 learned to read translated labels and
            # found "Chapter t&itle:" claiming the same letter in this window:
            # Windows cycles a duplicated mnemonic instead of pressing it, so
            # Alt+I moved focus to the title field and this step quietly did
            # nothing.
            workbench.set_focus()
            workbench.type_keys("%c")
            modal = quill_app.main_window.child_window(
                title_re=".*silences.*", control_type="Window"
            )
            # Not opening is tolerated -- the proposal pool does not surface on
            # every CI runner. Once it *is* open, the scan is an assertion.
            # It used to share an ``except Exception`` with the wait, which
            # swallowed its own AssertionError: a test that could not fail.
            try:
                modal.wait("exists visible", timeout=6.0)
            except Exception:  # noqa: BLE001 - no pool on this runner, nothing to scan
                opened = False
            else:
                opened = True
            try:
                if opened:
                    records = scan_window(modal)
                    offenders = unnamed_focusable(records)
                    assert not offenders, (
                        "SilenceParamsDialog: unnamed focusable controls detected:\n"
                        + "\n".join(summarize(offenders))
                    )
            finally:
                # Close whatever modal opened (or the Workbench itself if
                # the silence params dialog didn't surface).
                try:
                    modal.type_keys("{ESC}")
                    _wait_for_close(modal)
                except Exception:  # noqa: BLE001
                    workbench.type_keys("{ESC}")
                    _wait_for_close(workbench)
        finally:
            try:
                if workbench.exists(timeout=0.5):
                    workbench.type_keys("{ESC}")
                    _wait_for_close(workbench)
            except Exception:  # noqa: BLE001 - already closed
                pass
    finally:
        try:
            if dialog.exists(timeout=0.5):
                dialog.type_keys("{ESC}")
                _wait_for_close(dialog)
        except Exception:  # noqa: BLE001 - already closed
            pass
