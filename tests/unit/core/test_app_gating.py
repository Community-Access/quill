"""Gated companion apps must be absent from public surfaces (release sign-off §G).

QUILL, Quill Radio, Quill Weather, and Quill Inkwell are public for 1.0.0; the Media
Player, Quill Cast, Audio Studio, Quill Converter, and QuillBeacon are gated behind
``RELEASED_APPS`` / ``QUILL_DEV_BUILD``.

Inkwell is public because it is the system-wide half of the editor's own abbreviation
expansion and shares one library with it -- gating it would leave that feature visibly
half-present, with abbreviations that work in QUILL and nowhere else.
"""

from __future__ import annotations

import pytest

from quill.core.app_launcher import RELEASED_APPS, is_app_released

PUBLIC = ("quill", "radio", "weather", "inkwell")
GATED = ("player", "cast", "studio", "converter", "beacon")


def test_released_apps_are_only_the_public_set() -> None:
    assert RELEASED_APPS == frozenset({"quill", "radio", "weather", "inkwell"})


def test_public_apps_are_always_released(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    for key in PUBLIC:
        assert is_app_released(key), key


def test_gated_apps_hidden_in_public_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    for key in GATED:
        assert not is_app_released(key), key


def test_developer_build_reveals_every_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    for key in (*PUBLIC, *GATED):
        assert is_app_released(key), key


def test_convert_shell_verb_absent_in_public_build(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.shell_verbs import enabled_verbs

    class _Settings:
        shell_verb_read = True
        shell_verb_convert = True

    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    actions = {
        verb.action
        for verb in enabled_verbs(
            settings_values=_Settings(), master_enabled=True, assistant_enabled=False
        )
    }
    assert "convert" not in actions


def test_gated_apps_not_offered_for_download_in_public(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.companion_install as ci

    monkeypatch.setattr(ci.sys, "frozen", True, raising=False)
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    for key in ("cast", "studio"):
        assert not ci.can_offer_download(key), key
