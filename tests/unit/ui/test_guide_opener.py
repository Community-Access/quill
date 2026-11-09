"""Help > Open User Guide and Open GitHub Guide, and the GitHub windows' F1 button."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.ui import app_context_help, guide_opener


@pytest.fixture
def opened(monkeypatch) -> list[str]:
    urls: list[str] = []
    monkeypatch.setattr(guide_opener.webbrowser, "open", lambda url: urls.append(url) or True)
    return urls


@pytest.fixture(autouse=True)
def _no_routes(monkeypatch) -> None:
    monkeypatch.setattr(app_context_help, "_guide_routes", [])


def test_the_github_guide_opens_its_shipped_html(opened) -> None:
    said: list[str] = []
    for product in ("quill", "quilllite"):
        assert guide_opener.open_guide(product, "github", report=said.append)
    assert opened[0].endswith("github-guide/github-guide.html")
    assert opened[1].endswith("github-guide/lite-github-guide.html")
    assert said == ["Opened GitHub Guide in browser"] * 2


def test_a_missing_github_guide_says_so(monkeypatch, opened) -> None:
    monkeypatch.setattr(guide_opener, "find_guide", lambda *_a, **_k: None)
    said: list[str] = []
    assert not guide_opener.open_guide("quilllite", "github", report=said.append)
    assert opened == []
    assert said == [
        "The GitHub Guide is not in this copy of QUILL Lite. Reinstalling puts it back."
    ]


def test_the_user_guide_is_rendered_into_the_data_folder(monkeypatch, tmp_path, opened) -> None:
    source = tmp_path / "src" / "userguide.md"
    source.parent.mkdir()
    source.write_text("# Guide\n\nHello.\n", encoding="utf-8")
    monkeypatch.setattr(guide_opener, "find_guide", lambda *_a, **_k: source)
    said: list[str] = []
    out = tmp_path / "out"
    assert guide_opener.open_guide("quill", "user", render_dir=out, report=said.append)
    assert opened == [(out / "userguide.html").as_uri()]
    assert said == ["Opened user guide in browser"]


def test_a_missing_user_guide_is_left_to_the_caller(monkeypatch, opened) -> None:
    monkeypatch.setattr(guide_opener, "find_guide", lambda *_a, **_k: None)
    said: list[str] = []
    assert not guide_opener.open_guide("quill", "user", render_dir=Path(), report=said.append)
    assert said == [] and opened == []


@pytest.mark.parametrize(
    ("title", "github"),
    [
        ("GitHub Items", True),
        ("Explore GitHub", True),
        ("Review pull request #12", True),
        ("Review Pull Request #12", True),
        ("Manage GitHub Accounts", True),
        ("Preferences", False),
        ("Find and Replace", False),
    ],
)
def test_which_windows_are_github_windows(title: str, github: bool) -> None:
    assert guide_opener.is_github_window(title) is github


def test_f1_in_a_github_window_offers_the_github_guide(opened) -> None:
    said: list[str] = []
    guide_opener.register_github_guide_help("quill", said.append)
    guide_opener.register_github_guide_help("quill", said.append)  # once, not twice
    assert len(app_context_help._guide_routes) == 1
    assert app_context_help.guide_route_for("Preferences") is None
    route = app_context_help.guide_route_for("GitHub Items")
    assert route is not None
    label, opener = route
    assert label == "Open GitHub Guide"
    opener()
    assert opened[-1].endswith("github-guide/github-guide.html")
    assert said == ["Opened GitHub Guide in browser"]


def test_a_broken_route_never_breaks_f1() -> None:
    def boom(_title: str) -> bool:
        raise RuntimeError("bad")

    app_context_help.register_guide_route(boom, "Broken", lambda: None)
    assert app_context_help.guide_route_for("GitHub Items") is None


def test_quills_help_row_opens_the_github_guide(opened) -> None:
    from quill.ui.main_frame_guides import GuidesMenuMixin

    status: list[str] = []
    host = SimpleNamespace(_set_status=status.append)
    GuidesMenuMixin.open_github_guide(host)  # type: ignore[arg-type]
    assert opened[-1].endswith("github-guide/github-guide.html")
    assert status == ["Opened GitHub Guide in browser"]
