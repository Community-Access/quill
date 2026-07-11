"""Smoke + flow tests for the AI Setup Wizard."""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

import quill.core.ai.onboarding as ob  # noqa: E402
from quill.ui.ai_setup_wizard import (  # noqa: E402
    _STEP_CONFIG,
    _STEP_DONE,
    _STEP_MODEL,
    _STEP_PATH,
    AISetupWizard,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _wizard(wx_app):
    frame = wx.Frame(None)
    dlg = AISetupWizard(frame)
    return frame, dlg


def test_prose_is_readonly_edit_and_no_stray_panel(wx_app):
    # Screen-reader fixes: wizard prose must be navigable read-only edit controls
    # (not StaticText), and there must be no intermediate container panel (it became
    # a stray keyboard tab stop). Controls parent directly on the dialog.
    frame, dlg = _wizard(wx_app)
    try:
        for step in range(5):
            dlg._step = step
            dlg._render()
            kids = dlg.dialog.GetChildren()
            assert not any(isinstance(c, wx.Panel) for c in kids), f"stray panel on step {step}"
            ro_edits = [
                c
                for c in kids
                if isinstance(c, wx.TextCtrl) and (c.GetWindowStyleFlag() & wx.TE_READONLY)
            ]
            assert ro_edits, f"step {step} prose should be a read-only edit control"
    finally:
        dlg.close()
        frame.Destroy()


def test_cloud_flow_add_provider_then_pick_model(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    applied = {}
    monkeypatch.setattr(ob, "apply_cloud_setup", lambda p, k, **kw: applied.update(p=p, k=k, **kw))
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    monkeypatch.setattr(ob, "stored_provider_key", lambda p: "sk-test")
    try:
        dlg._added = []  # deterministic regardless of machine config
        # Welcome -> Path
        dlg._go_next()
        assert dlg._step == _STEP_PATH
        # Choose cloud (find by id; order is cloud-first) -> Config
        cloud_idx = next(i for i, p in enumerate(ob.ONBOARDING_PATHS) if p.id == "cloud")
        dlg._path_choice.SetSelection(cloud_idx)
        dlg._on_path_changed(None)
        assert dlg._path == "cloud"
        dlg._go_next()
        assert dlg._step == _STEP_CONFIG
        # Next with nothing added stays on config and asks for a provider.
        dlg._go_next()
        assert dlg._step == _STEP_CONFIG
        assert "provider" in dlg._status.GetLabel().lower()
        # Simulate a successful verify+add (skip the async probe), then advance.
        opt = ob.CLOUD_PROVIDER_OPTIONS[0]
        dlg._on_verify_result(opt.id, opt.name, "sk-test", True, "")
        assert (opt.id, opt.name) in dlg._added
        dlg._go_next()
        assert dlg._step == _STEP_MODEL
        # Finishing verifies the chosen model first; simulate a passing check -> applies.
        dlg._model = dlg._selected_model()
        dlg._on_model_verified(True, "")
        assert dlg._step == _STEP_DONE
        assert applied["p"] == opt.id and applied["k"] == "sk-test"
        assert applied["model"]  # a model was chosen
    finally:
        dlg.close()
        frame.Destroy()


def test_consent_checkbox_gates_add(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    granted = []
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    monkeypatch.setattr(ob, "grant_provider_consent", lambda pid: granted.append(pid))
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        # Pick a keyed (cloud) provider so a key + consent are both required.
        avail = dlg._available_providers()
        keyed_idx = next(i for i, o in enumerate(avail) if not o.local)
        dlg._provider_choice.SetSelection(keyed_idx)
        dlg._on_provider_changed(None)
        dlg._key_ctrl.SetValue("sk-test")
        # Allow box unchecked -> add is refused, nothing consented or added.
        dlg._consent_cb.SetValue(False)
        dlg._verify_and_add()
        assert "allow" in dlg._status.GetLabel().lower()
        assert granted == [] and dlg._added == []
        # A successful add grants standing consent for that provider.
        dlg._on_verify_result(avail[keyed_idx].id, avail[keyed_idx].name, "sk-test", True, "")
        assert avail[keyed_idx].id in granted
        assert (avail[keyed_idx].id, avail[keyed_idx].name) in dlg._added
    finally:
        dlg.close()
        frame.Destroy()


def test_model_verification_failure_keeps_user_on_step(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    applied = {}
    monkeypatch.setattr(ob, "apply_cloud_setup", lambda *a, **k: applied.update(done=True))
    try:
        dlg._added = [("claude", "Claude (Anthropic)")]
        dlg._provider, dlg._provider_name = "claude", "Claude (Anthropic)"
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        dlg._model = dlg._selected_model()
        # A model that doesn't respond must not be saved; the user stays on the step.
        dlg._on_model_verified(False, "model not found")
        assert dlg._step == _STEP_MODEL
        assert "model not found" in dlg._status.GetLabel().lower()
        assert applied == {}
    finally:
        dlg.close()
        frame.Destroy()


def test_cloud_add_then_remove_provider(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    monkeypatch.setattr(ob, "forget_provider_key", lambda *a, **k: None)
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        opt = ob.CLOUD_PROVIDER_OPTIONS[0]
        # Add removes it from the available combo and lists it.
        dlg._on_verify_result(opt.id, opt.name, "sk-test", True, "")
        assert (opt.id, opt.name) in dlg._added
        assert opt.name not in dlg._provider_choice.GetStrings()
        assert opt.name in dlg._added_list.GetStrings()
        # Remove puts it back in the combo and clears it from the list.
        dlg._added_list.SetSelection(0)
        dlg._remove_selected()
        assert dlg._added == []
        assert opt.name in dlg._provider_choice.GetStrings()
    finally:
        dlg.close()
        frame.Destroy()


def test_config_step_focus_always_lands_on_provider_combo(wx_app, monkeypatch):
    # Landing in the API key field (because the first available-to-add provider happened
    # to need a key) was disorienting -- the provider combo is the step's actual starting
    # point, regardless of whether that provider needs a key.
    frame, dlg = _wizard(wx_app)
    monkeypatch.setattr(ob, "forget_provider_key", lambda *a, **k: None)
    try:
        # Ollama already added (e.g. a reachable local server), so the first available
        # provider to pick from the combo is a keyed cloud one.
        dlg._added = [("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)]
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        assert not dlg._key_ctrl.HasFocus()
        assert dlg._provider_choice.HasFocus()

        # Same expectation after a remove-triggered re-render.
        dlg._added_list.SetSelection(0)
        dlg._remove_selected()
        assert dlg._provider_choice.HasFocus()
    finally:
        dlg.close()
        frame.Destroy()


def test_remove_button_disabled_until_something_is_selected(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        opt = ob.CLOUD_PROVIDER_OPTIONS[0]
        dlg._on_verify_result(opt.id, opt.name, "sk-test", True, "")
        # A non-empty Added list must not enable Remove until an entry is selected.
        assert dlg._added
        assert not dlg._remove_btn.IsEnabled()
        dlg._added_list.SetSelection(0)
        dlg._on_added_list_selection(None)
        assert dlg._remove_btn.IsEnabled()
    finally:
        dlg.close()
        frame.Destroy()


def test_model_step_list_all_models_repopulates_combo(wx_app):
    frame, dlg = _wizard(wx_app)
    try:
        dlg._added = [("ollama_cloud", "Ollama Cloud")]
        dlg._provider, dlg._provider_name = "ollama_cloud", "Ollama Cloud"
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        before = dlg._model_combo.GetCount()
        # Simulate the async result of "List all available models" (no network).
        dlg._on_models_listed(["gemma3:12b", "llama3.1:70b", "qwen2.5:32b", "phi4"], "")
        assert dlg._model_combo.GetCount() == 4 > before
        assert dlg._model_combo.GetValue() == "gemma3:12b"  # kept the in-list current value
        # An error with no models is surfaced and leaves the combo usable.
        dlg._on_models_listed([], "connection refused")
        assert "refused" in dlg._status.GetLabel().lower()
    finally:
        dlg.close()
        frame.Destroy()


def test_skip_path_jumps_to_done_without_configuring(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    calls = []
    monkeypatch.setattr(ob, "apply_cloud_setup", lambda *a, **k: calls.append("cloud"))
    monkeypatch.setattr(ob, "apply_on_device_setup", lambda *a, **k: calls.append("device"))
    try:
        dlg._go_next()  # -> path
        # Select "Not right now" (skip is index 2)
        skip_idx = next(i for i, p in enumerate(ob.ONBOARDING_PATHS) if p.id == "skip")
        dlg._path_choice.SetSelection(skip_idx)
        dlg._on_path_changed(None)
        dlg._go_next()  # skip -> done directly
        assert dlg._step == _STEP_DONE
        assert calls == []  # nothing configured
    finally:
        dlg.close()
        frame.Destroy()


def test_local_ollama_add_then_finish_uses_on_device_setup(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)
    applied = {}

    def _on_device(**k):
        applied.update(model=k.get("model", ""))

    monkeypatch.setattr(ob, "apply_on_device_setup", _on_device)
    monkeypatch.setattr(ob, "apply_cloud_setup", lambda *a, **k: applied.update(cloud=True))
    monkeypatch.setattr(ob, "ollama_installed_models", lambda host="": [])
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        name = ob.ONDEVICE_PROVIDER_OPTION.name
        # Ollama not running -> not added; friendly guidance surfaced, no key needed.
        dlg._on_verify_result("ollama", name, "", False, "Ollama isn't running on this computer.")
        assert dlg._added == []
        assert "ollama" in dlg._status.GetLabel().lower()
        # Ollama present -> added with no key.
        dlg._on_verify_result("ollama", name, "", True, "")
        assert ("ollama", name) in dlg._added
        # Default-provider/model step, then finish -> applies on-device (not cloud) setup.
        dlg._go_next()
        assert dlg._step == _STEP_MODEL
        dlg._model = dlg._selected_model()
        dlg._on_model_verified(True, "")
        assert dlg._step == _STEP_DONE
        assert applied.get("model") and "cloud" not in applied
    finally:
        dlg.close()
        frame.Destroy()


def test_ollama_host_field_enabled_only_for_local_and_is_verified_against(wx_app, monkeypatch):
    # The host field is Ollama's counterpart to the API key field: editable only for
    # the on-device option, and a custom (e.g. remote/LAN) address must actually be
    # used when verifying -- not silently ignored in favor of localhost.
    import quill.ui.ai_setup_wizard as wizard_mod

    class _SyncThread:
        def __init__(self, target=None, **kw):
            self._target = target

        def start(self) -> None:
            if self._target:
                self._target()

    monkeypatch.setattr(wizard_mod.threading, "Thread", _SyncThread)
    monkeypatch.setattr(wizard_mod.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    seen_hosts: list[str] = []
    monkeypatch.setattr(
        ob,
        "ollama_status",
        lambda host="http://localhost:11434": (seen_hosts.append(host), (True, "", "m"))[1],
    )
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    monkeypatch.setattr(ob, "grant_provider_consent", lambda *a, **k: None)

    frame, dlg = _wizard(wx_app)
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        available = dlg._available_providers()
        local_idx = next(i for i, o in enumerate(available) if o.local)
        dlg._provider_choice.SetSelection(local_idx)
        dlg._on_provider_changed(None)
        assert dlg._ollama_host_ctrl.IsEnabled()

        # A cloud provider disables the host field again.
        cloud_idx = next(i for i, o in enumerate(available) if not o.local)
        dlg._provider_choice.SetSelection(cloud_idx)
        dlg._on_provider_changed(None)
        assert not dlg._ollama_host_ctrl.IsEnabled()

        # Back to local, type a remote address, and verify -- the network call must
        # receive exactly what was typed, not a silently-ignored localhost default.
        dlg._provider_choice.SetSelection(local_idx)
        dlg._on_provider_changed(None)
        dlg._ollama_host_ctrl.SetValue("http://192.168.1.50:11434")
        dlg._consent_cb.SetValue(True)
        dlg._verify_and_add()
        assert seen_hosts == ["http://192.168.1.50:11434"]
        assert dlg._ollama_host == "http://192.168.1.50:11434"
    finally:
        dlg.close()
        frame.Destroy()


def test_pull_section_offers_only_uninstalled_recommendations(wx_app, monkeypatch):
    from quill.core.ai.providers import recommended_model_guidance

    frame, dlg = _wizard(wx_app)
    guidance = recommended_model_guidance("ollama")
    assert len(guidance) >= 2  # the fixture below assumes at least two curated models
    already_installed = guidance[0].model
    monkeypatch.setattr(ob, "ollama_installed_models", lambda host="": [already_installed])
    try:
        dlg._added = [("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)]
        dlg._provider, dlg._provider_name = "ollama", ob.ONDEVICE_PROVIDER_OPTION.name
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        assert already_installed not in dlg._pull_models
        assert set(dlg._pull_models) == {g.model for g in guidance if g.model != already_installed}
    finally:
        dlg.close()
        frame.Destroy()


def test_pull_model_success_selects_it_as_the_model(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)

    class _SyncThread:
        def __init__(self, target=None, **kw):
            self._target = target

        def start(self) -> None:
            if self._target:
                self._target()

    import quill.ui.ai_setup_wizard as wizard_mod

    monkeypatch.setattr(wizard_mod.threading, "Thread", _SyncThread)
    monkeypatch.setattr(wizard_mod.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(ob, "ollama_installed_models", lambda host="": [])
    pulled: dict[str, str] = {}

    def _fake_pull(model, *, host, on_progress=None, **kw):
        pulled["model"] = model
        if on_progress is not None:
            on_progress("downloading -- 50%")
        return True, ""

    monkeypatch.setattr(ob, "pull_ollama_model", _fake_pull)
    try:
        dlg._added = [("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)]
        dlg._provider, dlg._provider_name = "ollama", ob.ONDEVICE_PROVIDER_OPTION.name
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        target_model = dlg._pull_models[0]
        dlg._pull_choice.SetSelection(0)
        dlg._pull_selected_model()
        assert pulled["model"] == target_model
        assert dlg._model == target_model
        assert dlg._model_combo.GetValue() == target_model
    finally:
        dlg.close()
        frame.Destroy()


def test_pull_model_failure_reenables_button_and_reports_status(wx_app, monkeypatch):
    frame, dlg = _wizard(wx_app)

    class _SyncThread:
        def __init__(self, target=None, **kw):
            self._target = target

        def start(self) -> None:
            if self._target:
                self._target()

    import quill.ui.ai_setup_wizard as wizard_mod

    monkeypatch.setattr(wizard_mod.threading, "Thread", _SyncThread)
    monkeypatch.setattr(wizard_mod.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(ob, "ollama_installed_models", lambda host="": [])
    monkeypatch.setattr(
        ob, "pull_ollama_model", lambda model, *, host, on_progress=None, **kw: (False, "disk full")
    )
    try:
        dlg._added = [("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)]
        dlg._provider, dlg._provider_name = "ollama", ob.ONDEVICE_PROVIDER_OPTION.name
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        dlg._pull_choice.SetSelection(0)
        dlg._pull_selected_model()
        assert "disk full" in dlg._status.GetLabel()
        assert dlg._pull_btn.IsEnabled()
    finally:
        dlg.close()
        frame.Destroy()


def test_never_configured_default_does_not_hide_ollama(wx_app, monkeypatch):
    # The connection settings default to provider="ollama" even when AI has never
    # been touched (a fresh/never-saved settings file loads that default), and this
    # is what a brand-new install looks like. Priming must not mistake that default
    # for "the user already added Ollama" when no local server actually answers --
    # otherwise Ollama silently disappears from the picker and only key-requiring
    # cloud providers remain, forcing a key entry for a user who has Ollama locally
    # (or hasn't installed it yet and just wants to see the option).
    import quill.core.assistant_ai as assistant_ai
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setattr(ob, "configured_cloud_providers", lambda: [])
    monkeypatch.setattr(ob, "active_cloud_selection", lambda: ("", ""))
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: AssistantConnectionSettings(),  # the untouched default: provider="ollama"
    )
    monkeypatch.setattr(ob, "ollama_status", lambda host: (False, "not reachable", ""))
    frame, dlg = _wizard(wx_app)
    try:
        assert dlg._added == []
        ids = {opt.id for opt in dlg._available_providers()}
        assert "ollama" in ids
    finally:
        dlg.close()
        frame.Destroy()


def test_reachable_ollama_default_is_primed_as_added(wx_app, monkeypatch):
    # The mirror case: when a local Ollama server genuinely answers, the default
    # connection settings pointing at it IS meaningful, and priming should still
    # pre-add it so a relaunch of the wizard remembers a real on-device setup.
    import quill.core.assistant_ai as assistant_ai
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setattr(ob, "configured_cloud_providers", lambda: [])
    monkeypatch.setattr(ob, "active_cloud_selection", lambda: ("", ""))
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: AssistantConnectionSettings(),
    )
    monkeypatch.setattr(ob, "ollama_status", lambda host: (True, "", "llama3.2:1b"))
    frame, dlg = _wizard(wx_app)
    try:
        assert ("ollama", ob.ONDEVICE_PROVIDER_OPTION.name) in dlg._added
    finally:
        dlg.close()
        frame.Destroy()


def test_remove_then_readd_ollama_never_asks_for_a_key(wx_app, monkeypatch):
    # Reported symptom: after removing Ollama from Added and trying to add it again,
    # the key field kept demanding an API key. Exercise the REAL _verify_and_add()
    # path (not the _on_verify_result shortcut the other tests use) so a bug in how
    # opt.local is resolved on the second pass would actually surface.
    import quill.ui.ai_setup_wizard as wizard_mod

    class _SyncThread:
        def __init__(self, target=None, **kw):
            self._target = target

        def start(self) -> None:
            if self._target:
                self._target()

    monkeypatch.setattr(wizard_mod.threading, "Thread", _SyncThread)
    monkeypatch.setattr(wizard_mod.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(ob, "ollama_status", lambda host="http://localhost:11434": (True, "", "m"))
    monkeypatch.setattr(ob, "remember_provider_key", lambda *a, **k: None)
    monkeypatch.setattr(ob, "grant_provider_consent", lambda *a, **k: None)
    monkeypatch.setattr(ob, "forget_provider_key", lambda *a, **k: None)

    frame, dlg = _wizard(wx_app)
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()

        def _add_ollama_via_real_button() -> None:
            available = dlg._available_providers()
            local_idx = next(i for i, o in enumerate(available) if o.local)
            dlg._provider_choice.SetSelection(local_idx)
            dlg._on_provider_changed(None)
            assert not dlg._key_ctrl.IsEnabled(), "key field must stay disabled for local Ollama"
            dlg._consent_cb.SetValue(True)
            dlg._verify_and_add()  # the actual "Verify and add provider" button handler

        _add_ollama_via_real_button()
        assert ("ollama", ob.ONDEVICE_PROVIDER_OPTION.name) in dlg._added

        # Remove it via the real button path (select in the list first, like a user would).
        idx = dlg._added_list.FindString(ob.ONDEVICE_PROVIDER_OPTION.name)
        assert idx != wx.NOT_FOUND
        dlg._added_list.SetSelection(idx)
        dlg._remove_selected()
        assert dlg._added == []

        # Add it again -- must not require a key this second time either.
        _add_ollama_via_real_button()
        assert ("ollama", ob.ONDEVICE_PROVIDER_OPTION.name) in dlg._added
        assert "api key" not in dlg._status.GetLabel().lower()
    finally:
        dlg.close()
        frame.Destroy()


def test_get_api_key_opens_provider_signup(wx_app, monkeypatch):
    import webbrowser

    frame, dlg = _wizard(wx_app)
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: opened.append(url) or True)
    try:
        dlg._added = []
        dlg._path = "cloud"
        dlg._step = _STEP_CONFIG
        dlg._render()
        # Select a keyed provider; Get API key opens exactly its signup_url.
        avail = dlg._available_providers()
        keyed_idx = next(i for i, o in enumerate(avail) if not o.local)
        dlg._provider_choice.SetSelection(keyed_idx)
        dlg._on_provider_changed(None)
        assert dlg._get_key_btn.IsEnabled()
        dlg._open_get_api_key()
        assert opened == [avail[keyed_idx].signup_url]
        # On-device Ollama needs no key, so the button is disabled.
        local_idx = next(i for i, o in enumerate(avail) if o.local)
        dlg._provider_choice.SetSelection(local_idx)
        dlg._on_provider_changed(None)
        assert not dlg._get_key_btn.IsEnabled()
    finally:
        dlg.close()
        frame.Destroy()


def test_openrouter_preselects_free_model(wx_app, monkeypatch):
    from quill.core.ai.free_models import best_free_writing_model

    frame, dlg = _wizard(wx_app)
    monkeypatch.setattr(ob, "stored_provider_model", lambda p: "")  # no saved override
    try:
        dlg._added = [("openrouter", "OpenRouter")]
        dlg._provider, dlg._provider_name = "openrouter", "OpenRouter"
        dlg._model = ""  # no explicit selection, so the recommended default leads
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        expected = best_free_writing_model("openrouter")
        assert dlg._model_combo.GetValue() == expected
        assert expected.endswith(":free")
    finally:
        dlg.close()
        frame.Destroy()


def test_finish_persists_experience_mode_and_completion(wx_app, tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "onboarding_state_path", lambda: tmp_path / "ai" / "onboarding.json")
    monkeypatch.setattr(ob, "apply_on_device_setup", lambda *a, **k: None)
    frame, dlg = _wizard(wx_app)
    try:
        dlg._added = [("ollama", ob.ONDEVICE_PROVIDER_OPTION.name)]
        dlg._provider, dlg._provider_name = "ollama", ob.ONDEVICE_PROVIDER_OPTION.name
        dlg._path = "cloud"
        dlg._step = _STEP_MODEL
        dlg._render()
        dlg._model = dlg._selected_model()
        dlg._on_model_verified(True, "")  # applies + advances to done
        assert dlg._step == _STEP_DONE
        # Uncheck "keep it simple" -> advanced mode persisted on finish.
        dlg._basic_cb.SetValue(False)
        dlg._finish()
        assert ob.onboarding_complete() is True
        assert ob.load_experience_mode() == ob.EXPERIENCE_ADVANCED
    finally:
        frame.Destroy()


def test_agent_path_wires_to_the_engines_tab() -> None:
    # Source-contract: the "use an agent you already pay for" path finishes by
    # opening the AI Hub Engines tab (no provider/key config in the wizard).
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    src = (root / "quill" / "ui" / "ai_setup_wizard.py").read_text(encoding="utf-8")
    assert "open_engines_cb" in src
    assert 'initial_page="Engines"' in src
    assert 'self._path in ("skip", "agent")' in src  # agent skips the provider config step
    # The hand-off is deferred (CallAfter) so the modal AI Hub never opens
    # inside the wizard's still-unwinding modal handler (#801 review).
    finish_src = src.split("def _finish", 1)[1].split(chr(10) + "def ", 1)[0]
    assert "CallAfter" in finish_src
    assert "_hand_off" in finish_src
    # The onboarding model offers the agent path.
    from quill.core.ai import onboarding as ob

    assert any(p.id == "agent" for p in ob.ONBOARDING_PATHS)
