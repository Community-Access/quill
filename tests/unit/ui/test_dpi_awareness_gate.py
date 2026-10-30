"""GATE-DPI (#1702): every app is DPI aware, and no size is written in raw pixels.

The two halves have to stay true together. Declaring per-monitor awareness is
what stops Windows stretching (and blurring) every QuillVille app at 150 and
200 percent; but once a process is aware, a size written in plain pixels is
too small there unless it goes through ``FromDIP`` or ``quill.ui.dpi``.

- **Every app declares awareness.** Every place in ``quill/`` or
  ``standalone/`` that constructs a ``wx.App`` (or a subclass of one) must
  call ``enable_dpi_awareness()`` earlier in the same function. That covers
  every entry point at once, including one added next year, because no app
  can open a window without constructing an App. A second test walks the
  roster -- every ``quill/apps`` app with a ``main`` and every
  ``standalone/<app>`` launcher -- so an app that builds its App somewhere
  unusual is noticed rather than silently uncovered.
- **No raw pixel sizes.** ``quill.tools.fixed_pixel_audit`` scans every UI
  module an app is built from; a new ``size=(400, 300)`` fails here until it
  is written ``size=dip_size(parent, 400, 300)`` (or ``FromDIP``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.tools import fixed_pixel_audit

REPO_ROOT = Path(__file__).resolve().parents[3]
AWARENESS_CALL = "enable_dpi_awareness"


def _python_files(*roots: str) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            parts = path.relative_to(REPO_ROOT).parts
            if "tests" in parts or "build" in parts or "dist" in parts:
                continue
            files.append(path)
    return files


def _app_class_names(files: list[Path]) -> set[str]:
    """Names of every class anywhere that subclasses ``wx.App``."""
    names = {"wx.App"}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                ast.unparse(base) == "wx.App" for base in node.bases
            ):
                names.add(node.name)
    return names


def _app_constructions(path: Path, app_names: set[str]) -> list[tuple[int, bool]]:
    """``(line, covered)`` for each App construction in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    results: list[tuple[int, bool]] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            continue
        body_nodes = [n for stmt in func.body for n in ast.walk(stmt)]
        aware_lines = [
            n.lineno
            for n in body_nodes
            if isinstance(n, ast.Call) and ast.unparse(n.func).endswith(AWARENESS_CALL)
        ]
        for node in body_nodes:
            if isinstance(node, ast.Call) and ast.unparse(node.func) in app_names:
                # Only judge a construction in the innermost function holding it.
                owner = _innermost_function(tree, node)
                if owner is not func:
                    continue
                covered = any(line < node.lineno for line in aware_lines)
                results.append((node.lineno, covered))
    return results


def _innermost_function(tree: ast.Module, target: ast.AST) -> ast.AST:
    best: ast.AST = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(child is target for child in ast.walk(node)):
                if best is tree or node.lineno >= getattr(best, "lineno", 0):
                    best = node
    return best


_FILES = _python_files("quill", "standalone")
_APP_NAMES = _app_class_names(_FILES)


def _all_constructions() -> dict[str, list[tuple[int, bool]]]:
    found: dict[str, list[tuple[int, bool]]] = {}
    for path in _FILES:
        source = path.read_text(encoding="utf-8")
        if "App(" not in source:
            continue
        hits = _app_constructions(path, _APP_NAMES)
        if hits:
            found[path.relative_to(REPO_ROOT).as_posix()] = hits
    return found


def test_every_app_construction_declares_dpi_awareness_first() -> None:
    constructions = _all_constructions()
    assert constructions, "the scan found no wx.App at all -- the gate is broken"
    uncovered = [
        f"{path}:{line}"
        for path, hits in sorted(constructions.items())
        for line, covered in hits
        if not covered
    ]
    assert not uncovered, (
        "these construct a wx.App without calling enable_dpi_awareness() first "
        "in the same function, so Windows will stretch and blur the app at 150 "
        "and 200 percent (#1702):\n  " + "\n  ".join(uncovered)
    )


def _covered_modules() -> set[str]:
    return {
        path
        for path, hits in _all_constructions().items()
        if any(covered for _line, covered in hits)
    }


def _has_main(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)


def _app_roster() -> dict[str, Path]:
    """Every QuillVille app's own code: ``quill/apps/<x>.py`` with a ``main``
    and every ``quill/apps/<x>/`` package, plus QUILL itself."""
    roster: dict[str, Path] = {"quill": REPO_ROOT / "quill" / "ui"}
    apps = REPO_ROOT / "quill" / "apps"
    for path in sorted(apps.glob("*.py")):
        if path.name != "__init__.py" and _has_main(path):
            roster[f"quill.apps.{path.stem}"] = path
    for package in sorted(p for p in apps.iterdir() if (p / "__init__.py").is_file()):
        roster[f"quill.apps.{package.name}"] = package
    return roster


def _is_covered(target: Path, covered: set[str]) -> bool:
    relative = target.relative_to(REPO_ROOT).as_posix()
    if target.is_file():
        return relative in covered
    if relative == "quill/ui":
        return "quill/ui/main_frame.py" in covered
    return any(path.startswith(relative + "/") for path in covered)


