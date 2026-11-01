"""The family prompt migration at startup (decision 18): which stores, once, never harmful."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import family_prompt_migration as fpm
from quill.core.ai.family_prompts import FamilyPromptStore


def _write(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _lite(tmp_path: Path, prompts: list[dict[str, str]]) -> Path:
    return _write(tmp_path / "lite" / "prompts.json", {"user_prompts": prompts})


def _studio(tmp_path: Path, prompts: list[dict[str, str]]) -> Path:
    return _write(tmp_path / "quill" / "ai" / "assistant-prompts.json", {"prompts": prompts})


def _settings(tmp_path: Path, vision: list[dict[str, str]] | None = None) -> Path:
    return _write(tmp_path / "quill" / "settings.json", {"vision_custom_prompts": vision or []})


def _store(tmp_path: Path) -> FamilyPromptStore:
    return FamilyPromptStore(tmp_path / "quill" / "prompts.json")


def _found(tmp_path: Path) -> list[fpm.FoundSource]:
    return fpm.discover_sources(
        studio=tmp_path / "quill" / "ai" / "assistant-prompts.json",
        quill_settings=tmp_path / "quill" / "settings.json",
        lite=tmp_path / "lite" / "prompts.json",
    )


def test_identical_prompts_merge_into_one(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add("Shared", "Same text {selection}")
    _lite(tmp_path, [{"id": "l1", "name": "Shared", "text": "Same   text {selection}"}])
    _settings(tmp_path)
    report = fpm.run(store, _found(tmp_path))
    assert report is not None and report.merged == ["Shared"]
    assert [p.name for p in store.prompts()] == ["Shared"]


def test_same_name_different_text_keeps_both_the_second_named_by_its_store(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.add("Tighten", "QUILL's own: {selection}")
    _studio(tmp_path, [{"id": "s1", "title": "Tighten", "template": "Studio: {selection}"}])
    _lite(tmp_path, [{"id": "l1", "name": "Tighten", "text": "Lite: {selection}"}])
    _settings(tmp_path, [{"id": "v1", "title": "Chart", "prompt": "Describe the chart"}])
    fpm.run(store, _found(tmp_path))
    names = sorted(p.name for p in store.prompts())
    assert names == [
        "Chart",
        "Tighten",
        "Tighten (from Prompt Studio)",
        "Tighten (from QUILL Lite)",
    ]
    chart = next(p for p in store.prompts() if p.name == "Chart")
    assert chart.needs == ("pictures",)


def test_runs_once_and_never_touches_the_old_files(tmp_path: Path) -> None:
    store = _store(tmp_path)
    lite = _lite(tmp_path, [{"id": "l1", "name": "Tighten", "text": "Lite: {selection}"}])
    _settings(tmp_path)
    before = lite.read_bytes()
    assert fpm.run(store, _found(tmp_path)) is not None
    assert fpm.done_labels(store) >= {fpm.LITE_LABEL, fpm.VISION_LABEL}
    # The marker: a second run reads nothing it has already brought in.
    assert fpm.run(store, _found(tmp_path)) is None
    assert len(store.prompts()) == 1
    assert lite.read_bytes() == before


def test_a_store_that_arrives_later_is_brought_in_then(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _settings(tmp_path)
    store.add("Mine", "Mine {selection}")
    fpm.run(store, _found(tmp_path))
    assert fpm.LITE_LABEL not in fpm.done_labels(store)  # not installed yet
    _lite(tmp_path, [{"id": "l1", "name": "Later", "text": "Later {selection}"}])
    report = fpm.run(store, _found(tmp_path))
    assert report is not None and report.added == ["Later"]


def test_a_corrupt_old_file_is_skipped_and_left_for_later(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add("Mine", "Mine {selection}")
    lite = tmp_path / "lite" / "prompts.json"
    lite.parent.mkdir(parents=True)
    lite.write_bytes(b"{not json")
    _settings(tmp_path)
    fpm.run(store, _found(tmp_path))
    assert fpm.LITE_LABEL not in fpm.done_labels(store)
    assert lite.read_bytes() == b"{not json"
    _lite(tmp_path, [{"id": "l1", "name": "Fixed", "text": "Fixed {selection}"}])
    report = fpm.run(store, _found(tmp_path))
    assert report is not None and report.added == ["Fixed"]


def test_a_corrupt_family_store_is_never_rewritten(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.path.parent.mkdir(parents=True)
    store.path.write_bytes(b"[broken")
    _lite(tmp_path, [{"id": "l1", "name": "Tighten", "text": "Lite: {selection}"}])
    assert fpm.run(store, _found(tmp_path)) is None
    assert store.path.read_bytes() == b"[broken"


def test_nothing_to_bring_creates_no_family_folder(tmp_path: Path) -> None:
    """QUILL Lite on a computer without QUILL: no QUILL folder for an empty list."""
    store = FamilyPromptStore(tmp_path / "no-quill-yet" / "prompts.json")
    _lite(tmp_path, [])
    assert fpm.run(store, _found(tmp_path)) is None
    assert not store.path.parent.exists()


def test_run_quietly_logs_and_swallows(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: Any, **_k: Any) -> None:
        raise OSError("disk gone")

    monkeypatch.setattr(fpm, "run", boom)
    assert fpm.run_quietly(cancellation_token=None, operation_id="x") is None


def test_schedule_submits_to_the_task_manager_and_reports_only_arrivals(tmp_path: Path) -> None:
    from quill.core.ai.family_prompts import MigrationReport

    calls: list[tuple[str, Any, dict[str, Any]]] = []
    arrived: list[MigrationReport] = []

    def submit(name: str, func: Any, **kwargs: Any) -> None:
        calls.append((name, func, kwargs))

    assert fpm.schedule(submit, on_done=arrived.append) is True
    name, func, kwargs = calls[0]
    assert name == fpm.TASK_NAME and func is fpm.run_quietly
    kwargs["on_success"]("op", MigrationReport())  # nothing added: nothing said
    kwargs["on_success"]("op", None)
    full = MigrationReport(added=["Tighten"])
    kwargs["on_success"]("op", full)
    assert arrived == [full]


def test_schedule_never_raises() -> None:
    def broken(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("pool shut down")

    assert fpm.schedule(broken) is False


# -- the startup wiring, in both editors ------------------------------------- #


def test_quill_runs_it_in_its_deferred_startup_list() -> None:
    source = (Path(__file__).resolve().parents[4] / "quill/ui/main_frame.py").read_text(
        encoding="utf-8"
    )
    assert '("family prompts", self._start_family_prompt_migration)' in source


def test_quills_hook_schedules_on_its_task_manager_and_drops_the_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui.main_frame_hosted_ai import HostedAiCommandsMixin

    submitted: list[str] = []

    class _Pool:
        def submit(self, name: str, _func: Any, **_kwargs: Any) -> None:
            submitted.append(name)

    frame = HostedAiCommandsMixin.__new__(HostedAiCommandsMixin)
    frame._safe_mode = False
    frame._task_manager = _Pool()
    frame._prompt_library_cache = object()
    frame._start_family_prompt_migration()
    assert submitted == [fpm.TASK_NAME]
    frame._family_prompts_arrived(None)
    assert "_prompt_library_cache" not in frame.__dict__
    frame._safe_mode = True
    frame._start_family_prompt_migration()
    assert submitted == [fpm.TASK_NAME]  # Safe Mode: not run


def test_quill_lite_runs_it_at_startup_while_its_ai_area_is_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.apps.lite_window_open as lwo
    from quill.apps.lite_services import LiteServicesMixin

    submitted: list[str] = []

    class _Pool:
        def submit(self, name: str, _func: Any, **_kwargs: Any) -> None:
            submitted.append(name)

    monkeypatch.setattr(lwo, "app_task_manager", lambda _app: _Pool())

    class _App(LiteServicesMixin):
        on = True

        def feature_enabled(self, area_id: str) -> bool:
            return self.on and area_id == "hosted_ai"

    app = _App()
    app._start_family_prompt_migration()
    assert submitted == [fpm.TASK_NAME]
    app.on = False
    app._start_family_prompt_migration()
    assert submitted == [fpm.TASK_NAME]
    source = (Path(__file__).resolve().parents[4] / "quill/apps/lite.py").read_text(
        encoding="utf-8"
    )
    assert "self._start_family_prompt_migration()" in source


def test_every_prompt_library_reads_the_family_store(tmp_path: Path) -> None:
    from quill.core.ai.family_prompts import family_store_path
    from quill.ui.hosted_ai_answers import AiAnswersMixin

    holder = AiAnswersMixin.__new__(AiAnswersMixin)
    library = holder._ai_prompt_library()
    assert Path(library._path) == family_store_path()
