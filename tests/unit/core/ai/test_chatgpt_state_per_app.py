"""One ChatGPT sign-in per app, in one shared data folder (2026-10-02).

Every QuillVille app shares one data folder, and the one ``chatgpt.json`` they
all wrote meant the second app to sign in overwrote the first app's client id
and model while each kept its own refresh token. Each app now has its own
file, the legacy file is still read until an app has written its own, and an
app can say which siblings are signed in without pretending to be them.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.chatgpt_account import ChatGptAccount
from quill.core.ai.chatgpt_state import (
    ChatGptState,
    load_state,
    save_state,
    sibling_sign_ins,
    slug_for,
)


def _signed_in(agent: str) -> ChatGptState:
    return ChatGptState(
        client_id="c-" + slug_for(agent), subject="sub", email="a@b.c", agent_name=agent
    )


def test_two_apps_keep_two_files_and_neither_overwrites_the_other(tmp_path: Path) -> None:
    save_state(tmp_path, _signed_in("QUILL Lite"), slug_for("QUILL Lite"))
    save_state(tmp_path, _signed_in("QUILL Cast"), slug_for("QUILL Cast"))
    assert (tmp_path / "ai" / "chatgpt-quill-lite.json").exists()
    assert (tmp_path / "ai" / "chatgpt-quill-cast.json").exists()
    assert load_state(tmp_path, "quill-lite").client_id == "c-quill-lite"
    assert load_state(tmp_path, "quill-cast").client_id == "c-quill-cast"


def test_the_legacy_shared_file_is_read_until_the_app_writes_its_own(tmp_path: Path) -> None:
    save_state(tmp_path, _signed_in("QUILL"))  # the pre-2026-10 shared file
    assert load_state(tmp_path, "quill").signed_in is True
    save_state(tmp_path, ChatGptState(), "quill")  # signed out: the app's own file now rules
    assert load_state(tmp_path, "quill").signed_in is False
    assert load_state(tmp_path).signed_in is True, "the legacy file is left alone"


def test_a_sibling_sign_in_is_reported_by_name_and_is_not_this_apps(tmp_path: Path) -> None:
    save_state(tmp_path, _signed_in("QUILL Lite"), "quill-lite")
    save_state(tmp_path, _signed_in("Quill Radio"), "quill-radio")
    save_state(tmp_path, ChatGptState(), "quill-cast")  # a file, but signed out
    assert sibling_sign_ins(tmp_path, except_slug="quill-cast") == ["QUILL Lite", "Quill Radio"]
    assert sibling_sign_ins(tmp_path, except_slug="quill-lite") == ["Quill Radio"]
    assert sibling_sign_ins(tmp_path / "nowhere") == []
    cast = ChatGptAccount(tmp_path, agent_name="QUILL Cast")
    assert cast.signed_in is False, "a sibling's sign-in never signs this app in"
    assert cast.siblings_signed_in() == ["QUILL Lite", "Quill Radio"]


def test_the_account_stamps_its_own_name_on_what_it_saves(tmp_path: Path) -> None:
    account = ChatGptAccount(tmp_path, agent_name="QUILL Cast")
    account._save(ChatGptState(client_id="c", subject="s"))
    assert load_state(tmp_path, "quill-cast").agent_name == "QUILL Cast"
