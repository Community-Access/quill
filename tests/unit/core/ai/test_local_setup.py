"""The guided local-AI journey's wx-free brain (issue #1558)."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai import local_setup as ls


def test_the_four_states_are_three_steps_in_order() -> None:
    nothing = ls.local_ai_setup_status(installed=False, reachable=False)
    assert nothing.stage == ls.STAGE_INSTALL
    assert nothing.step_number == 1
    assert nothing.can_install and not nothing.can_pull and not nothing.can_finish

    installed = ls.local_ai_setup_status(installed=True, reachable=False)
    assert installed.stage == ls.STAGE_START
    assert installed.step_number == 1
    assert not installed.can_install, "'installed but not running' is never fixed by reinstalling"

    empty = ls.local_ai_setup_status(installed=True, reachable=True, models=())
    assert empty.stage == ls.STAGE_MODEL
    assert empty.step_number == 2
    assert empty.can_pull and not empty.can_finish

    ready = ls.local_ai_setup_status(installed=True, reachable=True, models=("llama3.2:1b",))
    assert ready.stage == ls.STAGE_READY
    assert ready.step_number == ls.TOTAL_SETUP_STEPS
    assert ready.can_finish and ready.models == ("llama3.2:1b",)


def test_installed_but_not_running_says_start_not_install() -> None:
    """Collapsing these two produced exactly the #1558 confusion: 'install it'
    is wrong advice to somebody who already did."""
    status = ls.local_ai_setup_status(installed=True, reachable=False)
    assert "not running" in status.headline
    assert "install" not in status.next_step.lower()
    assert "start" in status.next_step.lower()


def test_a_build_that_cannot_install_still_guides() -> None:
    status = ls.local_ai_setup_status(installed=False, reachable=False, install_supported=False)
    assert not status.can_install
    assert "ollama.com" in status.next_step


def test_every_stage_names_the_step_out_of_three() -> None:
    for status in (
        ls.local_ai_setup_status(installed=False, reachable=False),
        ls.local_ai_setup_status(installed=True, reachable=False),
        ls.local_ai_setup_status(installed=True, reachable=True),
        ls.local_ai_setup_status(installed=True, reachable=True, models=("m",)),
    ):
        assert f"of {ls.TOTAL_SETUP_STEPS}" in status.headline
        assert status.next_step, "every stage must name the single next action"


def test_machine_fit_words_the_measurements(monkeypatch) -> None:
    import quill.core.speech.service as service

    monkeypatch.setattr(service, "detect_total_ram_gb", lambda: 16.0)
    monkeypatch.setattr(service, "detect_has_gpu", lambda: False)
    fit = ls.machine_fit()
    assert "16 GB of RAM" in fit.summary
    assert "no graphics card" in fit.summary
    assert fit.total_ram_gb == 16.0 and fit.has_gpu is False


def test_machine_fit_degrades_honestly_when_detection_fails(monkeypatch) -> None:
    import quill.core.speech.service as service

    monkeypatch.setattr(service, "detect_total_ram_gb", lambda: -1.0)
    monkeypatch.setattr(service, "detect_has_gpu", lambda: True)
    fit = ls.machine_fit()
    assert "could not be measured" in fit.summary
    assert "a graphics card" in fit.summary


def test_probe_separates_unreachable_from_empty(monkeypatch) -> None:
    """ollama_status folds 'no server' and 'no models' into one message; the
    journey needs them apart because they are different steps."""
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(
        assistant_ai, "list_assistant_models", lambda *a, **k: ([], "connection refused")
    )
    assert ls.ollama_probe() == (False, [])
    monkeypatch.setattr(assistant_ai, "list_assistant_models", lambda *a, **k: ([], ""))
    assert ls.ollama_probe() == (True, [])
    monkeypatch.setattr(assistant_ai, "list_assistant_models", lambda *a, **k: (["m1", "m2"], ""))
    assert ls.ollama_probe() == (True, ["m1", "m2"])


def test_probe_never_raises(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    def boom(*_a, **_k):
        raise OSError("no network stack at all")

    monkeypatch.setattr(assistant_ai, "list_assistant_models", boom)
    assert ls.ollama_probe() == (False, [])


def test_executable_detection_checks_path_then_the_installer_home(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ls.shutil, "which", lambda _n: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert ls.ollama_executable() is None
    exe = tmp_path / "Programs" / "Ollama" / "ollama.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    assert ls.ollama_executable() == exe
    monkeypatch.setattr(ls.shutil, "which", lambda _n: str(tmp_path / "on-path"))
    assert ls.ollama_executable() == tmp_path / "on-path"


def test_the_download_is_https_and_hardened(monkeypatch, tmp_path) -> None:
    """The installer must go through download_verified (HTTPS-only, Safe-Mode
    gated, atomic), never a bare urlopen."""
    assert ls.OLLAMA_DOWNLOAD_URL.startswith("https://ollama.com/")

    from quill.core import release_assets

    calls = {}

    def fake_download(urls, dest, **kwargs):
        calls["urls"] = list(urls)
        calls["kwargs"] = kwargs
        return Path(dest)

    monkeypatch.setattr(release_assets, "download_verified", fake_download)
    result = ls.download_ollama_installer()
    assert calls["urls"] == [ls.OLLAMA_DOWNLOAD_URL]
    assert calls["kwargs"]["sha256"] == ""  # a moving "latest" URL has no pin
    assert result.suffix == ".exe"
    result.unlink(missing_ok=True)


def test_launching_the_installer_does_not_wait_on_it(monkeypatch, tmp_path) -> None:
    """A GUI installer is driven by the user; a captured, timed subprocess
    call would kill it after 30 seconds mid-prompt."""
    started = {}
    monkeypatch.setattr(ls.subprocess, "Popen", lambda argv: started.setdefault("argv", argv))
    installer = tmp_path / "OllamaSetup.exe"
    ls.launch_ollama_installer(installer)
    assert started["argv"] == [str(installer)]
