"""The wiki's pages, discussion to issue to pull request, Related, and prompt files (GX12).

* **Edit Wiki Pages...** on a repository's Wiki row copies the wiki's git
  repository to QUILL's own folder (or brings the copy up to date) and lists
  its pages; Enter opens one in the editor. **New Wiki Page...** makes one.
  **Publish Wiki Changes...** commits the changed pages with your message and
  pushes them, after saying which pages and as whom. GitHub has no API for
  wiki pages, so this is git (:mod:`quill.core.github.wiki_pages`).
* **Create Issue from Discussion...** on a discussion opens an issue whose
  body links back, and, if you choose, comments on the discussion with its
  link. **Start Pull Request for This Issue...** on an open issue makes a
  linked branch and a draft pull request that closes the issue.
  **Related...** on an issue, pull request or discussion lists the chain
  around it (:mod:`quill.core.github.collab_links`).
* **Prompt Files...** on a repository lists its GitHub Models prompt files
  and reads each as structure (:mod:`quill.core.github.prompt_files`); Open
  in Editor edits one through the editor's own GitHub file path.
* **Open in github.dev** on a file or a pull request opens GitHub's free
  web editor at that exact file or pull request (GX14); nothing is created
  and nothing costs money.

Every write here declares its tier in
:mod:`quill.core.github.write_requirements`, so the one level check in the
dispatcher refuses it in Read Only and Safe Mode before it gets here.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem

__all__ = ["COLLAB_REASONS", "COLLAB_VERBS", "GitHubWorkbenchCollabMixin", "wiki_root"]

_WIKI = frozenset({"view", "wiki"})

COLLAB_VERBS: dict[str, frozenset[str]] = {
    "wiki_pages": _WIKI,
    "new_wiki_page": _WIKI,
    "publish_wiki": _WIKI,
    "issue_from_discussion": frozenset({"discussion"}),
    "pull_for_issue": frozenset({"item"}),
    "related": frozenset({"item", "discussion"}),
    "prompt_files": frozenset({"view", "repo"}),
    "open_github_dev": frozenset({"file", "item"}),
}

COLLAB_REASONS: dict[str, str] = {
    "wiki_pages": "Edit Wiki Pages is for a repository whose wiki is on.",
    "new_wiki_page": "New Wiki Page is for a repository whose wiki is on.",
    "publish_wiki": (
        "Publish Wiki Changes needs a copy of the wiki here (Edit Wiki Pages... makes one), "
        "while you are signed in."
    ),
    "issue_from_discussion": "Create Issue from Discussion is for a discussion, while signed in.",
    "pull_for_issue": "Start Pull Request is for an open issue, while you are signed in.",
    "related": "Related is for an issue, a pull request or a discussion, while signed in.",
    "prompt_files": "Prompt Files is for a repository.",
    "open_github_dev": "Open in github.dev is for a file of a repository or a pull request.",
}


def wiki_root() -> Path:
    """QUILL's own folder for wiki copies, one per repository."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "GitHub Wikis"


