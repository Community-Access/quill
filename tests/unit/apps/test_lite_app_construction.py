"""The wx.App itself can be constructed, which no other test checks.

Every other QUILL Lite test builds a stub window (``tests/unit/apps/conftest.py``)
because a real ``wx.App`` needs a display. That is the right trade for testing
commands -- and it left ``QuillLiteApp.__init__`` with no test at all, so on
2026-09-17 it could read ``self.settings`` at line 88 while ``OnInit`` set it at
line 121, and **QUILL Lite did not start**. The only thing that constructs the
real app is the live probe, which is run by hand.

This does not need a display: ``__init__`` is plain Python up to the
``super().__init__`` call, and what broke was in that plain Python. Checking the
attribute order is enough to catch the whole class of fault, which is a
constructor reaching for state a later phase sets.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

LITE = Path(__file__).resolve().parents[3] / "quill" / "apps" / "lite.py"
LITE_STARTUP = Path(__file__).resolve().parents[3] / "quill" / "apps" / "lite_startup.py"
LITE_WRAPPER = (
    Path(__file__).resolve().parents[3] / "standalone" / "quilllite" / "quill_lite" / "__init__.py"
)


def _assigned_and_read(method: str) -> tuple[set[str], set[str]]:
    """``(attributes assigned, attributes read)`` on ``self`` in *method*."""
    tree = ast.parse(LITE.read_text(encoding="utf-8"))
    node = next(
        n
        for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "QuillLiteApp"
        for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name == method
    )
    assigned: set[str] = set()
    read: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            if sub.value.id != "self":
                continue
            (assigned if isinstance(sub.ctx, ast.Store) else read).add(sub.attr)
    return assigned, read


def test_init_never_reads_state_that_oninit_sets() -> None:
    """The fault that stopped QUILL Lite starting, in one assertion.

    ``__init__`` runs before ``OnInit``. An attribute read in the first and
    assigned only in the second is an AttributeError on launch -- and
    ``getattr(self.settings, "x", default)`` does not protect it, because the
    default covers a missing *field*, not a missing ``self.settings``.
    """
    init_assigned, init_read = _assigned_and_read("__init__")
    oninit_assigned, _ = _assigned_and_read("OnInit")

    too_early = sorted((init_read & oninit_assigned) - init_assigned)
    assert too_early == [], (
        f"__init__ reads {too_early}, which OnInit sets later -- QUILL Lite will "
        "raise AttributeError before its first window appears"
    )


def test_settings_is_one_of_the_attributes_oninit_owns() -> None:
    """Guards the guard: if settings ever moved into __init__ the test above
    would pass for the wrong reason, having nothing left to compare."""
    oninit_assigned, _ = _assigned_and_read("OnInit")
    assert "settings" in oninit_assigned


def test_optional_startup_work_waits_for_the_editor() -> None:
    """Audio and service startup must not hold the first window hostage."""
    lite_source = LITE.read_text(encoding="utf-8")
    startup_source = LITE_STARTUP.read_text(encoding="utf-8")
    tree = ast.parse(lite_source)
    methods = {
        n.name: ast.get_source_segment(lite_source, n) or ""
        for cls in ast.walk(tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "QuillLiteApp"
        for n in cls.body
        if isinstance(n, ast.FunctionDef)
    }
    oninit = methods["OnInit"]
    startup_tree = ast.parse(startup_source)
    finish = next(
        ast.get_source_segment(startup_source, node) or ""
        for cls in ast.walk(startup_tree)
        if isinstance(cls, ast.ClassDef) and cls.name == "LiteStartupMixin"
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "_finish_startup"
    )
    assert "init_app_sound" not in oninit
    assert "_load_optional_stores" not in oninit
    assert "claim_instance_marker" not in oninit.split("starting_up = False", 1)[0]
    assert "init_app_sound" in finish
    assert "_start_family_prompt_migration" in finish
    assert "_resume_scribe_queue" in finish


def test_portable_wrapper_enables_fatal_stack_capture_before_importing_lite() -> None:
    source = LITE_WRAPPER.read_text(encoding="utf-8")
    assert source.index("_enable_launch_fault_handler()") < source.index(
        "from quill.apps.lite import main as run"
    )


def test_lite_import_defers_the_network_stack() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import quill.apps.lite, sys; print('quill.core.net' in sys.modules)",
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert result.stdout.strip().endswith("False"), result.stderr


def test_saved_scribe_work_resumes_only_after_feature_check(monkeypatch) -> None:
    from quill.apps import lite_window_scribe
    from quill.apps.lite import QuillLiteApp
    from quill.ui import scribe_controller

    started = []
    host = object()
    monkeypatch.setattr(lite_window_scribe, "LiteScribeHost", lambda _app: host)
    monkeypatch.setattr(
        scribe_controller,
        "controller_for",
        lambda found: SimpleNamespace(start_if_jobs_waiting=lambda: started.append(found is host)),
    )
    app = SimpleNamespace(shutting_down=False, feature_enabled=lambda _area: True)
    QuillLiteApp._resume_scribe_queue(app)
    assert started == [True]
    app.feature_enabled = lambda _area: False
    QuillLiteApp._resume_scribe_queue(app)
    assert started == [True]


def test_stop_background_sources_is_idempotent() -> None:
    from quill.apps.lite import QuillLiteApp

    stopped = []
    app = SimpleNamespace(shutting_down=False)
    app._inbox_timer = SimpleNamespace(Stop=lambda: stopped.append(app.shutting_down))
    app.stop_background_sources = lambda: QuillLiteApp.stop_background_sources(app)
    app.stop_background_sources()
    assert QuillLiteApp.OnExit(app) == 0
    assert stopped == [True]
    assert app._inbox_timer is None


def test_shutdown_leaves_pending_inbox_request_on_disk(monkeypatch, tmp_path) -> None:
    from quill.apps.lite import QuillLiteApp
    from quill.core.lite import inbox

    assert inbox.post_request([tmp_path / "requested.txt"], None, directory=tmp_path)
    read_requests = inbox.read_requests
    monkeypatch.setattr(inbox, "read_requests", lambda: read_requests(tmp_path))
    QuillLiteApp._poll_inbox(SimpleNamespace(shutting_down=True), None)
    assert len(list(tmp_path.glob("*.req"))) == 1


def test_shutdown_during_inbox_processing_preserves_later_requests(monkeypatch) -> None:
    from quill.apps.lite import QuillLiteApp
    from quill.core.lite import inbox

    app = SimpleNamespace(shutting_down=False, settings=SimpleNamespace(default_mode="plain"))
    app.new_window = lambda _mode: setattr(app, "shutting_down", True)
    reposted = []
    monkeypatch.setattr(inbox, "read_requests", lambda: ["NEW", "later.txt", "NEW:rich"])
    monkeypatch.setattr(inbox, "post_request", lambda *args: reposted.append(args))
    QuillLiteApp._poll_inbox(app, None)
    assert reposted == [([Path("later.txt")], None), ([], "rich")]


@pytest.mark.parametrize("can_veto,consent", [(True, False), (True, True), (False, False)])
def test_shell_close_stops_app_sources_only_after_consent(monkeypatch, can_veto, consent) -> None:
    from quill.apps.lite_shell import QuillLiteShell

    calls = []
    child = SimpleNamespace(
        modified=True,
        confirm_discard=lambda: consent,
        stop_timers=lambda: calls.append("child"),
        remember_document_memory=lambda: calls.append("place"),
    )
    app = SimpleNamespace(
        frames=[child],
        remember_session=lambda: calls.append("session"),
        stop_background_sources=lambda: calls.append("app"),
    )
    shell = SimpleNamespace(app=app, Destroy=lambda: calls.append("destroy"))
    event = SimpleNamespace(CanVeto=lambda: can_veto, Veto=lambda: calls.append("veto"))
    monkeypatch.setattr("quill.ui.sound_manager.post_sound_and_wait", lambda *_args: None)
    QuillLiteShell._on_close(shell, event)
    # "place" (FUX-01): each document's cursor, which the shell's Destroy would
    # otherwise take down without the window's own close ever writing it --
    # including the close Windows sends at sign-out, which cannot be vetoed.
    expected = (
        ["veto"] if can_veto and not consent else ["place", "session", "app", "child", "destroy"]
    )
    assert calls == expected
