"""Tests for the radio debug-mode logging control (quill-radio #5)."""

from __future__ import annotations

import logging

import pytest

from quill.core.radio.radio_logging import (
    RADIO_LOGGER_NAMES,
    radio_debug_enabled,
    set_radio_debug,
)


@pytest.fixture(autouse=True)
def _restore_levels() -> object:
    saved = {name: logging.getLogger(name).level for name in RADIO_LOGGER_NAMES}
    yield
    for name, level in saved.items():
        logging.getLogger(name).setLevel(level)


def test_default_is_off() -> None:
    set_radio_debug(False)
    assert radio_debug_enabled() is False
    for name in RADIO_LOGGER_NAMES:
        assert logging.getLogger(name).level == logging.NOTSET


def test_enabling_raises_the_radio_subtrees_to_debug() -> None:
    set_radio_debug(True)
    assert radio_debug_enabled() is True
    for name in RADIO_LOGGER_NAMES:
        assert logging.getLogger(name).level == logging.DEBUG


def test_disabling_restores_notset_not_info() -> None:
    set_radio_debug(True)
    set_radio_debug(False)
    assert radio_debug_enabled() is False
    for name in RADIO_LOGGER_NAMES:
        # NOTSET (0), not pinned to INFO, so the loggers inherit the root again.
        assert logging.getLogger(name).level == logging.NOTSET


def test_debug_mode_does_not_touch_the_root_logger() -> None:
    root_level = logging.getLogger().level
    set_radio_debug(True)
    assert logging.getLogger().level == root_level  # composes when embedded
