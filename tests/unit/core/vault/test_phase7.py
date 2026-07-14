"""Tests for Vault Phase 7: static HTML site export and Git sync (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.resolve import build_resolver
from quill.core.vault.site_export import (
    build_site,
    note_to_html_fragment,
    write_site,
)
from quill.core.vault.sync import (
    SyncStep,
    detect_conflicts,
    run_vault_sync,
)
from quill.core.vault.vault import scan_vault


def _md(text: str) -> str:
    """A stand-in Markdown renderer: wrap in <p>, pass embedded HTML through."""
    return f"<p>{text}</p>"


def _vault(tmp_path: Path):
    (tmp_path / "a.md").write_text("# Alpha\n\nSee [[Beta]].\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "beta.md").write_text("# Beta\n\nHi.\n", encoding="utf-8")
    return scan_vault(tmp_path)


# --- site export -----------------------------------------------------------


def test_build_site_makes_a_page_per_note_plus_index(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    site = build_site(vault, build_resolver(vault), markdown_to_html=_md)
    assert set(site) == {"a.md".replace(".md", ".html"), "sub/beta.html", "index.html"}
    assert "<title>Alpha</title>" in site["a.html"]
    # The wikilink resolved to a relative .html anchor (a.md -> sub/beta.md).
    assert 'href="sub/beta.html' in site["a.html"]
    # Index lists both notes.
    assert "Alpha" in site["index.html"] and "Beta" in site["index.html"]


def test_note_fragment_resolves_links_and_embeds(tmp_path: Path) -> None:
    (tmp_path / "x.md").write_text("# X\n\n![[Y]] and [[Y]].\n", encoding="utf-8")
    (tmp_path / "y.md").write_text("# Y\n\nY body.\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    frag = note_to_html_fragment(vault, build_resolver(vault), "x.md", markdown_to_html=_md)
    assert "Y body." in frag  # embed inlined
    assert 'class="vault-link"' in frag  # the plain [[Y]] link resolved


def test_write_site_writes_files(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    site = build_site(vault, build_resolver(vault), markdown_to_html=_md)
    out = tmp_path / "site"
    written = write_site(site, str(out))
    assert (out / "index.html").is_file()
    assert (out / "sub" / "beta.html").is_file()
    assert set(written) == set(site)


# --- git sync --------------------------------------------------------------


def test_detect_conflicts_parses_porcelain() -> None:
    porcelain = "UU notes/a.md\n M notes/b.md\nAA notes/c.md\n?? d.md\n"
    assert detect_conflicts(porcelain) == ["notes/a.md", "notes/c.md"]


class _FakeGit:
    """A scripted git runner keyed by the git subcommand."""

    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
        self.calls.append(list(command))
        sub = command[3]  # ["git", "-C", root, <sub>, ...]
        code, out = self.responses.get(sub, (0, ""))

        class R:
            returncode = code
            stdout = out
            stderr = ""

        return R()


def test_run_vault_sync_happy_path_commits_pulls_pushes() -> None:
    runner = _FakeGit({"status": (0, " M note.md")})  # something to commit; no conflicts
    result = run_vault_sync("/vault", runner=runner)
    assert result.ok and result.message == "Vault synced."
    subs = [c[3] for c in runner.calls]
    assert subs == ["add", "status", "commit", "pull", "status", "push"]


def test_run_vault_sync_reports_conflicts_and_stops_before_push() -> None:
    # First status: something to commit; second status (after pull): a conflict.
    class _ConflictGit(_FakeGit):
        def __init__(self) -> None:
            super().__init__({})
            self._status_calls = 0

        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            self.calls.append(list(command))
            sub = command[3]
            if sub == "status":
                self._status_calls += 1
                out = " M note.md" if self._status_calls == 1 else "UU note.md"
                code = 0
            else:
                code, out = 0, ""

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    runner = _ConflictGit()
    result = run_vault_sync("/vault", runner=runner)
    assert not result.ok
    assert result.conflicts == ("note.md",)
    assert "push" not in [c[3] for c in runner.calls]  # never pushed a conflicted tree


def test_sync_step_records_command() -> None:
    step = SyncStep(command=("git", "add", "-A"), returncode=0, output="")
    assert step.command == ("git", "add", "-A")


# --- gated publish ---------------------------------------------------------


def test_prepare_note_publish_is_gated_off_by_default(tmp_path: Path) -> None:
    from quill.core.vault.publish import prepare_note_publish

    vault = _vault(tmp_path)
    # future.publishing is locked_off -> feature_enabled False -> nothing to send.
    assert (
        prepare_note_publish(
            vault,
            build_resolver(vault),
            "a.html".replace(".html", ".md"),
            markdown_to_html=_md,
            feature_enabled=False,
        )
        is None
    )


def test_prepare_note_publish_builds_payload_when_enabled(tmp_path: Path) -> None:
    from quill.core.vault.publish import prepare_note_publish

    vault = _vault(tmp_path)
    payload = prepare_note_publish(
        vault, build_resolver(vault), "a.md", markdown_to_html=_md, feature_enabled=True
    )
    assert payload is not None
    assert payload.title == "Alpha" and payload.path == "a.md"
    assert 'class="vault-link"' in payload.html  # links resolved in the published HTML


def test_prepare_note_publish_none_for_missing_note(tmp_path: Path) -> None:
    from quill.core.vault.publish import prepare_note_publish

    vault = _vault(tmp_path)
    assert (
        prepare_note_publish(
            vault, build_resolver(vault), "nope.md", markdown_to_html=_md, feature_enabled=True
        )
        is None
    )