class GitHubWorkbenchCollabMixin:
    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _show_text: Callable[[str, str], None]
    _open_document: Callable[[Path], None] | None
    _open_file_url: Callable[[str], None] | None

    # Annotations only: a stub here would shadow the real ones later in the MRO.
    account_name: Callable[[], str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _who(self) -> str:
        getter = getattr(self, "account_name", None)
        name = str(getter() or "") if callable(getter) else ""
        return f"as {name}" if name else "as the signed-in account"

    def _current_repo(self) -> str:
        current = getattr(self.frame, "current", None)
        return str(current.instance) if getattr(current, "template", "") == "repository" else ""

    # -- the wiki --------------------------------------------------------------------

    def _wiki_repo(self, row: object) -> str:
        if isinstance(row, ExploreRow) and row.kind == "wiki":
            return row.repo if row.key != "off" else ""
        return self._current_repo()

    def _wiki_dir(self, repository: str) -> Path:
        from quill.core.github.wiki_pages import wiki_folder

        return wiki_folder(wiki_root(), repository)

    def _fits_wiki_pages(self, row: object) -> bool:
        return bool(self._wiki_repo(row))

    _fits_new_wiki_page = _fits_wiki_pages

    def _fits_publish_wiki(self, row: object) -> bool:
        repo = self._wiki_repo(row)
        return self.signed_in and bool(repo) and (self._wiki_dir(repo) / ".git").is_dir()

    @staticmethod
    def _git() -> Any:
        from quill.core.git_binaries import GitBinaryError, find_git

        try:
            return find_git()
        except GitBinaryError:
            return None

    def _token(self) -> str:
        return str(getattr(self.items, "token", None) or "")

    def _wiki_fetch(self, repository: str, then: Callable[[Path], None]) -> None:
        """Copy or update the wiki off the UI thread; *then* gets its folder."""
        from quill.core.github.wiki_pages import fetch_copy
        from quill.stability.safe_subprocess import run_subprocess_safely

        git = self._git()
        if git is None:
            self._say("Editing a wiki needs git, which is not installed. Git for Windows adds it.")
            return
        folder, token = self._wiki_dir(repository), self._token()

        def done(said: Any) -> None:
            self._say(str(said))
            then(folder)

        self._background(
            f"copy {repository}'s wiki",
            lambda: fetch_copy(git, repository, folder, token=token, runner=run_subprocess_safely),
            done,
        )

    def _open_page(self, path: Path) -> None:
        if self._open_document is None:
            self._say(f"The editor that opened this window cannot open files. The page is {path}.")
            return
        self._open_document(path)

    def _do_wiki_pages(self, _ref: Any, row: object) -> None:
        repository = self._wiki_repo(row)
        self._wiki_fetch(repository, lambda folder: self._show_pages(repository, folder))

    def _show_pages(self, repository: str, folder: Path) -> None:
        from quill.core.github.wiki_pages import list_pages
        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        pages = list_pages(folder)

        def detail(index: int) -> str:
            path = pages[index].path
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return f"Could not read {path.name}: {exc}"
            return f"{path}\n\n{text[:2000]}"

        chosen: list[Callable[[], None]] = []

        def open_page(index: int) -> None:
            if index >= 0:
                chosen.append(lambda: self._open_page(pages[index].path))
                box.dialog.EndModal(self.frame._wx.ID_OK)

        def new_page(_index: int) -> None:
            chosen.append(lambda: self._make_page(repository, folder))
            box.dialog.EndModal(self.frame._wx.ID_OK)

        box = WorkbenchListDialog(
            self.frame.frame,
            f"Wiki Pages: {repository}",
            [page.label for page in pages],
            list_name="Pages",
            list_help=(
                "The wiki's pages, Home first. Enter opens one in the editor; save it there, "
                "then Publish Wiki Changes... on the Wiki row sends your changes to GitHub."
            ),
            detail=detail,
            actions=(
                ("&Open in Editor", "Open the page in the editor to edit it.", open_page),
                ("&New Page...", "Make a new page, then open it.", new_page),
            ),
            copy_text=self.frame.copy_text,
        )
        box.show()
        for then in chosen[:1]:
            then()

    def _do_new_wiki_page(self, _ref: Any, row: object) -> None:
        repository = self._wiki_repo(row)
        folder = self._wiki_dir(repository)
        if (folder / ".git").is_dir():
            self._make_page(repository, folder)
        else:
            self._wiki_fetch(repository, lambda copy: self._make_page(repository, copy))

    def _make_page(self, repository: str, folder: Path) -> None:
        from quill.core.github.wiki_pages import WikiPagesError, new_page

        title = self._ask_text("New Wiki Page", f"The new page's title, in {repository}'s wiki:")
        if not title:
            return
        try:
            path = new_page(folder, title)
        except WikiPagesError as exc:
            self._say(str(exc).split("] ", 1)[-1])
            return
        self._say(
            f"Made the page {title} here. Save it in the editor, then Publish Wiki Changes... "
            "sends it to GitHub."
        )
        self._open_page(path)

    def _do_publish_wiki(self, _ref: Any, row: object) -> None:
        from quill.core.github.wiki_pages import changed_pages, publish
        from quill.stability.safe_subprocess import run_subprocess_safely

        repository, git = self._wiki_repo(row), self._git()
        if git is None:
            self._say("Publishing a wiki needs git, which is not installed.")
            return
        folder, token = self._wiki_dir(repository), self._token()

        def ask(pages: Any) -> None:
            pages = list(pages)
            names = ", ".join(pages[:8]) + (
                f", and {len(pages) - 8} more" if len(pages) > 8 else ""
            )
            what = (
                f"{len(pages)} changed pages ({names})" if pages else "the changes committed here"
            )
            if not self._confirm(
                "Publish Wiki Changes",
                f"Publish {what} to {repository}'s wiki on GitHub, {self._who()}? "
                "Everyone who can read the wiki sees them at once.",
            ):
                return
            message = self._ask_text(
                "Publish Wiki Changes",
                "Describe the change (the commit message):",
                value="Update wiki pages",
            )
            if not message:
                return
            self._background(
                f"publish {repository}'s wiki",
                lambda: publish(
                    git, repository, folder, message, token=token, runner=run_subprocess_safely
                ),
                lambda said: self._say(str(said)),
            )

        self._background(
            "read the wiki's changes",
            lambda: changed_pages(git, folder, runner=run_subprocess_safely),
            ask,
        )

    # -- discussion to issue to pull request ------------------------------------------

    @staticmethod
    def _discussion(row: object) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == "discussion" and row.key.isdigit()
        return row if found and isinstance(row, ExploreRow) else None

    def _fits_issue_from_discussion(self, row: object) -> bool:
        return self.signed_in and self._discussion(row) is not None

    def _do_issue_from_discussion(self, ref: Any, row: object) -> None:
        found = self._discussion(row)
        if found is None:
            return
        repository, number, api = found.repo or str(ref.instance), int(found.key), self.github_api()

        def read() -> tuple[str, str]:
            query = (
                "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
                "discussion(number:$i){body author{login}}}}"
            )
            owner, _slash, name = repository.partition("/")
            data = api.graphql(query, {"o": owner, "n": name, "i": number})
            node = (data.get("repository") or {}).get("discussion") or {}
            return str(node.get("body") or ""), str((node.get("author") or {}).get("login") or "")

        self._background(
            f"read discussion #{number}",
            read,
            lambda found_body: self._ask_issue(repository, found, number, *found_body),
        )

    def _ask_issue(
        self, repository: str, row: ExploreRow, number: int, body: str, author: str
    ) -> None:
        from quill.core.github.collab_links import discussion_issue_body, issue_from_discussion

        title = self._ask_text(
            "Create Issue from Discussion", "The new issue's title:", value=row.title or row.label
        )
        if not title:
            return
        text = self._ask_text(
            "Create Issue from Discussion",
            "The new issue's text (it links back to the discussion):",
            multiline=True,
            value=discussion_issue_body(row.url, author, body),
        )
        if not text:
            return
        choice = self._choose(
            "Create Issue from Discussion",
            f"Open the issue in {repository}, {self._who()}:",
            [
                f"Open it, and comment on discussion #{number} with its link",
                "Open it only",
            ],
        )
        if choice < 0:
            return
        api = self.github_api()
        self._background(
            "open the issue",
            lambda: issue_from_discussion(
                api, repository, number, title, text, comment_back=choice == 0
            ),
            lambda made: self._say(str(made[1])),
        )

    def _fits_pull_for_issue(self, row: object) -> bool:
        return (
            self.signed_in
            and isinstance(row, GitHubItem)
            and not row.is_pr
            and str(row.state).lower() == "open"
        )

    def _do_pull_for_issue(self, ref: Any, row: object) -> None:
        from quill.core.github.collab_links import pull_for_issue
        from quill.core.github.issue_development import branch_name_for, valid_branch_name

        assert isinstance(row, GitHubItem)
        repository, number = str(ref.instance), row.number
        name = self._ask_text(
            "Start Pull Request for This Issue",
            f"Branch for #{number} (made from the default branch, or used if it exists):",
            value=branch_name_for(number, row.title),
        )
        if not name:
            return
        why = valid_branch_name(name)
        if why:
            self._say(why)
            return
        if not self._confirm(
            "Start Pull Request for This Issue",
            f"In {repository}, {self._who()}: make branch {name} linked to #{number}, add one "
            "empty commit if it has none of its own (GitHub needs a commit to compare), and "
            f"open a draft pull request that closes #{number} when it merges?",
        ):
            return
        api = self.github_api()
        self._background(
            "start the pull request",
            lambda: pull_for_issue(api, repository, number, row.title, name),
            lambda made: (self._say(str(made[1])), self.frame.reload()),
        )

    def _fits_related(self, row: object) -> bool:
        return self.signed_in and (isinstance(row, GitHubItem) or self._discussion(row) is not None)

    def _do_related(self, ref: Any, row: object) -> None:
        from quill.core.github.collab_links import related

        if isinstance(row, GitHubItem):
            kind = "pull_request" if row.is_pr else "issue"
            repository, number = str(ref.instance), row.number
        else:
            found = self._discussion(row)
            if found is None:
                return
            kind, repository, number = "discussion", found.repo or str(ref.instance), int(found.key)
        api = self.github_api()
        self._background(
            f"read what links to #{number}",
            lambda: related(api, repository, kind, number),
            self._show_related,
        )

    def _show_related(self, found: Any) -> None:
        import webbrowser

        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        self._say(found.sentence)
        links = list(found.links)
        if not links:
            return

        def browse(index: int) -> None:
            url = links[index].url if index >= 0 else ""
            if not url.startswith("https://") or not webbrowser.open(url, new=2):
                self._say("That link could not be opened.")

        def copy(index: int) -> None:
            if index >= 0:
                self.frame.copy_text(links[index].url)
                self._say("Copied the link.")

        WorkbenchListDialog(
            self.frame.frame,
            f"Related: {found.subject}",
            found.lines(),
            list_name="Linked items",
            list_help="Each issue, pull request or discussion linked to it, and how.",
            detail=lambda i: "\n".join([links[i].line, links[i].url, *found.notes]),
            actions=(
                ("&Open on GitHub", "Open the selected item in your browser.", browse),
                ("Copy &Link", "Copy the selected item's address.", copy),
            ),
            copy_text=self.frame.copy_text,
        ).show()

    # -- prompt files -------------------------------------------------------------------

    def _prompt_repo(self, row: object) -> str:
        if isinstance(row, ExploreRow) and row.kind == "repo":
            return row.repo or row.key
        return self._current_repo()

    def _fits_prompt_files(self, row: object) -> bool:
        return bool(self._prompt_repo(row))

    def _do_prompt_files(self, _ref: Any, row: object) -> None:
        from quill.core.github.prompt_files import find_prompt_files

        repository, api = self._prompt_repo(row), self.github_api()

        def show(found: Any) -> None:
            self._say(found.sentence)
            if found.paths:
                self._show_prompts(repository, found)

        self._background(
            f"find {repository}'s prompt files", lambda: find_prompt_files(api, repository), show
        )

    def _show_prompts(self, repository: str, found: Any) -> None:
        from quill.core.github.prompt_files import describe, read_prompt_file
        from quill.ui.github_workbench_list_dialog import WorkbenchListDialog

        api, paths, read = self.github_api(), list(found.paths), {}

        def detail(index: int) -> str:
            path = paths[index]
            if path not in read:
                try:
                    text = read_prompt_file(api, repository, path, found.ref)
                    read[path] = "\n".join(describe(text).lines(path))
                except Exception as exc:  # noqa: BLE001 - said in the details box
                    read[path] = f"Could not read {path}: {exc}"
            return str(read[path])

        def edit(index: int) -> None:
            if index < 0 or self._open_file_url is None:
                self._say("The editor that opened this window cannot open GitHub files.")
                return
            from quill.core.github.repo_files import blob_url

            self._open_file_url(blob_url(repository, found.ref, paths[index]))

        WorkbenchListDialog(
            self.frame.frame,
            f"Prompt Files: {repository}",
            paths,
            list_name="Prompt files",
            list_help="GitHub Models prompt files on the default branch; the details read one.",
            detail=detail,
            actions=(("&Open in Editor", "Edit it; saving in the editor commits it.", edit),),
            copy_text=self.frame.copy_text,
        ).show()

    # -- github.dev (GX14) ----------------------------------------------------------------

    def _github_dev_url(self, row: object) -> str:
        url = ""
        if isinstance(row, ExploreRow) and row.kind == "file":
            url = row.url
        elif isinstance(row, GitHubItem) and row.is_pr:
            url = row.url
        prefix = "https://github.com/"
        return "https://github.dev/" + url.removeprefix(prefix) if url.startswith(prefix) else ""

    def _fits_open_github_dev(self, row: object) -> bool:
        return bool(self._github_dev_url(row))

    def _do_open_github_dev(self, _ref: Any, row: object) -> None:
        import webbrowser

        if not webbrowser.open(self._github_dev_url(row), new=2):
            self._say("The browser could not be opened.")
