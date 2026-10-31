"""The user's name leaves a crash bundle, as a whole word only.

The rule and both tests are from Kelly Ford's Quick Describe, whose bug
reports write the user name as a placeholder and test that a name inside a
longer word is left alone.
"""

from __future__ import annotations

from quill.stability.redaction import redact_text_for_bundle, redact_user_name


def test_the_name_on_its_own_is_replaced_in_any_case():
    assert redact_user_name("signed in as jeffb, Jeffb again", "jeffb") == (
        "signed in as <user>, <user> again"
    )


def test_a_name_inside_another_word_is_left_alone():
    assert redact_user_name("press Alt+F4, then Also", "Al") == "press Alt+F4, then Also"
    assert redact_user_name("Al pressed Alt", "Al") == "<user> pressed Alt"


def test_a_one_letter_or_missing_name_changes_nothing():
    assert redact_user_name("a b c", "a") == "a b c"
    assert redact_user_name("anything", "") == "anything"


def test_bundles_use_it(monkeypatch):
    monkeypatch.setenv("USERNAME", "kelly")
    assert redact_text_for_bundle("Studio started for kelly\n") == "Studio started for <user>\n"
