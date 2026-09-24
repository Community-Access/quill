"""Tools > AI: what each command actually does.

Every test here **calls the handler**, and the calls are written as lambdas
rather than as a parametrized list of method names. That is not a style
preference: ``quill.tools.lite_command_coverage`` detects coverage by walking
the AST for real calls, and ``getattr(win, name)()`` over a parametrized string
is invisible to it. A table of handler names that never calls one is exactly the
shape of test that let the F8 bug ship -- a key, a label, a handler, a passing
test, and extend mode that had never once worked from the keyboard.

The frames are patched at :mod:`quill.ui.hosted_ai_dialogs`, which is where the
mixin imports them from (inside the methods, so that is also where they are
looked up). What is being exercised is the handler: the guard, the resolution of
what to send, and what it hands the window.
"""

from __future__ import annotations

import pytest


class _FakeFrame:
    """Records how it was constructed, and pretends to be a window."""

    last: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last = {"args": args, "kwargs": kwargs}
        self.shown = False

    def Show(self):  # noqa: N802 - wx API shape
        self.shown = True

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        self.focused = True

    def Bind(self, _event, handler):  # noqa: N802 - wx API shape
        # The mixin attaches an EVT_CLOSE handler so a closed window stops
        # counting as open. Kept so close() below can fire it.
        self._on_close = handler

    def close(self):
        """Close this window the way wx would, handler and all."""
        handler = getattr(self, "_on_close", None)
        if handler is not None:
            handler(type("_Event", (), {"Skip": lambda _self: None})())


@pytest.fixture
def ai_frames(monkeypatch):
    """Every AI window, replaced by a recorder. Returns the four classes."""
    import quill.ui.hosted_ai_dialogs as dialogs
    import quill.ui.hosted_ai_pad as pad

    # Patched where each is looked up, not where it is defined -- the mixin
    # imports them inside its methods, so the defining module is the lookup
    # site. Getting this backwards is the mistake tests/unit/apps/conftest.py's
    # DialogRecorder names both ends of every entry point to avoid.
    made = {}
    for module, names in (
        (pad, ("AiPadFrame", "AiResultFrame")),
        (dialogs, ("AiSignInFrame", "AiUsageFrame")),
    ):
        for name in names:
            cls = type(name, (_FakeFrame,), {"last": None})
            monkeypatch.setattr(module, name, cls)
            made[name] = cls
    return made


@pytest.fixture
def signed_in(monkeypatch):
    """An AI service that believes this computer is connected **and agreed to**.

    The agreement is granted here rather than repeated in every test that is
    about something else, because every one of these would otherwise be
    testing the consent gate by accident and its own subject not at all. The
    gate has its own tests further down, and they are the ones that matter for
    it.
    """
    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)

    class Service:
        signed_in = True
        support_id = "A1B2-C3D4"

        def __init__(self):
            self.refreshed = False
            self.asked = None

        def refresh_limits(self, on_done=None):
            self.refreshed = True

        def unavailable_reason(self, feature=""):
            return ""

    return Service()


@pytest.fixture
def connected(monkeypatch):
    """Connected, but with the consent gate left alone.

    The companion to ``signed_in``: same service, no acceptance granted, so the
    gate's own tests exercise the gate rather than a fixture's opinion of it.
    """

    class Service:
        signed_in = True
        support_id = "A1B2-C3D4"

        def refresh_limits(self, on_done=None):
            pass

        def unavailable_reason(self, feature=""):
            return ""

    return Service()


# --------------------------------------------------------------------------- #
# The guard: an area that is off owns nothing
# --------------------------------------------------------------------------- #


def test_the_assistant_refuses_when_the_area_is_switched_off(lite_window, ai_frames, monkeypatch):
    """The menus and the palette already hide these, so reaching here with the
    area off means a stale accelerator. The thing being guarded is a network
    request somebody declined, which is worth a second check."""
    win = lite_window("some text")
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_ai_assistant())(win)

    assert ai_frames["AiPadFrame"].last is None
    assert any("switched off" in said for said in win.announcements)


def test_every_ai_command_refuses_when_the_area_is_off(lite_window, ai_frames, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_ai_ask_document())(win)
    (lambda w: w.cmd_ai_usage())(win)
    (lambda w: w.cmd_ai_sign_in())(win)

    assert ai_frames["AiPadFrame"].last is None
    assert ai_frames["AiUsageFrame"].last is None
    assert ai_frames["AiSignInFrame"].last is None