def test_every_app_in_the_roster_declares_dpi_awareness() -> None:
    roster = _app_roster()
    covered = _covered_modules()
    # The roster must actually hold the family, or this test proves nothing.
    for expected in (
        "quill.apps.lite",
        "quill.apps.radio",
        "quill.apps.podcasts",
        "quill.apps.studio",
        "quill.apps.weather",
        "quill.apps.inkwell",
        "quill.apps.converter",
        "quill.apps.player",
        "quill.apps.transcribe",
        "quill.apps.beacon",
    ):
        assert expected in roster, f"{expected} fell out of the app roster"
    missing = [name for name, target in roster.items() if not _is_covered(target, covered)]
    assert not missing, (
        "these apps never construct a wx.App behind enable_dpi_awareness(), "
        f"so nothing makes them DPI aware (#1702): {missing}"
    )


def _standalone_targets() -> dict[str, str]:
    """Each ``standalone/<app>`` shell -> the module whose ``main`` it runs."""
    targets: dict[str, str] = {}
    for shell in sorted((REPO_ROOT / "standalone").iterdir()):
        launchers = [shell / "launcher.py", *sorted(shell.glob("quill_*/__init__.py"))]
        for launcher in launchers:
            if not launcher.is_file():
                continue
            tree = ast.parse(launcher.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith(("quill.apps", "quill_social.ui"))
                    and any(alias.name in {"main", "run"} for alias in node.names)
                ):
                    targets[shell.name] = node.module
    return targets


def test_every_standalone_shell_runs_an_aware_app() -> None:
    targets = _standalone_targets()
    for shell in ("quilllite", "radio", "cast", "studio", "weather", "inkwell"):
        assert shell in targets, f"standalone/{shell} launcher was not resolved"
    covered = _covered_modules()
    unaware = []
    for shell, module in sorted(targets.items()):
        if module.startswith("quill_social"):
            path = f"standalone/social/{module.replace('.', '/')}.py"
            ok = path in covered
        else:
            base = module.replace(".", "/")
            ok = f"{base}.py" in covered or any(p.startswith(base + "/") for p in covered)
        if not ok:
            unaware.append(f"standalone/{shell} -> {module}")
    assert not unaware, f"these shells start an app that is not DPI aware: {unaware}"


def test_runtime_picker_declares_dpi_awareness() -> None:
    assert "standalone/runtime/runtime_launcher.py" in _covered_modules()


def test_no_raw_pixel_sizes_in_ui_modules() -> None:
    findings = fixed_pixel_audit.scan_tree(REPO_ROOT)
    listed = "\n  ".join(f"{f.path}:{f.line} ({f.kind})" for f in findings)
    assert not findings, (
        "a window size written in raw pixels is too small at 150 and 200 percent "
        "now that every app is DPI aware; wrap it in FromDIP, dip() or "
        f"dip_size() from quill.ui.dpi (#1702):\n  {listed}"
    )


@pytest.mark.parametrize(
    "source",
    [
        "wx.Dialog(parent, size=(720, 580))",
        "wx.TextCtrl(panel, size=wx.Size(-1, 200))",
        "self.SetMinSize((400, 300))",
        "frame.SetSize(800, 600)",
        "self.SetSizeHints(300, 200)",
        "lst.InsertColumn(0, 'Name', width=200)",
        "lst.InsertColumn(0, 'Name', wx.LIST_FORMAT_LEFT, 200)",
        "lst.SetColumnWidth(1, 120)",
        "view.AppendTextColumn('Title', width=180)",
        "apply_window_geometry(frame, 'quill', default_size=(1000, 700))",
        "def show(parent, size=(560, 400)): pass",
        "_SIZE = (720, 520); dialog.SetSize(_SIZE)",
    ],
)
def test_audit_finds_raw_pixel_sizes(source: str) -> None:
    assert fixed_pixel_audit.scan_source(source), source


@pytest.mark.parametrize(
    "source",
    [
        "wx.Dialog(parent, size=dip_size(parent, 720, 580))",
        "wx.TextCtrl(panel, size=self.FromDIP(wx.Size(-1, 200)))",
        "wx.TextCtrl(panel, size=(-1, -1))",
        "self.SetMinSize(sizer.GetMinSize())",
        "self.SetSize((width, height))",
        "lst.SetColumnWidth(1, wx.LIST_AUTOSIZE)",
        "lst.SetColumnWidth(1, -1)",
        "lst.InsertColumn(0, 'Name', width=dip(lst, 200))",
        "frame.SetSize(0, 0, 800, 600)",
        "read(size=4096)",
        "def show(parent, size=None): pass",
        "_SIZE = (720, 520); dialog.SetSize(dip_size(dialog, *_SIZE))",
    ],
)
def test_audit_leaves_converted_and_computed_sizes_alone(source: str) -> None:
    assert not fixed_pixel_audit.scan_source(source), source
