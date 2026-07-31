from __future__ import annotations

from dataclasses import dataclass

from quill.core.shell_verbs import (
    default_shell_verbs,
    enabled_verbs,
    verb_actions,
    verb_for_action,
    verbs_for_extension,
)


@dataclass
class _FakeSettings:
    shell_verb_ocr: bool = False
    shell_verb_ocr_structured: bool = False
    shell_verb_open: bool = False
    shell_verb_read: bool = False
    shell_verb_convert: bool = False


def test_default_verbs_have_unique_ids_and_actions() -> None:
    verbs = default_shell_verbs()
    assert len(verbs) >= 4
    ids = [verb.verb_id for verb in verbs]
    actions = [verb.action for verb in verbs]
    assert len(set(ids)) == len(ids)
    assert len(set(actions)) == len(actions)


def test_verb_actions_matches_registry() -> None:
    assert set(verb_actions()) == {verb.action for verb in default_shell_verbs()}


def test_verb_for_action_roundtrip() -> None:
    verb = verb_for_action("ocr")
    assert verb is not None
    assert verb.action == "ocr"
    assert verb_for_action("does-not-exist") is None


def test_applies_to_extension_is_case_insensitive() -> None:
    ocr = verb_for_action("ocr")
    assert ocr is not None
    assert ocr.applies_to(".PNG")
    assert ocr.applies_to("png")
    assert not ocr.applies_to(".txt")


def test_verbs_for_extension_filters() -> None:
    text_verbs = {verb.action for verb in verbs_for_extension(".md")}
    assert "open" in text_verbs
    assert "ocr" not in text_verbs


def test_master_toggle_off_returns_nothing() -> None:
    settings = _FakeSettings(shell_verb_ocr=True, shell_verb_open=True)
    assert (
        enabled_verbs(
            settings_values=settings,
            master_enabled=False,
            assistant_enabled=True,
        )
        == []
    )


def test_enabled_verbs_respects_per_verb_toggle() -> None:
    settings = _FakeSettings(shell_verb_open=True)
    active = enabled_verbs(
        settings_values=settings,
        master_enabled=True,
        assistant_enabled=False,
    )
    assert [verb.action for verb in active] == ["open"]


def test_ai_verb_requires_assistant() -> None:
    settings = _FakeSettings(shell_verb_ocr_structured=True)
    without_ai = enabled_verbs(
        settings_values=settings,
        master_enabled=True,
        assistant_enabled=False,
    )
    assert without_ai == []
    with_ai = enabled_verbs(
        settings_values=settings,
        master_enabled=True,
        assistant_enabled=True,
    )
    assert [verb.action for verb in with_ai] == ["ocr-structured"]


def test_convert_verb_present_and_targets_media() -> None:
    verb = verb_for_action("convert")
    assert verb is not None
    assert verb.verb_id == "convert"
    assert verb.settings_key == "shell_verb_convert"
    # Applies to common audio + video containers, not to text/images.
    assert verb.applies_to(".mp3") and verb.applies_to(".mp4")
    assert not verb.applies_to(".txt")


def test_convert_verb_media_matches_engine_extensions() -> None:
    from quill.core.audio.convert import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS
    from quill.core.shell_verbs import MEDIA_EXTENSIONS

    assert set(MEDIA_EXTENSIONS) == set(AUDIO_EXTENSIONS) | set(VIDEO_EXTENSIONS)


def test_convert_verb_enabled_by_its_toggle() -> None:
    active = enabled_verbs(
        settings_values=_FakeSettings(shell_verb_convert=True),
        master_enabled=True,
        assistant_enabled=False,
    )
    assert [verb.action for verb in active] == ["convert"]