# --------------------------------------------------------------------------- #
# Signed out: offer the way in rather than a dead end
# --------------------------------------------------------------------------- #


def test_the_assistant_offers_sign_in_when_this_computer_is_not_connected(
    lite_window, ai_frames, monkeypatch
):
    """Not a refusal. Somebody who presses the AI key wants AI, and the next
    thing they need is the one window that gets them there."""
    win = lite_window("some text")

    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)

    class SignedOut:
        signed_in = False

    monkeypatch.setattr(win, "_ai_service", lambda: SignedOut())

    (lambda w: w.cmd_ai_assistant())(win)

    assert ai_frames["AiPadFrame"].last is None
    assert ai_frames["AiSignInFrame"].last is not None
    assert any("not connected" in said for said in win.announcements)


def test_usage_does_not_open_when_signed_out(lite_window, ai_frames, monkeypatch):
    """A usage window for an account that does not exist has nothing to show."""
    win = lite_window("text")

    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)

    class SignedOut:
        signed_in = False

    monkeypatch.setattr(win, "_ai_service", lambda: SignedOut())

    (lambda w: w.cmd_ai_usage())(win)

    assert ai_frames["AiUsageFrame"].last is None


# --------------------------------------------------------------------------- #
# What the pad is handed
# --------------------------------------------------------------------------- #


def test_the_assistant_hands_the_pad_the_selection_and_the_caret(
    lite_window, ai_frames, monkeypatch, signed_in
):
    win = lite_window("First paragraph.\n\nSecond paragraph.")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)
    win.control.SetSelection(0, 16)

    (lambda w: w.cmd_ai_assistant())(win)

    kwargs = ai_frames["AiPadFrame"].last["kwargs"]
    assert kwargs["selection"] == "First paragraph."
    assert kwargs["document_text"].startswith("First paragraph.")
    assert kwargs["initial_action"] == ""


def test_ask_about_this_document_opens_the_pad_on_the_question_action(
    lite_window, ai_frames, monkeypatch, signed_in
):
    """The one command whose input is a question rather than the selection,
    which is why it has a chord of its own."""
    win = lite_window("Some document text.")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    (lambda w: w.cmd_ai_ask_document())(win)

    assert ai_frames["AiPadFrame"].last["kwargs"]["initial_action"] == "document_qna"


def test_opening_the_pad_refreshes_what_the_service_allows(
    lite_window, ai_frames, monkeypatch, signed_in
):
    """So the size check and the excerpt count match the server rather than a
    constant compiled in months ago."""
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    (lambda w: w.cmd_ai_assistant())(win)

    assert signed_in.refreshed is True


def test_the_usage_window_is_handed_the_service(lite_window, ai_frames, monkeypatch, signed_in):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    (lambda w: w.cmd_ai_usage())(win)

    assert ai_frames["AiUsageFrame"].last is not None


def test_sign_in_opens_even_when_already_connected(lite_window, ai_frames, monkeypatch, signed_in):
    """It is Sign In *or Out*: somebody already connected uses this window to
    check that, and to get to the way back out."""
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    (lambda w: w.cmd_ai_sign_in())(win)

    assert ai_frames["AiSignInFrame"].last is not None


# --------------------------------------------------------------------------- #
# Applying an answer, and refusing to apply a stale one
# --------------------------------------------------------------------------- #


def test_replace_is_offered_when_the_selection_is_still_there(
    lite_window, ai_frames, monkeypatch, signed_in
):
    win = lite_window("First paragraph.\n\nSecond paragraph.")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    win._show_ai_result("summarize", "A summary.", "Used 1.", 0, 16, "First paragraph.", "")

    assert ai_frames["AiResultFrame"].last["kwargs"]["on_replace"] is not None


def test_replace_is_withheld_when_the_text_moved_while_the_answer_was_coming(
    lite_window, ai_frames, monkeypatch, signed_in
):
    """The editor stayed live while the request ran, so the offsets may now hold
    something else entirely. Writing an answer over whatever happens to be there
    would be a silent wrong edit -- and the undo stack would show it as
    something the user did."""
    win = lite_window("Totally different text now.")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    win._show_ai_result("summarize", "A summary.", "Used 1.", 0, 16, "First paragraph.", "")

    assert ai_frames["AiResultFrame"].last["kwargs"]["on_replace"] is None
    # Insert is still offered: it does not depend on the old range.
    assert ai_frames["AiResultFrame"].last["kwargs"]["on_insert"] is not None


