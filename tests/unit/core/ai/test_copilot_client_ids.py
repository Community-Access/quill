"""Every QuillVille app that signs in to GitHub Copilot has its own client id.

The table is keyed by agent name, so a name that drifts from the one the app
actually signs in under leaves that app without sign-in and nothing says so:
the Media Player was "QUILL Player" in the table and "QUILL Media Player" in
the app until 2026-11-02. This reads each app's own constant.
"""

from __future__ import annotations

import re

import pytest

from quill.core.ai import copilot_auth


@pytest.mark.parametrize(
    "module_name",
    [
        "quill.ui.radio.radio_ai_host",
        "quill.ui.audio_studio.studio_ai_host",
        "quill.apps.transcribe_ai",
        "quill.apps.converter_ai",
        "quill.apps.player_ai",
        "quill.apps.weather_ai",
        "quill.apps.inkwell_ai",
        "quill.apps.beacon.ai",
    ],
)
def test_each_app_agent_name_has_a_client_id(module_name: str) -> None:
    pytest.importorskip("wx")
    import importlib

    name = importlib.import_module(module_name).AGENT_NAME
    assert copilot_auth.CLIENT_IDS.get(name), f"{module_name}: {name!r} has no client id"


@pytest.mark.parametrize("name", ["QUILL", "QUILL Lite", "QUILL Cast", "QUILL Social"])
def test_the_editors_cast_and_social_have_a_client_id(name: str) -> None:
    assert copilot_auth.CLIENT_IDS.get(name)


def test_every_client_id_looks_like_a_github_oauth_app_id() -> None:
    ids = list(copilot_auth.CLIENT_IDS.values())
    assert len(ids) == 12
    assert all(re.fullmatch(r"Ov23[A-Za-z0-9]{16}", cid) for cid in ids), ids
    assert len(set(ids)) == len(ids), "two apps share a registration"
