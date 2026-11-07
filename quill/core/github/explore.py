"""Global work, activity, people, and repository discovery for the workbench."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.github.attention_queue_fetch import (
    account_login as _account_login,
)
from quill.core.github.attention_queue_fetch import (
    fetch_attention_queue,
)
from quill.core.github.discussions import fetch_discussion, list_discussions
from quill.core.github.explore_models import (
    ExploreRow,
    GitHubExploreError,
    _event_row,
    _issue_row,
    _person_row,
    _repo_row,
    _rows,
    _text,
)
from quill.core.github.explore_notifications import ExploreNotificationsMixin
from quill.core.github.explore_views import AUTH_VIEWS, PERSON_VIEWS
from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.repository_views import (
    fetch_deployments,
    fetch_repository_access,
    fetch_repository_metrics,
)
from quill.core.net import verified_ssl_context

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


class GitHubExploreClient(ExploreNotificationsMixin):
    """Bounded reads and explicit writes using the workbench's existing session."""

    def __init__(self, provider: GitHubItemsProvider) -> None:
        self._provider = provider
        self._notification_init()

    def _user(self) -> Any:
        if not self._provider.is_authenticated:
            raise GitHubExploreError("Sign in to GitHub for this account view.")
        return self._provider._gh.get_user()  # noqa: SLF001

    def account_login(self) -> str:
        """Return the signed-in login for account-scoped local queue state."""
        return _account_login(self._provider)

    def fetch_attention(
        self,
        *,
        repositories: tuple[str, ...] | list[str] = (),
        categories: tuple[str, ...] | list[str] = (),
        limit: int = 50,
    ) -> GitHubFetchResult[ExploreRow]:
        """Fetch the signed-in account's bounded attention queue."""
        return fetch_attention_queue(
            self._provider,
            repositories=repositories,
            categories=categories,
            limit=limit,
        )

    def fetch_discussion(self, repository: str, number: int) -> ExploreRow:
        """Load a discussion URL's exact number, even outside recent pages."""
        return fetch_discussion(getattr(self._provider, "token", None), repository, number)

    def _repo(self, full_name: str) -> Any:
        if not full_name or "/" not in full_name:
            raise GitHubExploreError("Enter a repository as owner/repo for this view.")
        return self._provider._repo(full_name)  # noqa: SLF001

    def fetch(
        self,
        view: str,
        *,
        repo: str = "",
        query: str = "",
        person: str = "",
        repositories: tuple[str, ...] | list[str] = (),
        categories: tuple[str, ...] | list[str] = (),
        limit: int = 50,
    ) -> list[ExploreRow]:
        """Fetch one view. Network work belongs on the caller's worker thread."""
        return list(
            self.fetch_with_status(
                view,
                repo=repo,
                query=query,
                person=person,
                repositories=repositories,
                categories=categories,
                limit=limit,
            ).items
        )

    def fetch_with_status(
        self,
        view: str,
        *,
        repo: str = "",
        query: str = "",
        person: str = "",
        repositories: tuple[str, ...] | list[str] = (),
        categories: tuple[str, ...] | list[str] = (),
        limit: int = 50,
        include_read: bool = False,
    ) -> GitHubFetchResult[ExploreRow]:
        """Fetch one view and retain any page errors or row-cap warnings."""
        if view in AUTH_VIEWS and not self._provider.is_authenticated:
            raise GitHubExploreError("Sign in to GitHub for this account view.")
        if view == "attention":
            return self.fetch_attention(
                repositories=repositories, categories=categories, limit=limit
            )
        warnings: list[str] = []
        try:
            rows = self._fetch(
                view,
                repo=repo,
                query=query,
                person=person,
                limit=max(1, min(limit, 100)),
                warnings=warnings,
                include_read=include_read,
            )
        except GitHubExploreError:
            raise
        except Exception as exc:  # noqa: BLE001 - API errors must be announced
            raise GitHubExploreError(f"Could not load {view.replace('_', ' ')}: {exc}") from exc
        return GitHubFetchResult(tuple(rows), complete=not warnings, warning="; ".join(warnings))

    def _fetch(
        self,
        view: str,
        *,
        repo: str,
        query: str,
        person: str,
        limit: int,
        warnings: list[str],
        include_read: bool = False,
    ) -> list[ExploreRow]:
        gh = self._provider._gh  # noqa: SLF001
        if view == "search":
            if not query.strip():
                raise GitHubExploreError("Enter a global GitHub search query first.")
            return [
                _issue_row(row, f"Search: {query}")
                for row in _rows(gh.search_issues(query), limit, source="Search", warnings=warnings)
            ]
        if view == "my_work":
            user = self._user()
            login = _text(getattr(user, "login", ""))
            if not login:
                raise GitHubExploreError("Could not determine the signed-in GitHub user.")
            searches = (
                ("Assigned", f"is:open assignee:{login}"),
                ("Review requested", f"is:open is:pr review-requested:{login}"),
                ("Mentioned", f"is:open mentions:{login}"),
                ("Authored", f"is:open author:{login}"),
            )
            found: dict[str, ExploreRow] = {}
            for source, expression in searches:
                try:
                    matches = gh.search_issues(expression)
                except Exception as exc:  # noqa: BLE001 - other categories may still load
                    warnings.append(f"{source}: could not load results: {exc}")
                    continue
                for row in _rows(matches, limit, source=source, warnings=warnings):
                    mapped = _issue_row(row, source)
                    if mapped.url in found:
                        previous = found[mapped.url]
                        found[mapped.url] = ExploreRow(
                            previous.label,
                            f"{source}; {previous.detail}",
                            previous.url,
                            previous.repo,
                            previous.kind,
                            previous.key,
                            previous.updated_at,
                            previous.title,
                        )
                    else:
                        found[mapped.url] = mapped
            if len(found) > limit:
                warnings.append(
                    f"My Work: showing the first {limit} unique results; more may exist"
                )
            return list(found.values())[:limit]
        if view == "activity":
            login = _text(getattr(self._user(), "login", ""))
            feed = gh.get_user(login).get_received_events()
            return [
                _event_row(row, "Activity from followed people and watched repositories")
                for row in _rows(feed, limit, source="Activity", warnings=warnings)
            ]
        if view in {"repositories", "starred", "watched"}:
            user = self._user()
            method = {
                "repositories": "get_repos",
                "starred": "get_starred",
                "watched": "get_watched",
            }[view]
            return [
                _repo_row(row, view)
                for row in _rows(getattr(user, method)(), limit, source=view, warnings=warnings)
            ]
        if view in {"following", "followers"}:
            user = self._user()
            method = "get_following" if view == "following" else "get_followers"
            return [
                _person_row(row, view)
                for row in _rows(getattr(user, method)(), limit, source=view, warnings=warnings)
            ]
        if view == "gists":
            user = self._user()
            result = []
            for row in _rows(user.get_gists(), limit, source="Gists", warnings=warnings):
                url = _text(getattr(row, "html_url", ""))
                description = _text(getattr(row, "description", "")) or "Untitled gist"
                result.append(
                    ExploreRow(description, f"Gist: {description}\n{url}", url, kind="gist")
                )
            return result
        if view == "notifications":
            return self._fetch_notification_rows(include_read=include_read, limit=limit)
        if view == "chooser":
            if not self._provider.is_authenticated:
                return []
            user = self._user()
            discovered: dict[str, ExploreRow] = {}
            for source, method in (
                ("My repositories", "get_repos"),
                ("Starred", "get_starred"),
                ("Watched", "get_watched"),
            ):
                try:
                    source_rows = getattr(user, method)()
                except Exception as exc:  # noqa: BLE001 - retain other chooser sources
                    warnings.append(f"{source}: could not load repositories: {exc}")
                    continue
                for row in _rows(source_rows, limit, source=source, warnings=warnings):
                    mapped = _repo_row(row, source)
                    discovered.setdefault(mapped.repo.casefold(), mapped)
            if len(discovered) > limit:
                warnings.append(
                    f"Repository chooser: showing the first {limit} results; more may exist"
                )
            return list(discovered.values())[:limit]
        if view in PERSON_VIEWS:
            login = person.strip().lstrip("@")
            if not login:
                raise GitHubExploreError("Enter a GitHub username for this people view.")
            user = gh.get_user(login)
            if view == "person_repos":
                return [
                    _repo_row(row, f"Owned by @{login}")
                    for row in _rows(
                        user.get_repos(),
                        limit,
                        source=f"Repositories for @{login}",
                        warnings=warnings,
                    )
                ]
            if view == "person_activity":
                return [
                    _event_row(row, f"Public activity by @{login}")
                    for row in _rows(
                        user.get_public_events(),
                        limit,
                        source=f"Public activity for @{login}",
                        warnings=warnings,
                    )
                ]
            method = "get_followers" if view == "person_followers" else "get_following"
            return [
                _person_row(row, f"{view.replace('_', ' ')} of @{login}")
                for row in _rows(
                    getattr(user, method)(),
                    limit,
                    source=f"{view.replace('_', ' ')} for @{login}",
                    warnings=warnings,
                )
            ]
        target = self._repo(repo)
        if view == "repo_overview":
            url = _text(getattr(target, "html_url", ""))
            detail = (
                f"Repository: {repo}\n{_text(getattr(target, 'description', ''))}\n"
                f"Default branch: {_text(getattr(target, 'default_branch', ''))}\n"
                f"Stars: {_text(getattr(target, 'stargazers_count', ''))}\n"
                f"Forks: {_text(getattr(target, 'forks_count', ''))}\n"
                f"Watchers: {_text(getattr(target, 'subscribers_count', ''))}\n"
                f"Open issues: {_text(getattr(target, 'open_issues_count', ''))}\n{url}"
            )
            return [ExploreRow(repo, detail, url, repo, "repo")]
        if view == "repo_activity":
            return [
                _event_row(row, "Repository activity")
                for row in _rows(
                    target.get_events(), limit, source="Repository activity", warnings=warnings
                )
            ]
        if view == "repo_people":
            groups = (
                ("Stargazers", "get_stargazers"),
                ("Watchers", "get_watchers"),
                ("Contributors", "get_contributors"),
            )
            result = []
            for source, method in groups:
                try:
                    people = getattr(target, method)()
                except Exception as exc:  # noqa: BLE001 - retain other people groups
                    warnings.append(f"{source}: could not load people: {exc}")
                    continue
                result.extend(
                    _person_row(row, source)
                    for row in _rows(people, limit, source=source, warnings=warnings)
                )
            if len(result) > limit:
                warnings.append(
                    f"Repository people: showing the first {limit} results; more may exist"
                )
            return result[:limit]
        if view == "repo_access":
            return fetch_repository_access(target, repo, limit=limit, warnings=warnings)
        if view == "deployments":
            return fetch_deployments(target, repo, limit=limit, warnings=warnings)
        if view == "metrics":
            try:
                security_alerts = self._provider.fetch_security_alerts(repo, limit=limit)
            except Exception as exc:  # noqa: BLE001 - metrics must retain permission gaps
                warnings.append(f"Security alert counts unavailable: {exc}")
                security_alerts = [SimpleNamespace(state="unavailable", alert_type="Security")]
            return [
                fetch_repository_metrics(
                    target,
                    repo,
                    limit=limit,
                    warnings=warnings,
                    security_alerts=security_alerts,
                )
            ]
        if view == "repo_forks":
            return [
                _repo_row(row, "Fork of " + repo)
                for row in _rows(target.get_forks(), limit, source="Forks", warnings=warnings)
            ]
        if view == "labels":
            result = []
            for row in _rows(target.get_labels(), limit, source="Labels", warnings=warnings):
                name = _text(getattr(row, "name", ""))
                color = _text(getattr(row, "color", ""))
                description = _text(getattr(row, "description", ""))
                url = f"https://github.com/{repo}/labels/{quote(name, safe='')}"
                result.append(
                    ExploreRow(
                        name,
                        f"Label: {name}\nColor: #{color}\n{description}",
                        url,
                        repo,
                        "label",
                        name,
                    )
                )
            return result
        if view == "pages":
            site = self._api_get(f"/repos/{repo}/pages")
            if not isinstance(site, dict):
                raise GitHubExploreError("GitHub returned invalid Pages site details.")
            url = _text(site.get("html_url"))
            result = [
                ExploreRow(
                    "Pages site",
                    f"URL: {url}\nStatus: {site.get('status', '')}\n"
                    f"Source: {site.get('source', '')}",
                    url,
                    repo,
                    "pages",
                )
            ]
            builds = self._api_get(f"/repos/{repo}/pages/builds?per_page={limit}")
            if isinstance(builds, list):
                for build in builds[:limit]:
                    if not isinstance(build, dict):
                        continue
                    status = _text(build.get("status"))
                    created = _text(build.get("created_at"))
                    result.append(
                        ExploreRow(
                            f"Build: {status} — {created}",
                            f"Status: {status}\nStarted: {created}\n"
                            f"Error: {build.get('error', '')}",
                            url,
                            repo,
                            "pages_build",
                        )
                    )
            return result
        if view == "security":
            result = []
            for alert in self._provider.fetch_security_alerts(repo, limit=limit):
                alert_type = getattr(alert, "alert_type", "Dependabot")
                if alert.state == "unavailable":
                    label = f"{alert_type} alerts unavailable"
                    detail = f"{label}\n{alert.summary}\n{alert.html_url}"
                else:
                    severity = alert.severity or "severity not reported"
                    label = f"{alert_type}: {severity}: {alert.package} — {alert.summary}"
                    details = [
                        f"Security alert #{alert.number}",
                        label,
                        f"State: {alert.state}",
                        f"Created: {alert.created_at}",
                    ]
                    location = getattr(alert, "location", "")
                    tool = getattr(alert, "tool", "")
                    rule_id = getattr(alert, "rule_id", "")
                    if location:
                        details.append(f"Location: {location}")
                    if tool:
                        details.append(f"Tool: {tool}")
                    if rule_id:
                        details.append(f"Rule: {rule_id}")
                    details.append(alert.html_url)
                    detail = "\n".join(details)
                result.append(ExploreRow(label, detail, alert.html_url, repo, "security"))
            return result
        if view == "discussions":
            result, _complete, warning = list_discussions(
                getattr(self._provider, "token", None), repo, limit=limit
            )
            if warning:
                warnings.append(warning)
            return result
        raise GitHubExploreError(f"Unknown GitHub explore view: {view}")

    def _api_get(self, path: str) -> Any:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "QUILL-GitHub-Workbench"}
        if self._provider.token:
            headers["Authorization"] = f"Bearer {self._provider.token}"
        request = Request(f"https://api.github.com{path}", headers=headers)
        try:
            opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
            with opener.open(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 404 and path.endswith("/pages"):
                raise GitHubExploreError("This repository has no GitHub Pages site.") from exc
            if exc.code in (301, 302, 303, 307, 308):
                raise GitHubExploreError(
                    "GitHub redirected the Pages request; the authenticated "
                    "request was not followed."
                ) from exc
            if exc.code == 401:
                raise GitHubExploreError(
                    "The GitHub token is invalid or expired. Sign in again."
                ) from exc
            response_headers: Any = exc.headers or {}
            if exc.code == 429 or (
                exc.code == 403 and response_headers.get("X-RateLimit-Remaining") == "0"
            ):
                retry_after = response_headers.get("Retry-After")
                detail = f" Retry after {retry_after} seconds." if retry_after else ""
                raise GitHubExploreError(f"GitHub API rate limit reached.{detail}") from exc
            if exc.code == 403:
                raise GitHubExploreError(
                    "GitHub denied this request. Check account and repository permissions."
                ) from exc
            raise GitHubExploreError(f"GitHub Pages request failed (HTTP {exc.code}).") from exc

    def set_watched(self, repo: str, watched: bool) -> None:
        user = self._user()
        target = self._repo(repo)
        try:
            (user.add_to_watched if watched else user.remove_from_watched)(target)
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not change watch setting: {exc}") from exc

    def mark_notification_read(self, notification_id: str) -> None:
        self._user()
        try:
            self._provider.mark_notification_read(notification_id)
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not mark notification read: {exc}") from exc

    def set_starred(self, repo: str, starred: bool) -> None:
        user = self._user()
        target = self._repo(repo)
        try:
            (user.add_to_starred if starred else user.remove_from_starred)(target)
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not change star setting: {exc}") from exc

    def create_label(self, repo: str, name: str, color: str, description: str) -> None:
        self._user()
        if (
            not name.strip()
            or len(color) != 6
            or any(c not in "0123456789abcdefABCDEF" for c in color)
        ):
            raise GitHubExploreError("Enter a label name and a six-digit hexadecimal color.")
        try:
            self._repo(repo).create_label(name.strip(), color, description)
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not create label: {exc}") from exc

    def delete_label(self, repo: str, name: str) -> None:
        self._user()
        try:
            self._repo(repo).get_label(name).delete()
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not delete label {name}: {exc}") from exc

    def edit_label(self, repo: str, old_name: str, name: str, color: str, description: str) -> None:
        self._user()
        if (
            not name.strip()
            or len(color) != 6
            or any(c not in "0123456789abcdefABCDEF" for c in color)
        ):
            raise GitHubExploreError("Enter a label name and a six-digit hexadecimal color.")
        try:
            self._repo(repo).get_label(old_name).edit(name.strip(), color, description)
        except Exception as exc:  # noqa: BLE001
            raise GitHubExploreError(f"Could not edit label {old_name}: {exc}") from exc