def test_replace_goes_in_as_one_undoable_edit(lite_window, monkeypatch, signed_in):
    """Control Z takes back the whole answer, not forty separate writes."""
    win = lite_window("First paragraph.\n\nSecond paragraph.")
    win._replace_range(0, 16, "A shorter one.")
    assert win.control.GetValue().startswith("A shorter one.")
    assert "Second paragraph." in win.control.GetValue()


def test_insert_below_puts_the_answer_after_the_paragraph_not_inside_it(
    lite_window, monkeypatch, signed_in
):
    """An answer dropped mid-sentence is an answer somebody has to tidy up."""
    win = lite_window("First paragraph.\n\nSecond paragraph.")
    win.control.SetInsertionPoint(5)

    win._insert_below("A summary.")

    value = win.control.GetValue()
    assert value.startswith("First paragraph.\n\nA summary.")
    assert "Second paragraph." in value


def test_an_answer_never_reaches_the_document_on_its_own(
    lite_window, ai_frames, monkeypatch, signed_in
):
    """The whole rule: AI never edits without a keystroke saying so. Showing a
    result changes nothing until somebody presses a button in that window."""
    win = lite_window("Original text.")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    win._show_ai_result("summarize", "A summary.", "Used 1.", 0, 8, "Original", "")

    assert win.control.GetValue() == "Original text."


# --------------------------------------------------------------------------- #
# The privacy agreement
# --------------------------------------------------------------------------- #


@pytest.fixture
def agreement(monkeypatch):
    """The agreement dialog, answered by the test. Defaults to declining.

    Cancel-by-default, like every other dialog in this harness: refusing consent
    is the branch people forget to write, and it is the branch that must leave
    the feature unusable.
    """
    import quill.ui.hosted_ai_dialogs as dialogs

    calls = {"shown": 0, "answer": False}

    def fake(parent):
        calls["shown"] += 1
        return calls["answer"]

    monkeypatch.setattr(dialogs, "ask_ai_privacy_agreement", fake)
    return calls


def test_ai_does_nothing_until_the_agreement_is_accepted(
    lite_window, ai_frames, agreement, monkeypatch, connected
):
    """The area being on is not consent. It can be switched on by a profile, by
    a settings import, or by somebody else using this machine."""
    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = 0

    (lambda w: w.cmd_ai_assistant())(win)

    assert agreement["shown"] == 1
    assert ai_frames["AiPadFrame"].last is None


def test_accepting_the_agreement_lets_the_command_through_at_once(
    lite_window, ai_frames, agreement, monkeypatch, connected
):
    """An offer, not a refusal. Somebody who pressed the AI key wants AI, so
    accepting continues into the thing they asked for rather than making them
    press it again."""
    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = True

    (lambda w: w.cmd_ai_assistant())(win)

    assert ai_frames["AiPadFrame"].last is not None
    from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

    assert win.app.settings.ai_privacy_accepted_version == AGREEMENT_VERSION


def test_an_accepted_agreement_is_not_asked_for_again(
    lite_window, ai_frames, agreement, monkeypatch, connected
):
    from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = AGREEMENT_VERSION

    (lambda w: w.cmd_ai_assistant())(win)

    assert agreement["shown"] == 0
    assert ai_frames["AiPadFrame"].last is not None


def test_a_newer_agreement_asks_again(lite_window, ai_frames, agreement, monkeypatch, connected):
    """Versioned rather than a boolean, so a material change to what is sent or
    kept can ask again instead of an old yes silently covering a new thing."""
    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = 0  # an older yes, or none

    (lambda w: w.cmd_ai_assistant())(win)

    assert agreement["shown"] == 1


def test_the_privacy_command_shows_the_agreement_when_it_is_not_accepted(
    lite_window, agreement, monkeypatch
):
    win = lite_window("text")
    win.app.settings.ai_privacy_accepted_version = 0

    (lambda w: w.cmd_ai_privacy())(win)

    assert agreement["shown"] == 1


def test_the_privacy_command_withdraws_an_accepted_agreement(lite_window, agreement, monkeypatch):
    """Door one of three, in its "take it back" direction."""
    from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

    win = lite_window("text")
    win.app.settings.ai_privacy_accepted_version = AGREEMENT_VERSION

    (lambda w: w.cmd_ai_privacy())(win)

    assert win.app.settings.ai_privacy_accepted_version == 0
    assert any("signed out" in said for said in win.announcements)


