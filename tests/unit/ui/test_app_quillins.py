"""Tests for the companion-app Quillins wiring (composition + capability split).

The heavy wx frame construction is avoided: composition is asserted via the MRO
and source, and the app-neutral / editor-only capability split is exercised
directly on ``_AppHostServices`` (which is wx-free to import).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.quillins.model import CapabilityError
from quill.ui.app_quillins import QuillinsAppMixin
from quill.ui.app_quillins_host import _AppHostServices

_REPO = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (_REPO / rel).read_text(encoding="utf-8")


# -- composition -------------------------------------------------------------


def test_radio_and_cast_compose_the_mixin() -> None:
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.apps.radio import RadioAppFrame

    assert QuillinsAppMixin in RadioAppFrame.__mro__
    assert QuillinsAppMixin in PodcastsAppFrame.__mro__


def test_apps_init_the_host_and_add_the_menu() -> None:
    radio = _read("quill/apps/radio.py")
    # QUILL Cast's menu bar moved to apps/podcasts_menu.py in 1.1.0 (GATE-11).
    cast = _read("quill/apps/podcasts.py") + _read("quill/apps/podcasts_menu.py")
    assert 'self._init_app_quillins("radio")' in radio
    assert 'self._init_app_quillins("cast")' in cast
    assert '_build_quillins_menu(), "&Quillins"' in radio
    assert '_build_quillins_menu(), "&Quillins"' in cast


def test_apps_shut_down_the_host() -> None:
    assert "self._app_host.shutdown()" in _read("quill/apps/radio.py")
    assert "self._app_host.shutdown()" in _read("quill/apps/podcasts.py")


# -- capability split (app-neutral vs editor-only) ---------------------------


class _FakeSettings:
    verbosity_speech_enabled = True


class _FakeFrame:
    settings = _FakeSettings()


def test_editor_only_methods_raise_capability_error() -> None:
    services = _AppHostServices(_FakeFrame())
    for call in (
        services.get_text,
        services.get_selection,
        services.get_cursor,
        services.get_cursor_offset,
        services.get_selection_range,
    ):
        with pytest.raises(CapabilityError):
            call()
    with pytest.raises(CapabilityError):
        services.insert_text("x")
    with pytest.raises(CapabilityError):
        services.set_text("x")
    with pytest.raises(CapabilityError):
        services.replace_range(0, 0, "x")


def test_net_is_not_available_yet() -> None:
    services = _AppHostServices(_FakeFrame())
    with pytest.raises(CapabilityError):
        services.fetch("https://example.com", "GET", None)


def test_app_neutral_verbosity_flag_reads_settings() -> None:
    services = _AppHostServices(_FakeFrame())
    assert services.is_verbosity_speech_enabled() is True
