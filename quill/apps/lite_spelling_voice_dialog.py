"""The Spelling Announcements window: how a misspelling is said, and when.

Its own window rather than twelve more rows in Preferences, and that is a
judgement about *reading* rather than about screen space. Preferences is a flat
list of unrelated answers -- what Ctrl+N makes, which font, how often work is
copied aside -- and each row is read once and understood. These twelve are one
subject with three parts, and the parts only make sense next to each other: the
pause exists because the spelling is a second utterance, and the second utterance
exists because a misspelled word and the correct one are the same sound. Dropped
into a flat list they read as twelve unrelated switches, which is how a feature
gets configured wrong and then blamed.

So: three labelled groups, each with a sentence saying what the group is for,
and the numbers beside the switches they belong to.

QUILL renders the same twelve settings from ``settings_specs.py`` into its own
searchable Settings window, which is the right shape there because that window
has four hundred rows and a search box. Both read and write the same names, so a
listener who tunes this in one editor finds the other already tuned.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.spelling.voicing import LETTER_STYLES, SpellAloudPolicy, spell_out
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["edit_spelling_voice"]

#: Uniform padding, matching the other QuillLite dialogs.
_PAD = 8

#: The bounds every millisecond field is clamped to. Generous at the top on
#: purpose: a listener on a slow synthesiser genuinely waits longer than three
#: seconds to hear a word out, and the number that makes the feature usable for
#: them should not be un-typeable.
_MIN_MS = 100
_MAX_MS = 5000


def edit_spelling_voice(
    parent: wx.Window,
    settings: Any,
    *,
    announce: Callable[[str], None] | None = None,
) -> bool:
    """Edit how misspellings are announced. ``True`` when something changed.

    Mutates *settings* in place and reports whether anything moved, so the
    caller saves and re-applies exactly once -- the same contract Preferences
    has.
    """
    dialog = wx.Dialog(parent, title="Spelling Announcements", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    root.Add(
        wx.StaticText(
            dialog,
            label=(
                "A misspelled word and the correct one usually sound identical, so\n"
                "the letters are the part that answers the question."
            ),
        ),
        0,
        wx.ALL,
        _PAD,
    )

    # -- While you type ---------------------------------------------------- #
    typing_box = wx.StaticBoxSizer(wx.VERTICAL, dialog, "While you are typing")
    # Parented to the box, not the dialog: wx asserts on the other way
    # round and lays the group out wrong on Windows.
    typing_panel = typing_box.GetStaticBox()
    sound = wx.CheckBox(typing_panel, label="Play a &sound when you finish a misspelled word")
    sound.SetHelpText(
        "A short falling blip when a completed word is not in the dictionary. A "
        "sound rather than speech on purpose: speech would interrupt the sentence "
        "it is commenting on. Turn it off for silence; the status bar still says "
        "so, and F7 still finds everything."
    )
    sound.SetValue(bool(getattr(settings, "spelling_alert_sound", True)))
    typing_box.Add(sound, 0, wx.ALL, _PAD // 2)

    speech = wx.CheckBox(typing_panel, label="Also sa&y the word")
    speech.SetHelpText(
        "Speak the misspelling as well as the sound. Off by default and "
        "deliberately: an interruption while you are composing costs more than it "
        "tells you, and the same word is one Shift+F7 away."
    )
    speech.SetValue(bool(getattr(settings, "spelling_alert_speech", False)))
    typing_box.Add(speech, 0, wx.ALL, _PAD // 2)

    repeat_label = wx.StaticText(
        typing_panel, label="Shortest gap before &repeating the same word (milliseconds):"
    )
    repeat = wx.SpinCtrl(
        typing_panel,
        min=0,
        max=10000,
        initial=int(getattr(settings, "spelling_alert_repeat_ms", 750)),
    )
    set_accessible_name(repeat, "Shortest gap before repeating the same word, milliseconds")
    repeat.SetHelpText(
        "Stops one stubborn name becoming a drum while you edit around it. Zero "
        "means alert every time."
    )
    typing_box.Add(repeat_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    typing_box.Add(repeat, 0, wx.LEFT | wx.BOTTOM, _PAD // 2)
    root.Add(typing_box, 0, wx.EXPAND | wx.ALL, _PAD)

    # -- Spelling the word out --------------------------------------------- #
    letters_box = wx.StaticBoxSizer(wx.VERTICAL, dialog, "Spelling a word out")
    letters_panel = letters_box.GetStaticBox()
    enabled = wx.CheckBox(letters_panel, label="Spell misspelled words out &letter by letter")
    enabled.SetHelpText(
        "After a misspelled word is announced, spell it out after a pause. Without "
        "this you are told a word you cannot tell from the correct one, because "
        "the two sound the same."
    )
    enabled.SetValue(bool(getattr(settings, "spell_aloud_enabled", True)))
    letters_box.Add(enabled, 0, wx.ALL, _PAD // 2)

    style_label = wx.StaticText(letters_panel, label="How letters are s&poken:")
    style_choice = wx.Choice(letters_panel, choices=[label for _value, label in LETTER_STYLES])
    set_accessible_name(style_choice, "How letters are spoken")
    style_choice.SetHelpText(
        "Plain letters are fastest. The phonetic alphabet is unambiguous where B, "
        "D, E, P, T and V are one sound with a rumour attached. Both is for "
        "learning a word rather than checking one."
    )
    values = [value for value, _label in LETTER_STYLES]
    current_style = str(getattr(settings, "spell_aloud_style", "letters"))
    style_choice.SetSelection(values.index(current_style) if current_style in values else 0)
    letters_box.Add(style_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    letters_box.Add(style_choice, 0, wx.LEFT, _PAD // 2)

    capitals = wx.CheckBox(letters_panel, label="Say which letters are &capitals")
    capitals.SetHelpText(
        'Prefix an upper-case letter with "cap", so MacDonald and Macdonald are '
        "told apart. Letters are spoken in upper case whatever the word does, "
        "because several voices read a lone lower-case letter as a word."
    )
    capitals.SetValue(bool(getattr(settings, "spell_aloud_capitals", True)))
    letters_box.Add(capitals, 0, wx.ALL, _PAD // 2)

    # A read-only example, which is the whole reason the three style choices are
    # comprehensible: "phonetic alphabet" is a phrase, and "cap M, A, C, cap D"
    # is the thing you will actually hear. It updates as the controls move, and
    # the caller says it out loud -- an unfocused label changing is precisely
    # what a screen reader does not read by itself.
    example = wx.TextCtrl(letters_panel, value="", style=wx.TE_READONLY)
    set_accessible_name(example, "Example")
    example.SetHelpText("What MacDonald would sound like with the choices above.")
    example_label = wx.StaticText(letters_panel, label="&Example:")
    letters_box.Add(example_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    letters_box.Add(example, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD // 2)
    root.Add(letters_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

    def _example_text() -> str:
        return spell_out(
            "MacDonald",
            style=values[max(0, style_choice.GetSelection())],
            capitals=bool(capitals.GetValue()),
        )

    def _refresh_example(*, speak: bool) -> None:
        text = _example_text()
        if example.GetValue() == text:
            return
        example.SetValue(text)
        if speak and announce is not None:
            announce(text)

    style_choice.Bind(wx.EVT_CHOICE, lambda _e: _refresh_example(speak=True))
    capitals.Bind(wx.EVT_CHECKBOX, lambda _e: _refresh_example(speak=True))
    _refresh_example(speak=False)

    # -- When it happens ---------------------------------------------------- #
    when_box = wx.StaticBoxSizer(wx.VERTICAL, dialog, "When the letters follow")
    when_panel = when_box.GetStaticBox()
    review_label = wx.StaticText(when_panel, label="Pause in the spelling re&view (milliseconds):")
    review_delay = wx.SpinCtrl(
        when_panel,
        min=_MIN_MS,
        max=_MAX_MS,
        initial=int(getattr(settings, "spell_aloud_delay_ms", 800)),
    )
    set_accessible_name(review_delay, "Pause in the spelling review, milliseconds")
    review_delay.SetHelpText(
        "How long after a word is announced before it is spelled out. The pause is "
        "what lets you move on before the spelling starts: press the next key and "
        "it is cancelled unheard."
    )
    when_box.Add(review_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    when_box.Add(review_delay, 0, wx.LEFT, _PAD // 2)

    navigation = wx.CheckBox(when_panel, label="Spell the word when you &move to a misspelling")
    navigation.SetHelpText(
        "Spell out each misspelling you reach with Next or Previous Misspelling. "
        "Your screen reader reads the word itself because it is selected; this "
        "adds the part it cannot know, which is which letters are wrong."
    )
    navigation.SetValue(bool(getattr(settings, "spell_aloud_on_navigation", True)))
    when_box.Add(navigation, 0, wx.ALL, _PAD // 2)

    nav_label = wx.StaticText(when_panel, label="Pause when mo&ving between misspellings (ms):")
    nav_delay = wx.SpinCtrl(
        when_panel,
        min=_MIN_MS,
        max=_MAX_MS,
        initial=int(getattr(settings, "spell_aloud_navigation_delay_ms", 600)),
    )
    set_accessible_name(nav_delay, "Pause when moving between misspellings, milliseconds")
    nav_delay.SetHelpText(
        "A separate, shorter pause, because you may be travelling through a "
        "document rather than stopped and deciding."
    )
    when_box.Add(nav_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    when_box.Add(nav_delay, 0, wx.LEFT, _PAD // 2)

    suggestions = wx.CheckBox(when_panel, label="Spell each su&ggestion as you arrow through them")
    suggestions.SetHelpText(
        "Choosing between two spellings by ear is exactly as impossible in a list "
        "of corrections as it is in the document. Arrowing on cancels it."
    )
    suggestions.SetValue(bool(getattr(settings, "spell_aloud_suggestions", True)))
    when_box.Add(suggestions, 0, wx.ALL, _PAD // 2)

    sug_label = wx.StaticText(when_panel, label="Pause before spelling a s&uggestion (ms):")
    sug_delay = wx.SpinCtrl(
        when_panel,
        min=_MIN_MS,
        max=_MAX_MS,
        initial=int(getattr(settings, "spell_aloud_suggestion_delay_ms", 600)),
    )
    set_accessible_name(sug_delay, "Pause before spelling a suggestion, milliseconds")
    sug_delay.SetHelpText("How long to wait after landing on a suggestion before spelling it.")
    when_box.Add(sug_label, 0, wx.LEFT | wx.TOP, _PAD // 2)
    when_box.Add(sug_delay, 0, wx.LEFT, _PAD // 2)

    first = wx.CheckBox(when_panel, label="Spell the &first suggestion on arrival")
    first.SetHelpText(
        "When the review reaches a new misspelling, spell the top suggestion as "
        "well as the word. Off by default: it doubles the arrival announcement, "
        "which is welcome when you are learning a word and noise when you are "
        "checking one."
    )
    first.SetValue(bool(getattr(settings, "spell_aloud_first_suggestion", False)))
    when_box.Add(first, 0, wx.ALL, _PAD // 2)
    root.Add(when_box, 0, wx.EXPAND | wx.ALL, _PAD)

    # No access key on OK or Cancel: Enter and Escape already serve them, and
    # every letter they give up resolves a collision elsewhere (GATE-14).
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    sound.SetFocus()
    try:
        if show_modal_dialog(dialog, "Spelling Announcements") != wx.ID_OK:
            return False
        before = _snapshot(settings)
        settings.spelling_alert_sound = bool(sound.GetValue())
        settings.spelling_alert_speech = bool(speech.GetValue())
        settings.spelling_alert_repeat_ms = int(repeat.GetValue())
        settings.spell_aloud_enabled = bool(enabled.GetValue())
        settings.spell_aloud_style = values[max(0, style_choice.GetSelection())]
        settings.spell_aloud_capitals = bool(capitals.GetValue())
        settings.spell_aloud_delay_ms = int(review_delay.GetValue())
        settings.spell_aloud_on_navigation = bool(navigation.GetValue())
        settings.spell_aloud_navigation_delay_ms = int(nav_delay.GetValue())
        settings.spell_aloud_suggestions = bool(suggestions.GetValue())
        settings.spell_aloud_suggestion_delay_ms = int(sug_delay.GetValue())
        settings.spell_aloud_first_suggestion = bool(first.GetValue())
        settings.normalized()
        return _snapshot(settings) != before
    finally:
        dialog.Destroy()


def _snapshot(settings: Any) -> tuple[SpellAloudPolicy, tuple[bool, bool, int]]:
    """Everything this window can change, as one comparable value.

    The policy object rather than a hand-written tuple, so a field added to the
    policy is compared here without anybody remembering to add it -- the failure
    mode being a window that says "nothing changed" and quietly does not save.
    """
    return SpellAloudPolicy(
        enabled=bool(getattr(settings, "spell_aloud_enabled", True)),
        delay_ms=int(getattr(settings, "spell_aloud_delay_ms", 800)),
        navigation=bool(getattr(settings, "spell_aloud_on_navigation", True)),
        navigation_delay_ms=int(getattr(settings, "spell_aloud_navigation_delay_ms", 600)),
        suggestions=bool(getattr(settings, "spell_aloud_suggestions", True)),
        suggestion_delay_ms=int(getattr(settings, "spell_aloud_suggestion_delay_ms", 600)),
        first_suggestion=bool(getattr(settings, "spell_aloud_first_suggestion", False)),
        style=str(getattr(settings, "spell_aloud_style", "letters")),
        capitals=bool(getattr(settings, "spell_aloud_capitals", True)),
    ), (
        bool(getattr(settings, "spelling_alert_sound", True)),
        bool(getattr(settings, "spelling_alert_speech", False)),
        int(getattr(settings, "spelling_alert_repeat_ms", 750)),
    )