def test_withdrawing_also_signs_this_computer_out(lite_window, agreement, monkeypatch):
    """Leaving a token on disk for a service somebody just said they do not
    agree to use would be keeping the credential for the exact thing they
    withdrew from."""
    from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

    class Service:
        signed_in = True

        def __init__(self):
            self.signed_out = False

        def sign_out(self):
            self.signed_out = True

    service = Service()
    win = lite_window("text")
    win.app.ai_service = service
    win.app.settings.ai_privacy_accepted_version = AGREEMENT_VERSION

    (lambda w: w.cmd_ai_privacy())(win)

    assert service.signed_out is True


def test_declining_leaves_the_feature_present_and_unusable(
    lite_window, ai_frames, agreement, monkeypatch, connected
):
    """Not switched back off. A switch that flips itself back is a switch
    somebody will fight -- and they would be right to: they did turn it on, and
    what they declined was the sending."""
    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = False

    (lambda w: w.cmd_ai_assistant())(win)

    assert ai_frames["AiPadFrame"].last is None
    assert win.app.feature_enabled("hosted_ai") is True


def test_switching_the_area_on_offers_the_agreement(lite_window, agreement, monkeypatch):
    """Door two of three, and the one somebody can arrive at without meaning
    to: applying the Everything profile turns the area on along with seventeen
    others, and a profile is not consent."""
    win = lite_window("text")
    win.app.settings.ai_privacy_accepted_version = 0

    win._offer_ai_privacy_on_enable()

    assert agreement["shown"] == 1
    assert any("will not send anything" in said for said in win.announcements)


def test_the_agreement_says_what_is_sent_and_what_is_kept():
    """The two facts somebody needs to decide. If either ever stops being in
    there, the version number should have gone up."""
    from quill.core.ai.gateway_privacy import SUMMARY, agreement_text

    text = agreement_text()
    assert "OpenAI" in text
    assert "What QUILL keeps" in text
    assert "What QUILL does not keep" in text
    assert "What you wrote" in text
    # And it always says how to say no.
    assert "If you would rather not" in text
    assert "OpenAI" in SUMMARY


# --------------------------------------------------------------------------- #
# Focus, and the door that is always open
# --------------------------------------------------------------------------- #


def test_every_ai_window_says_where_focus_should_land(lite_window, monkeypatch, signed_in):
    """Reported from actually running it: the Sign In window did not take focus.

    The cause was ``SetFocus()`` in a constructor. On wxMSW focus given to a
    control in a window that has not been shown yet is discarded when the window
    finally is -- so every one of those calls was silently doing nothing. The
    other dialogs in QuillLite get away with it because they are ``wx.Dialog``s,
    which ``Show()`` activates; these are ``wx.Frame``s parented to an MDI child,
    which it does not.
    """
    from quill.ui.hosted_ai_dialogs import focus_on

    class Frame:
        pass

    class Control:
        pass

    frame, control = Frame(), Control()
    focus_on(frame, control)
    assert frame._focus_target is control


def test_showing_a_window_actually_gives_it_focus(lite_window, ai_frames, monkeypatch, signed_in):
    """The outcome, not the mechanism.

    An earlier version of this asserted that ``wx.CallAfter`` was used, which is
    a detail that changed the moment the no-running-app path was added. What has
    to stay true is that the window somebody opened ends up with focus -- the
    thing that was broken.
    """
    win = lite_window("some text")
    monkeypatch.setattr(win, "_ai_service", lambda: signed_in)

    (lambda w: w.cmd_ai_assistant())(win)

    pad = ai_frames["AiPadFrame"].last
    assert pad is not None
    # _show_ai_window keeps the instance it showed; the recorder only keeps the
    # construction, so reach for the frame through the call it made.
    assert getattr(win, "_last_shown_ai_window", None) is not None
    assert win._last_shown_ai_window.focused is True


def test_taking_focus_survives_a_window_closed_in_the_meantime(lite_window):
    """A user can close a window between Show() and the next idle cycle, and a
    focus call into a destroyed control is a crash rather than a missed focus."""
    from quill.ui.hosted_ai_dialogs import take_focus

    class Gone:
        def __bool__(self):
            return False

    take_focus(Gone())  # must not raise


def test_the_privacy_agreement_is_reachable_with_the_feature_switched_off():
    """Reported: the privacy option should work whether or not AI is enabled.

    A consent control that disappears along with the feature it governs is a
    consent control you cannot withdraw from -- and somebody has to be able to
    read what they would be agreeing to *before* agreeing to it.
    """
    from quill.core.lite.command_areas import visible_commands

    off = visible_commands(lambda area: area != "hosted_ai")
    rows = [row for row in off if row[0] == "&Tools|&AI"]
    assert [row[3] for row in rows] == ["cmd_ai_privacy"]
    # And the submenu that holds it survives with it.
    assert any(row[4] == "sub" and row[1] == "&AI" for row in off)


def test_the_privacy_command_runs_with_the_feature_switched_off(
    lite_window, agreement, monkeypatch
):
    c = lite_window("text")
    monkeypatch.setattr(c.app, "feature_enabled", lambda area: area != "hosted_ai")
    c.app.settings.ai_privacy_accepted_version = 0

    (lambda w: w.cmd_ai_privacy())(c)

    assert agreement["shown"] == 1


def test_accepting_from_the_privacy_command_switches_the_feature_on(
    lite_window, agreement, monkeypatch
):
    """Whichever door you came through, saying yes leaves you with a working
    feature. Being sent to find a second switch would be a yes that did
    nothing."""
    from quill.core.ai.gateway_privacy import AGREEMENT_VERSION

    class Features:
        def __init__(self):
            self.disabled = {"hosted_ai"}

        def is_enabled(self, area):
            return area not in self.disabled

        def set_enabled(self, area, enabled):
            self.disabled.discard(area) if enabled else self.disabled.add(area)

    win = lite_window("text")
    win.app.features = Features()
    monkeypatch.setattr(win.app, "feature_enabled", lambda a: win.app.features.is_enabled(a))
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = True

    (lambda w: w.cmd_ai_privacy())(win)

    assert win.app.settings.ai_privacy_accepted_version == AGREEMENT_VERSION
    assert win.app.features.is_enabled("hosted_ai") is True
    assert any("AI help is on" in said for said in win.announcements)


# --------------------------------------------------------------------------- #
# What the agreement says on the way past, and what the windows do twice
# --------------------------------------------------------------------------- #


def test_escaping_the_agreement_says_nothing(lite_window, ai_frames, agreement, monkeypatch):
    """Escape changed nothing, and the reader announces the caret arriving back
    in the document. A sentence on top of that is the over-announcing GATE-13
    exists to catch -- and it was said on every Escape from every door."""
    win = lite_window("text")
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = False

    (lambda w: w.cmd_ai_privacy())(win)

    assert agreement["shown"] == 1
    assert win.announcements == []


def test_accepting_on_the_way_to_sign_in_does_not_send_you_back_to_sign_in(
    lite_window, ai_frames, agreement, monkeypatch, connected
):
    """The agreement used to answer "choose Tools, AI, Sign In or Out" to
    somebody who had just chosen exactly that. The window they asked for is the
    answer; the reader announces it when it takes focus."""
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = True

    (lambda w: w.cmd_ai_sign_in())(win)

    assert ai_frames["AiSignInFrame"].last is not None
    assert win.announcements == []


def test_the_privacy_door_says_it_took_even_when_the_area_was_already_on(
    lite_window, agreement, monkeypatch
):
    """The sentence moved out of the dialog and into the caller, and this is the
    case that proves it had to: nothing about the *features* changed, so a
    message built around switching the area on could not be said here at all."""
    win = lite_window("text")
    win.app.settings.ai_privacy_accepted_version = 0
    agreement["answer"] = True

    (lambda w: w.cmd_ai_privacy())(win)

    assert any("AI help is on" in said for said in win.announcements)


def test_asking_for_a_window_twice_raises_the_one_that_is_open(
    lite_window, ai_frames, monkeypatch, signed_in
):
    """A second Sign-In window built over the first announces nothing, because
    a frame opening where a frame already is announces nothing -- so the second
    press was indistinguishable by ear from a key that is not bound."""
    win = lite_window("text")

    (lambda w: w.cmd_ai_sign_in())(win)
    first = ai_frames["AiSignInFrame"].last
    (lambda w: w.cmd_ai_sign_in())(win)

    assert ai_frames["AiSignInFrame"].last is first, "no second window was built"


def test_closing_a_window_lets_the_next_press_open_it_again(
    lite_window, ai_frames, monkeypatch, signed_in
):
    win = lite_window("text")

    (lambda w: w.cmd_ai_sign_in())(win)
    win._ai_windows["sign_in"].close()
    ai_frames["AiSignInFrame"].last = None
    (lambda w: w.cmd_ai_sign_in())(win)

    assert ai_frames["AiSignInFrame"].last is not None
