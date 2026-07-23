# Podcast Feed Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Username/password (HTTP Basic) authentication for private podcast feeds, end to end: subscribe, refresh, download, stream, transcripts, chapters -- with passwords in the platform secret store and a same-host gate on every request.

**Architecture:** A new wx-free core module `quill/core/podcasts/feed_auth.py` owns credential storage (via the existing unified secret store) and the one same-host gate (`auth_for_url`) every call site uses. `PodcastShow` gains a non-secret `feed_username` field. Existing fetchers gain an optional auth parameter; a small shared Feed Credentials dialog serves both the 401-retry prompt in Add Podcast and a new show-context-menu item.

**Tech Stack:** Python 3.13, wxPython, urllib, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-16-podcast-feed-auth-design.md`

## Global Constraints

- Work in repo `S:\quill` on branch `feature/podcast-feed-auth` in an isolated git worktree (the main checkout is in use by another session). Create via `superpowers:using-git-worktrees` at execution start.
- Passwords are NEVER written to `podcasts.json`, OPML, logs, or crash reports (spec section 5).
- Credentials are sent only when the request host equals the feed URL's host, case-insensitive exact match, no subdomain matching (spec D-1).
- Credential store name: `quill-podcast-feed:<show_id>` through `quill.platform.windows.credential_store` (`load_secret` / `save_secret` / `delete_secret`). Do NOT invent a new storage backend.
- Background refresh never opens modal prompts on auth failure (spec D-2).
- All new interactive controls get `SetName(...)` accessible names; dialogs route through `apply_modal_ids` + `show_modal_dialog` from `quill.ui.dialog_contract` (PRD A-1/A-3).
- No new network egress sites; only headers/params added inside the sites already registered in `quill/tools/network_egress_audit.py`.
- Run tests from the worktree root: `python -m pytest <file> -v` (pytest config: `pythonpath=["."]`, 30s timeout per test).
- Every task ends with a commit on the feature branch, message ending with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Core credential module `feed_auth.py` + URL userinfo redaction

**Files:**
- Create: `quill/core/podcasts/feed_auth.py`
- Modify: `quill/stability/redaction.py` (add `redact_url_userinfo`)
- Test: `tests/unit/core/test_podcast_feed_auth.py`

**Interfaces:**
- Consumes: `quill.platform.windows.credential_store.load_secret/save_secret/delete_secret`; `PodcastShow` (existing fields; `feed_username` arrives in Task 2 -- use `getattr(show, "feed_username", "")` is NOT needed, Task 2 lands before any UI consumes this; within this task's tests, set the attribute via a stub object).
- Produces (used by Tasks 3-10):
  - `save_feed_password(show_id: str, password: str) -> None`
  - `load_feed_password(show_id: str) -> str`
  - `delete_feed_password(show_id: str) -> None`
  - `basic_auth_header(username: str, password: str) -> str`
  - `auth_for_url(show: PodcastShow, url: str) -> tuple[str, str]`
  - `auth_header_for_url(show: PodcastShow, url: str) -> str`
  - `url_with_auth(show: PodcastShow, url: str) -> str`
  - `redact_url_userinfo(text: str) -> str` (in `quill.stability.redaction`)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/core/test_podcast_feed_auth.py`:

```python
"""feed_auth: the same-host credential gate for private podcast feeds."""

from __future__ import annotations

from quill.core.podcasts import feed_auth
from quill.core.podcasts.models import PodcastShow
from quill.stability.redaction import redact_url_userinfo


def _show(**kwargs: object) -> PodcastShow:
    defaults: dict[str, object] = {
        "id": "show-1",
        "title": "Private Show",
        "feed_url": "https://feeds.example.com/private.rss",
    }
    defaults.update(kwargs)
    show = PodcastShow(**defaults)  # type: ignore[arg-type]
    show.feed_username = kwargs.get("feed_username", "member")  # Task 2 adds the real field
    if "feed_username" in kwargs:
        show.feed_username = kwargs["feed_username"]
    return show


def _patch_password(monkeypatch, value: str) -> None:
    monkeypatch.setattr(feed_auth, "load_feed_password", lambda _sid: value)


def test_auth_for_url_same_host_returns_credentials(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/ep1.mp3") == ("member", "pw")


def test_auth_for_url_host_match_is_case_insensitive(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://FEEDS.EXAMPLE.COM/x") == ("member", "pw")


def test_auth_for_url_different_host_returns_nothing(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://cdn.example.com/ep1.mp3") == ("", "")


def test_auth_for_url_subdomain_is_a_different_host(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://media.feeds.example.com/x") == ("", "")


def test_auth_for_url_no_username_returns_nothing(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show(feed_username="")
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_for_url_local_show_returns_nothing(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show(is_local=True, feed_url="")
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_for_url_no_stored_password_returns_nothing(monkeypatch) -> None:
    _patch_password(monkeypatch, "")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_header_for_url_builds_basic_header(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    header = feed_auth.auth_header_for_url(show, "https://feeds.example.com/x")
    assert header.startswith("Basic ")
    assert feed_auth.auth_header_for_url(show, "https://cdn.example.com/x") == ""


def test_basic_auth_header_encodes_user_colon_password() -> None:
    import base64

    header = feed_auth.basic_auth_header("member", "pw")
    assert base64.b64decode(header.removeprefix("Basic ")).decode() == "member:pw"


def test_url_with_auth_embeds_percent_encoded_userinfo(monkeypatch) -> None:
    _patch_password(monkeypatch, "p w:@")
    show = _show(feed_username="me@site")
    url = feed_auth.url_with_auth(show, "https://feeds.example.com:8443/e.mp3?a=1")
    assert url == "https://me%40site:p%20w%3A%40@feeds.example.com:8443/e.mp3?a=1"


def test_url_with_auth_leaves_other_hosts_untouched(monkeypatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    url = "https://cdn.example.com/e.mp3"
    assert feed_auth.url_with_auth(show, url) == url


def test_store_roundtrip_uses_credential_store(monkeypatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.save_secret",
        lambda name, secret: saved.__setitem__(name, secret),
    )
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.load_secret",
        lambda name: saved.get(name, ""),
    )
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.delete_secret",
        lambda name: saved.pop(name, None) is not None,
    )
    feed_auth.save_feed_password("abc", "sekrit")
    assert saved == {"quill-podcast-feed:abc": "sekrit"}
    assert feed_auth.load_feed_password("abc") == "sekrit"
    feed_auth.delete_feed_password("abc")
    assert feed_auth.load_feed_password("abc") == ""


def test_redact_url_userinfo_strips_credentials() -> None:
    text = "loading https://me:pw@host.example.com/feed.rss now"
    assert redact_url_userinfo(text) == "loading https://host.example.com/feed.rss now"


def test_redact_url_userinfo_leaves_plain_urls_alone() -> None:
    text = "loading https://host.example.com/feed.rss now"
    assert redact_url_userinfo(text) == text
```

Note on `_show`: `PodcastShow` is `@dataclass(slots=True)`, so setting an undeclared attribute raises `AttributeError` until Task 2 adds the field. **Task 2 must land before this test file passes as written.** To keep Task 1 independently green, implement Task 1's module against the field name and mark the six `auth_for_url`/`url_with_auth` tests with `pytest.mark.skip(reason="needs feed_username field, Task 2")` -- then Task 2's checklist removes the skips. The store-roundtrip, `basic_auth_header`, and redaction tests must pass in Task 1 itself.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/core/test_podcast_feed_auth.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: quill.core.podcasts.feed_auth` and `ImportError: redact_url_userinfo`.

- [ ] **Step 3: Implement `quill/core/podcasts/feed_auth.py`**

```python
"""Per-show credentials for private (HTTP Basic auth) podcast feeds.

The username lives on the ``PodcastShow`` record (it is not a secret); the
password lives in the platform secret store via
``quill.platform.windows.credential_store`` (Windows Credential Manager on
installed copies, the DPAPI ``keys.enc`` file in portable mode, the macOS
login Keychain upstream) under ``quill-podcast-feed:<show_id>``.

:func:`auth_for_url` is the one same-host gate every network call site uses:
credentials are returned only for requests to the feed URL's own host, so a
password is never sent to a third-party CDN. wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import urllib.parse

from quill.core.podcasts.models import PodcastShow

_CRED_PREFIX = "quill-podcast-feed:"


def _cred_name(show_id: str) -> str:
    return f"{_CRED_PREFIX}{show_id}"


def save_feed_password(show_id: str, password: str) -> None:
    """Persist *password* for *show_id* (empty password deletes the entry)."""
    from quill.platform.windows import credential_store

    credential_store.save_secret(_cred_name(show_id), password)


def load_feed_password(show_id: str) -> str:
    """The stored password for *show_id*, or ``""``."""
    from quill.platform.windows import credential_store

    return credential_store.load_secret(_cred_name(show_id))


def delete_feed_password(show_id: str) -> None:
    """Remove *show_id*'s stored password (no-op when absent)."""
    from quill.platform.windows import credential_store

    credential_store.delete_secret(_cred_name(show_id))


def basic_auth_header(username: str, password: str) -> str:
    """``Authorization`` header value for HTTP Basic auth."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _hosts_match(feed_url: str, url: str) -> bool:
    feed_host = (urllib.parse.urlsplit(feed_url).hostname or "").lower()
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return bool(feed_host) and feed_host == host


def auth_for_url(show: PodcastShow, url: str) -> tuple[str, str]:
    """``(username, password)`` for *url*, or ``("", "")``.

    The same-host gate: non-empty only when the show has a username, the
    request host equals the feed's host exactly (case-insensitive; a
    subdomain is a different host), and a password is actually stored.
    """
    if show.is_local or not show.feed_username or not show.feed_url:
        return ("", "")
    if not _hosts_match(show.feed_url, url):
        return ("", "")
    password = load_feed_password(show.id)
    if not password:
        return ("", "")
    return (show.feed_username, password)


def auth_header_for_url(show: PodcastShow, url: str) -> str:
    """A ready ``Authorization`` header value for *url*, or ``""``."""
    username, password = auth_for_url(show, url)
    return basic_auth_header(username, password) if username else ""


def url_with_auth(show: PodcastShow, url: str) -> str:
    """*url* with percent-encoded userinfo embedded, for playback engines
    (mpv, the ffmpeg enhancement relay) that accept only a URL string.
    Unchanged when :func:`auth_for_url` yields nothing."""
    username, password = auth_for_url(show, url)
    if not username:
        return url
    parts = urllib.parse.urlsplit(url)
    user = urllib.parse.quote(username, safe="")
    secret = urllib.parse.quote(password, safe="")
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{user}:{secret}@{host}"
    return urllib.parse.urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
```

- [ ] **Step 4: Add `redact_url_userinfo` to `quill/stability/redaction.py`**

Add a module-level regex next to the existing `_TOKEN_RE`-style constants, and a public function next to `redact_source_tokens` (line ~73):

```python
_URL_USERINFO_RE = re.compile(r"(\bhttps?://)[^/\s@]+@")


def redact_url_userinfo(text: str) -> str:
    """Strip ``user:password@`` userinfo from any URL in *text*."""
    return _URL_USERINFO_RE.sub(r"\1", text)
```

Also apply it inside the existing `redact_source_tokens` and `redact_command_arg` bodies (one added line each, before their return-assembly): `text = _URL_USERINFO_RE.sub(r"\1", text)` -- match each function's local variable name. This makes crash bundles and logged subprocess args (the ffmpeg relay command line) credential-free automatically.

- [ ] **Step 5: Run the Task 1 tests**

Run: `python -m pytest tests/unit/core/test_podcast_feed_auth.py -v`
Expected: PASS for store-roundtrip, `basic_auth_header`, both redaction tests; SKIP for the gate tests (removed in Task 2). Also run `python -m pytest tests/unit/ -k redaction -v` -- existing redaction tests must still pass.

- [ ] **Step 6: Commit**

```bash
git add quill/core/podcasts/feed_auth.py quill/stability/redaction.py tests/unit/core/test_podcast_feed_auth.py
git commit -m "feat(podcasts): feed_auth credential module with same-host gate"
```

---

### Task 2: `PodcastShow.feed_username` field

**Files:**
- Modify: `quill/core/podcasts/models.py:344-428` (`PodcastShow`)
- Test: `tests/unit/core/test_podcast_models.py`, `tests/unit/core/test_podcast_opml.py`, `tests/unit/core/test_podcast_feed_auth.py`

**Interfaces:**
- Produces: `PodcastShow.feed_username: str = ""` -- persisted in `to_dict`/`from_dict`, defaulting `""` for old data. Consumed by Tasks 1 (gate), 7, 10.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/core/test_podcast_models.py`:

```python
def test_show_feed_username_round_trips() -> None:
    from quill.core.podcasts.models import PodcastShow

    show = PodcastShow(id="s1", title="T", feed_url="https://h/f.rss", feed_username="member")
    data = show.to_dict()
    assert data["feed_username"] == "member"
    loaded = PodcastShow.from_dict(data)
    assert loaded is not None and loaded.feed_username == "member"


def test_show_feed_username_defaults_empty_for_old_data() -> None:
    from quill.core.podcasts.models import PodcastShow

    loaded = PodcastShow.from_dict({"id": "s1", "title": "T"})
    assert loaded is not None and loaded.feed_username == ""
```

Append to `tests/unit/core/test_podcast_opml.py` (mirror the file's existing `PodcastShow`/`export_opml` usage at its top):

```python
def test_export_opml_never_contains_credentials() -> None:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1", title="Private", feed_url="https://feeds.example.com/p.rss",
        feed_username="member",
    )
    library.add_show(show)
    text = export_opml(library)
    assert "member" not in text
    assert "feed_username" not in text
```

(If that file imports differently -- e.g. `opml.export_opml` -- match its existing import style exactly.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/core/test_podcast_models.py tests/unit/core/test_podcast_opml.py -v`
Expected: FAIL with `TypeError: unexpected keyword argument 'feed_username'`.

- [ ] **Step 3: Implement the field**

In `quill/core/podcasts/models.py`, `PodcastShow`:
- After `feed_url: str = ""` (line 350) add:

```python
    #: Private feeds (HTTP Basic auth): the sign-in username. Not a secret;
    #: the password lives in the platform secret store (feed_auth.py) and is
    #: deliberately NOT a field here -- it must never reach podcasts.json.
    feed_username: str = ""
```

- In `to_dict()` after `"feed_url": self.feed_url,` add `"feed_username": self.feed_username,`
- In `from_dict()` after `feed_url=str(data.get("feed_url", "")),` add `feed_username=str(data.get("feed_username", "")),`

- [ ] **Step 4: Remove the Task 1 skips**

In `tests/unit/core/test_podcast_feed_auth.py`, delete the `pytest.mark.skip` markers added in Task 1 and simplify `_show` to pass `feed_username` as a normal constructor kwarg.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/unit/core/test_podcast_models.py tests/unit/core/test_podcast_opml.py tests/unit/core/test_podcast_feed_auth.py tests/unit/core/test_podcast_subscriptions.py -v`
Expected: ALL PASS (subscriptions round-trips through to_dict/from_dict, so run it too).

- [ ] **Step 6: Commit**

```bash
git add quill/core/podcasts/models.py tests/unit/core/test_podcast_models.py tests/unit/core/test_podcast_opml.py tests/unit/core/test_podcast_feed_auth.py
git commit -m "feat(podcasts): PodcastShow.feed_username field (password stays in secret store)"
```

---

### Task 3: `FeedAuthError` -- honest 401/403 from the feed reader

**Files:**
- Modify: `quill/core/podcasts/feed_reader.py:49-101`
- Test: `tests/unit/core/test_podcast_feed_reader.py`

**Interfaces:**
- Produces: `class FeedAuthError(FeedReaderError)` with `code = "QUILL-PODCASTS-FEED-AUTH"`, raised from `_fetch_feed_bytes` (and therefore `fetch_and_parse_feed`) on HTTP 401/403. Consumed by Tasks 7 and 8.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_podcast_feed_reader.py`, following its existing `_FakeResponse`/monkeypatch style (line ~117):

```python
def test_fetch_feed_bytes_401_raises_feed_auth_error(monkeypatch) -> None:
    import io
    import urllib.error

    def _raise_401(*_a: object, **_k: object) -> None:
        raise urllib.error.HTTPError(
            "https://feeds.example.com/p.rss", 401, "Unauthorized", {}, io.BytesIO(b"")
        )

    monkeypatch.setattr(feed_reader.urllib.request, "urlopen", _raise_401)
    with pytest.raises(feed_reader.FeedAuthError):
        feed_reader._fetch_feed_bytes("https://feeds.example.com/p.rss")


def test_fetch_feed_bytes_500_stays_generic_feed_reader_error(monkeypatch) -> None:
    import io
    import urllib.error

    def _raise_500(*_a: object, **_k: object) -> None:
        raise urllib.error.HTTPError(
            "https://feeds.example.com/p.rss", 500, "Server Error", {}, io.BytesIO(b"")
        )

    monkeypatch.setattr(feed_reader.urllib.request, "urlopen", _raise_500)
    with pytest.raises(feed_reader.FeedReaderError) as excinfo:
        feed_reader._fetch_feed_bytes("https://feeds.example.com/p.rss")
    assert not isinstance(excinfo.value, feed_reader.FeedAuthError)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/core/test_podcast_feed_reader.py -v`
Expected: the two new tests FAIL with `AttributeError: ... has no attribute 'FeedAuthError'`.

- [ ] **Step 3: Implement**

In `quill/core/podcasts/feed_reader.py`, after `FeedReaderError` (line 49-52) add:

```python
class FeedAuthError(FeedReaderError):
    """The feed demanded a sign-in, or refused the credentials we sent
    (HTTP 401/403) -- distinct from a network failure so the UI can prompt
    for credentials instead of blaming the connection."""

    code = "QUILL-PODCASTS-FEED-AUTH"
```

In `_fetch_feed_bytes`, insert an `HTTPError` clause BEFORE the existing `except (urllib.error.URLError, ...)` line (`HTTPError` subclasses `URLError`, so order matters):

```python
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise FeedAuthError(
                "This feed requires a sign-in, or did not accept the username/password."
            ) from error
        raise FeedReaderError(f"Could not reach that feed: {error}") from error
```

- [ ] **Step 4: Run the whole feed reader test file**

Run: `python -m pytest tests/unit/core/test_podcast_feed_reader.py -v`
Expected: ALL PASS (including the pre-existing basic-auth header test).

- [ ] **Step 5: Commit**

```bash
git add quill/core/podcasts/feed_reader.py tests/unit/core/test_podcast_feed_reader.py
git commit -m "feat(podcasts): FeedAuthError distinguishes 401/403 from network failures"
```

---

### Task 4: Authenticated episode downloads

**Files:**
- Modify: `quill/core/podcasts/download_queue.py` (`DownloadItem` ~line 64, `_fetch_chunked` ~line 87, `enqueue` ~line 179, worker call ~line 322)
- Test: `tests/unit/core/test_podcast_download_queue.py`

**Interfaces:**
- Consumes: header string produced by `feed_auth.auth_header_for_url` (Task 1).
- Produces: `enqueue(..., auth_header: str = "")`; `DownloadItem.auth_header: str = ""`; `_fetch_chunked(url, destination, *, auth_header: str = "", pause_event, cancel_event, on_progress)`. Consumed by Task 8's call-site wiring.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/test_podcast_download_queue.py`, mirroring that file's existing fake-urlopen pattern (inspect its helpers first and reuse them; the essential assertion):

```python
def test_fetch_chunked_sends_auth_header_when_given(monkeypatch, tmp_path) -> None:
    import threading

    from quill.core.podcasts import download_queue as dq

    captured: dict[str, str] = {}

    class _Resp:
        status = 200
        headers = {"Content-Length": "2"}

        def read(self, _n: int) -> bytes:
            if captured.get("done"):
                return b""
            captured["done"] = "1"
            return b"ok"

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def _fake_urlopen(request: object, **_k: object) -> _Resp:
        captured["auth"] = dict(request.headers).get("Authorization", "")
        return _Resp()

    monkeypatch.setattr(dq.urllib.request, "urlopen", _fake_urlopen)
    status = dq._fetch_chunked(
        "https://feeds.example.com/e.mp3",
        tmp_path / "e.mp3",
        auth_header="Basic abc123",
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda *_a: None,
    )
    assert status == "completed"
    assert captured["auth"] == "Basic abc123"


def test_fetch_chunked_sends_no_auth_header_by_default(monkeypatch, tmp_path) -> None:
    import threading

    from quill.core.podcasts import download_queue as dq

    captured: dict[str, str] = {}

    class _Resp:
        status = 200
        headers = {"Content-Length": "0"}

        def read(self, _n: int) -> bytes:
            return b""

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def _fake_urlopen(request: object, **_k: object) -> _Resp:
        captured["auth"] = dict(request.headers).get("Authorization", "MISSING")
        return _Resp()

    monkeypatch.setattr(dq.urllib.request, "urlopen", _fake_urlopen)
    dq._fetch_chunked(
        "https://feeds.example.com/e.mp3",
        tmp_path / "e.mp3",
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda *_a: None,
    )
    assert captured["auth"] == "MISSING"
```

Note: `urllib.request.Request.headers` capitalizes keys (`Authorization`); if the existing tests in this file access headers differently, mirror their access pattern.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/core/test_podcast_download_queue.py -v`
Expected: new tests FAIL with `TypeError: _fetch_chunked() got an unexpected keyword argument 'auth_header'`.

- [ ] **Step 3: Implement**

In `quill/core/podcasts/download_queue.py`:
- `DownloadItem`: after `destination: Path` add:

```python
    #: Ready "Authorization" header value for private feeds ("" = none).
    #: Computed by the enqueueing UI via feed_auth.auth_header_for_url, so
    #: the same-host gate has already been applied by the time it's here.
    auth_header: str = ""
```

- `_fetch_chunked` signature gains `auth_header: str = ""` (keyword-only, alongside `pause_event`). After the existing `headers = {"User-Agent": _USER_AGENT}` line add:

```python
    if auth_header:
        headers["Authorization"] = auth_header
```

- `enqueue` signature gains `auth_header: str = ""` (keyword-only) and passes `auth_header=auth_header` into the `DownloadItem(...)` construction.
- The worker's `_fetch_chunked(item.url, ...)` call (~line 322) gains `auth_header=item.auth_header`.
- If `DownloadItem` is persisted/serialized anywhere in this module (search for `to_dict`/`asdict` in the file), EXCLUDE `auth_header` from persistence -- the header encodes the password. Recompute at enqueue time only.

- [ ] **Step 4: Run the file's tests**

Run: `python -m pytest tests/unit/core/test_podcast_download_queue.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/podcasts/download_queue.py tests/unit/core/test_podcast_download_queue.py
git commit -m "feat(podcasts): optional Authorization header on episode downloads"
```

---

### Task 5: Authenticated transcripts and chapters

**Files:**
- Modify: `quill/core/podcasts/transcripts.py:52-63,121-128`; `quill/core/podcasts/chapters.py:58-71,105-111`
- Test: `tests/unit/core/test_podcast_transcripts.py`, `tests/unit/core/test_podcast_chapters.py`

**Interfaces:**
- Produces: `fetch_and_parse_transcript(url, transcript_type, *, safe_mode=False, auth_header: str = "")` and `fetch_and_parse_chapters(url, *, safe_mode=False, auth_header: str = "")`, threading the header into `_fetch_transcript_bytes(url, auth_header="")` / `_fetch_chapters_bytes(url, auth_header="")`. Consumed by Task 8.

- [ ] **Step 1: Write the failing tests**

Append to each test file (mirroring each file's existing fake-urlopen helper; the essential shape, shown for transcripts -- chapters is identical with `chapters`/`_fetch_chapters_bytes`):

```python
def test_fetch_transcript_bytes_sends_auth_header(monkeypatch) -> None:
    from quill.core.podcasts import transcripts

    captured: dict[str, str] = {}

    class _Resp:
        def read(self, _n: int) -> bytes:
            return b"WEBVTT"

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def _fake_urlopen(request: object, **_k: object) -> _Resp:
        captured["auth"] = dict(request.headers).get("Authorization", "MISSING")
        return _Resp()

    monkeypatch.setattr(transcripts.urllib.request, "urlopen", _fake_urlopen)
    transcripts._fetch_transcript_bytes("https://h.example.com/t.vtt", auth_header="Basic xyz")
    assert captured["auth"] == "Basic xyz"
    transcripts._fetch_transcript_bytes("https://h.example.com/t.vtt")
    assert captured["auth"] == "MISSING"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/core/test_podcast_transcripts.py tests/unit/core/test_podcast_chapters.py -v`
Expected: new tests FAIL with `TypeError ... unexpected keyword argument 'auth_header'`.

- [ ] **Step 3: Implement**

In `transcripts.py`, `_fetch_transcript_bytes(url: str, *, auth_header: str = "") -> bytes`; build headers as a dict and add `Authorization` when non-empty:

```python
    headers = {"User-Agent": _USER_AGENT}
    if auth_header:
        headers["Authorization"] = auth_header
    request = urllib.request.Request(url, headers=headers)
```

`fetch_and_parse_transcript` gains keyword-only `auth_header: str = ""` and forwards it. Mirror both changes in `chapters.py` (`_fetch_chapters_bytes` keeps its existing `Accept: application/json` header alongside).

- [ ] **Step 4: Run both files' tests**

Run: `python -m pytest tests/unit/core/test_podcast_transcripts.py tests/unit/core/test_podcast_chapters.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/podcasts/transcripts.py quill/core/podcasts/chapters.py tests/unit/core/test_podcast_transcripts.py tests/unit/core/test_podcast_chapters.py
git commit -m "feat(podcasts): optional Authorization header on transcript/chapter fetches"
```

---

### Task 6: The Feed Credentials dialog

**Files:**
- Create: `quill/ui/podcasts/feed_credentials_dialog.py`
- Test: `tests/unit/ui/test_podcast_feed_credentials_dialog.py`

**Interfaces:**
- Consumes: `quill.ui.dialog_contract.apply_modal_ids/show_modal_dialog`.
- Produces (consumed by Tasks 7 and 10):

```python
@dataclass(slots=True)
class FeedCredentialsResult:
    action: str        # "save" or "clear"
    username: str
    password: str      # "" on "save" means "keep the stored password"

class FeedCredentialsDialog:
    def __init__(self, parent, *, username: str = "", message: str = "",
                 allow_clear: bool = False,
                 announce_cb: Callable[[str], None] | None = None) -> None: ...
    def show(self) -> FeedCredentialsResult | None: ...   # None = cancelled
```

- [ ] **Step 1: Write the failing source-contract test**

UI tests in this repo assert source contracts rather than instantiating wx (see `tests/unit/ui/test_podcast_folder_picker.py:50`). Create `tests/unit/ui/test_podcast_feed_credentials_dialog.py`:

```python
"""Feed Credentials dialog: source contracts for accessibility + secrecy."""

from __future__ import annotations

from pathlib import Path

_SRC = (
    Path(__file__).resolve().parents[3]
    / "quill" / "ui" / "podcasts" / "feed_credentials_dialog.py"
)


def test_dialog_meets_the_dialog_contract() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "apply_modal_ids(" in src
    assert "show_modal_dialog(" in src


def test_password_field_is_masked_and_controls_are_named() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "wx.TE_PASSWORD" in src
    assert 'SetName("The username this feed requires")' in src
    assert 'SetName("The password this feed requires")' in src


def test_dialog_never_logs_or_prints_the_password() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "print(" not in src
    assert "logging" not in src


def test_result_shape() -> None:
    from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsResult

    result = FeedCredentialsResult(action="save", username="u", password="p")
    assert (result.action, result.username, result.password) == ("save", "u", "p")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/ui/test_podcast_feed_credentials_dialog.py -v`
Expected: FAIL, file not found / import error.

- [ ] **Step 3: Implement the dialog**

Create `quill/ui/podcasts/feed_credentials_dialog.py`:

```python
"""One small modal for private-feed credentials, shared by the Add Podcast
401 retry prompt and the show context menu's Feed Credentials... item.

Never touches the credential store itself -- it returns what the user typed
and the caller decides what to persist (add_podcast_dialog retries the fetch
first; show_actions saves/clears). The password never leaves this dialog in
any log or announcement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.ui.dialog_contract import apply_modal_ids


@dataclass(slots=True)
class FeedCredentialsResult:
    """What the user chose: action is ``"save"`` or ``"clear"``. On save, an
    empty password means "keep whatever password is already stored"."""

    action: str
    username: str
    password: str


class FeedCredentialsDialog:
    """Username + masked password, OK/Cancel, optional Clear Credentials."""

    def __init__(
        self,
        parent: object,
        *,
        username: str = "",
        message: str = "",
        allow_clear: bool = False,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: FeedCredentialsResult | None = None

        self.dialog = wx.Dialog(parent, title="Feed Credentials")
        root = wx.BoxSizer(wx.VERTICAL)

        intro = message or (
            "This feed requires a sign-in. Enter the username and password "
            "your podcast provider gave you."
        )
        intro_text = wx.StaticText(self.dialog, label=intro)
        intro_text.Wrap(420)
        root.Add(intro_text, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self.dialog, label="&Username:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._username_ctrl = wx.TextCtrl(self.dialog, value=username)
        self._username_ctrl.SetName("The username this feed requires")
        grid.Add(self._username_ctrl, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self.dialog, label="&Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._password_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PASSWORD)
        self._password_ctrl.SetName("The password this feed requires")
        grid.Add(self._password_ctrl, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        if username:
            keep_note = wx.StaticText(
                self.dialog,
                label="Leave the password blank to keep the stored one.",
            )
            root.Add(keep_note, 0, wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        if allow_clear:
            clear_btn = wx.Button(self.dialog, label="C&lear Credentials")
            clear_btn.SetName("Remove the stored username and password for this feed")
            clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
            btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self._username_ctrl.SetFocus()

    def _on_ok(self, _event: object) -> None:
        username = self._username_ctrl.GetValue().strip()
        if not username:
            self._announce("Enter a username first")
            self._username_ctrl.SetFocus()
            return
        self._result = FeedCredentialsResult(
            action="save",
            username=username,
            password=self._password_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_clear(self, _event: object) -> None:
        self._result = FeedCredentialsResult(action="clear", username="", password="")
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> FeedCredentialsResult | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Feed Credentials", announce=self._announce)
            return self._result
        finally:
            self.dialog.Destroy()
```

- [ ] **Step 4: Run the test**

Run: `python -m pytest tests/unit/ui/test_podcast_feed_credentials_dialog.py -v`
Expected: PASS. Also run `python -m pytest tests/unit/ui/fixtures -v 2>$null; python -m pytest tests/unit/ui -k dialog_inventory -v` if a dialog-inventory gate exists -- if it fails listing the new dialog, add the dialog to `tests/unit/ui/fixtures/dialog_inventory.json` following that file's schema.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/podcasts/feed_credentials_dialog.py tests/unit/ui/test_podcast_feed_credentials_dialog.py
git commit -m "feat(podcasts): Feed Credentials dialog (username + masked password)"
```

(Include `tests/unit/ui/fixtures/dialog_inventory.json` in the add if it changed.)

---

### Task 7: Add Podcast -- prompt on 401 and retry

**Files:**
- Modify: `quill/ui/podcasts/add_podcast_dialog.py:178-218` (`_subscribe_to_feed`, `_on_fetch_done`)
- Test: `tests/unit/ui/test_podcast_add_dialog_auth.py` (new, source-contract style)

**Interfaces:**
- Consumes: `feed_reader.FeedAuthError` (Task 3), `fetch_and_parse_feed(..., username=, password=)`, `FeedCredentialsDialog` (Task 6), `feed_auth.save_feed_password` (Task 1), `PodcastShow.feed_username` (Task 2).

- [ ] **Step 1: Write the failing source-contract test**

Create `tests/unit/ui/test_podcast_add_dialog_auth.py`:

```python
"""Add Podcast: a 401 opens the Feed Credentials prompt and retries."""

from __future__ import annotations

from pathlib import Path

_SRC = (
    Path(__file__).resolve().parents[3]
    / "quill" / "ui" / "podcasts" / "add_podcast_dialog.py"
)


def test_add_dialog_handles_feed_auth_error_with_prompt_and_retry() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "FeedAuthError" in src
    assert "FeedCredentialsDialog" in src
    # Credentials from the prompt are passed into the retry fetch...
    assert "username=" in src and "password=" in src
    # ...and persisted only after a successful subscribe.
    assert "save_feed_password" in src
    assert "feed_username" in src


def test_add_dialog_prefills_username_on_second_failure() -> None:
    src = _SRC.read_text(encoding="utf-8")
    assert "username=last_username" in src or "username=self._pending_username" in src
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/ui/test_podcast_add_dialog_auth.py -v`
Expected: FAIL on the asserts.

- [ ] **Step 3: Implement**

In `add_podcast_dialog.py`:

1. Extend `_subscribe_to_feed` to carry optional credentials (default empty) and remember them for the completion callback:

```python
    def _subscribe_to_feed(
        self, feed_url: str, *, title_hint: str = "", username: str = "", password: str = ""
    ) -> None:
        if self._safe_mode:
            self._status.SetLabel("Adding podcasts is disabled in Safe Mode.")
            return
        if self._library.find_show_by_feed_url(feed_url) is not None:
            self._status.SetLabel("You're already subscribed to that feed.")
            return
        self._status.SetLabel(f"Fetching {title_hint or feed_url}...")

        def _do_fetch(**_kwargs: Any) -> feed_reader.FeedInfo:
            return feed_reader.fetch_and_parse_feed(
                feed_url, username=username, password=password, safe_mode=self._safe_mode
            )

        self._task_manager.submit(
            "podcast-subscribe",
            _do_fetch,
            on_success=lambda _op, info: self._on_fetch_done(
                feed_url, info, None, username=username, password=password
            ),
            on_failure=lambda _op, exc: self._on_fetch_done(
                feed_url, None, exc, username=username, password=password
            ),
        )
```

2. Extend `_on_fetch_done` -- on `FeedAuthError`, prompt and retry; on success with credentials, persist them:

```python
    def _on_fetch_done(
        self,
        feed_url: str,
        info: feed_reader.FeedInfo | None,
        error: BaseException | None,
        *,
        username: str = "",
        password: str = "",
    ) -> None:
        if isinstance(error, feed_reader.FeedAuthError):
            self._prompt_for_credentials(feed_url, last_username=username)
            return
        if error is not None or info is None:
            self._status.SetLabel(f"Could not subscribe: {error}")
            return
        show = PodcastShow(
            id=new_id(),
            title=info.title or feed_url,
            feed_url=feed_url,
            homepage=info.homepage,
            artwork_url=info.artwork_url,
            feed_username=username,
            episodes=info.episodes,
        )
        added = self._library.add_show(show)
        if not added:
            self._status.SetLabel("You're already subscribed to that feed.")
            return
        if username and password:
            from quill.core.podcasts import feed_auth

            feed_auth.save_feed_password(show.id, password)
        self._on_library_changed()
        self._status.SetLabel(f"Subscribed to {show.title} ({len(show.episodes)} episodes).")
        self._announce(f"Subscribed to {show.title}")
        self._url_ctrl.SetValue("")

    def _prompt_for_credentials(self, feed_url: str, *, last_username: str) -> None:
        from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsDialog

        message = (
            "The username or password was not accepted. Try again."
            if last_username
            else ""
        )
        result = FeedCredentialsDialog(
            self.dialog,
            username=last_username,
            message=message,
            announce_cb=self._announce,
        ).show()
        if result is None or result.action != "save":
            self._status.SetLabel(
                "That feed requires a sign-in. Add it again when you have the credentials."
            )
            return
        self._subscribe_to_feed(
            feed_url, username=result.username, password=result.password
        )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/ui/test_podcast_add_dialog_auth.py -v`
Expected: PASS. Then compile-check: `python -c "import ast; ast.parse(open('quill/ui/podcasts/add_podcast_dialog.py', encoding='utf-8').read())"` and run any existing add-dialog tests: `python -m pytest tests/unit/ui -k add_podcast -v`.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/podcasts/add_podcast_dialog.py tests/unit/ui/test_podcast_add_dialog_auth.py
git commit -m "feat(podcasts): Add Podcast prompts for credentials on 401 and retries"
```

---

### Task 8: Wire credentials into refresh, downloads, transcripts, chapters

**Files:**
- Modify: `quill/ui/main_frame_podcasts.py` (`refresh_podcast_feed` ~line 713; `_maybe_backfill_always_sync` ~line 736/763; `_maybe_reload_podcast_chapters` ~line 145-153)
- Modify: `quill/ui/podcasts/manager_dialog.py` (`_on_download` ~line 1014-1019; `_on_chapters_click` ~line 825-835)
- Modify: `quill/ui/podcasts/manager_phase4.py` (`_fetch_transcript_then` ~line 730-741)
- Modify: `quill/ui/podcasts/show_actions.py` (`download_all_episodes` line 233-259)
- Test: `tests/unit/ui/test_podcast_feed_auth_wiring.py` (new, source-contract style)

**Interfaces:**
- Consumes: `feed_auth.auth_for_url` / `auth_header_for_url` (Task 1), `enqueue(..., auth_header=)` (Task 4), `fetch_and_parse_transcript/chapters(..., auth_header=)` (Task 5), `FeedAuthError` (Task 3).

- [ ] **Step 1: Write the failing source-contract test**

Create `tests/unit/ui/test_podcast_feed_auth_wiring.py`:

```python
"""Every per-show network call site passes gated credentials (spec D-1)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_feed_refresh_passes_credentials_and_reports_auth_failure() -> None:
    src = _read("ui/main_frame_podcasts.py")
    assert "auth_for_url(show, show.feed_url)" in src
    assert "FeedAuthError" in src
    assert "feed sign-in failed" in src


def test_downloads_pass_auth_header_everywhere() -> None:
    for rel in (
        "ui/main_frame_podcasts.py",
        "ui/podcasts/manager_dialog.py",
        "ui/podcasts/show_actions.py",
    ):
        assert "auth_header_for_url(show, episode.audio_url)" in _read(rel), rel


def test_chapters_and_transcripts_pass_auth_header() -> None:
    assert "auth_header_for_url(show, episode.chapters_url)" in _read(
        "ui/podcasts/manager_dialog.py"
    )
    assert "auth_header_for_url(show, episode.chapters_url)" in _read(
        "ui/main_frame_podcasts.py"
    )
    assert "auth_header_for_url(show, episode.transcript_url)" in _read(
        "ui/podcasts/manager_phase4.py"
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/ui/test_podcast_feed_auth_wiring.py -v`
Expected: FAIL on all three tests.

- [ ] **Step 3: Implement, one call site at a time**

Pattern -- compute credentials on the UI thread BEFORE `task_manager.submit` (the secret-store read is fast, and the worker closure then carries plain strings):

1. `main_frame_podcasts.refresh_podcast_feed` (line ~713):

```python
    def refresh_podcast_feed(self, show_id: str) -> None:
        from quill.core.podcasts import feed_auth, feed_reader

        show = self._podcast_library.find_show(show_id)
        if show is None or not show.feed_url or show.paused or self._safe_mode:
            return
        username, password = feed_auth.auth_for_url(show, show.feed_url)

        def _do_refresh(**_kwargs: object) -> feed_reader.FeedInfo:
            return feed_reader.fetch_and_parse_feed(
                show.feed_url, username=username, password=password, safe_mode=self._safe_mode
            )

        def _on_success(_op: str, info: feed_reader.FeedInfo) -> None:
            new_count = merge_episodes(show, info.episodes)
            self._save_podcast_library()
            if self._podcast_manager_dialog is not None:
                self._podcast_manager_dialog.refresh_tree()
            if new_count:
                self._announce(f"{new_count} new episode(s) for {show.title}")
            self._maybe_backfill_always_sync(show)

        def _on_failure(_op: str, exc: BaseException) -> None:
            if isinstance(exc, feed_reader.FeedAuthError):
                self._announce(
                    f"{show.title}: feed sign-in failed. Update credentials with "
                    "Feed Credentials on the show's menu."
                )

        self._task_manager.submit(
            "podcast-refresh", _do_refresh, on_success=_on_success, on_failure=_on_failure
        )
```

(No modal prompt here -- spec D-2.)

2. Each `enqueue` call site gains `auth_header=feed_auth.auth_header_for_url(show, episode.audio_url)`:
   - `show_actions.download_all_episodes` (line 253): add `from quill.core.podcasts import feed_auth` to the function's imports (top of module is fine -- it's wx-free) and the kwarg to the `enqueue(...)` call.
   - `manager_dialog._on_download` (~line 1019): `show = self._current_show` is in scope; add the kwarg.
   - `main_frame_podcasts._maybe_backfill_always_sync` (~line 763): `show` is the parameter; add the kwarg. Note `show` is typed `object` there -- keep the existing style (`getattr`-free direct attribute access is already used for `show.episodes`).

3. Chapters: in `manager_dialog._on_chapters_click` (~line 825-835) and `main_frame_podcasts._maybe_reload_podcast_chapters` (~line 145-153), compute `auth_header = feed_auth.auth_header_for_url(show, episode.chapters_url)` before the nested `_do_fetch`, and pass `auth_header=auth_header` to `fetch_and_parse_chapters`.

4. Transcripts: in `manager_phase4._fetch_transcript_then` (~line 730-741), compute `auth_header = feed_auth.auth_header_for_url(show, episode.transcript_url)` and pass it to `fetch_and_parse_transcript`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/ui/test_podcast_feed_auth_wiring.py tests/unit/ui -k podcast -v`
Expected: wiring tests PASS; no pre-existing podcast UI test regresses.

- [ ] **Step 5: Commit**

```bash
git add quill/ui/main_frame_podcasts.py quill/ui/podcasts/manager_dialog.py quill/ui/podcasts/manager_phase4.py quill/ui/podcasts/show_actions.py tests/unit/ui/test_podcast_feed_auth_wiring.py
git commit -m "feat(podcasts): pass gated credentials to refresh, downloads, transcripts, chapters"
```

---

### Task 9: Authenticated streaming playback

**Files:**
- Modify: `quill/core/podcasts/feed_auth.py` (add `playback_source`)
- Modify the seven `play_episode` call sites' `source` resolution: `quill/ui/podcasts/manager_dialog.py:878`, `quill/ui/podcasts/manager_phase4.py:~385`, `quill/ui/main_frame_podcasts.py:~214/~331/~361`, `quill/apps/podcasts.py:~385/~548`
- Test: `tests/unit/core/test_podcast_feed_auth.py` (extend), `tests/unit/ui/test_podcast_feed_auth_wiring.py` (extend)

**Interfaces:**
- Produces: `feed_auth.playback_source(show: PodcastShow, episode: PodcastEpisode) -> str` -- downloaded path if present, else `url_with_auth(show, episode.audio_url)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/core/test_podcast_feed_auth.py`:

```python
def test_playback_source_prefers_downloaded_path(monkeypatch) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    _patch_password(monkeypatch, "pw")
    show = _show()
    episode = PodcastEpisode(
        guid="g", title="E", audio_url="https://feeds.example.com/e.mp3",
        downloaded_path="C:/pods/e.mp3",
    )
    assert feed_auth.playback_source(show, episode) == "C:/pods/e.mp3"


def test_playback_source_embeds_auth_for_streaming(monkeypatch) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    _patch_password(monkeypatch, "pw")
    show = _show()
    episode = PodcastEpisode(
        guid="g", title="E", audio_url="https://feeds.example.com/e.mp3"
    )
    assert feed_auth.playback_source(show, episode) == (
        "https://member:pw@feeds.example.com/e.mp3"
    )
```

(Check `PodcastEpisode`'s actual required constructor fields in `models.py` and fill any others with defaults.)

Append to `tests/unit/ui/test_podcast_feed_auth_wiring.py`:

```python
def test_every_play_call_site_uses_playback_source() -> None:
    for rel in (
        "ui/podcasts/manager_dialog.py",
        "ui/podcasts/manager_phase4.py",
        "ui/main_frame_podcasts.py",
        "apps/podcasts.py",
    ):
        src = _read(rel)
        assert "playback_source(" in src, rel
        assert "episode.downloaded_path or episode.audio_url" not in src, rel
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/core/test_podcast_feed_auth.py tests/unit/ui/test_podcast_feed_auth_wiring.py -v`
Expected: new tests FAIL (`playback_source` missing; call sites unchanged).

- [ ] **Step 3: Implement**

Add to `feed_auth.py`:

```python
def playback_source(show: PodcastShow, episode: "PodcastEpisode") -> str:
    """What to hand the playback engine: the downloaded file when there is
    one, otherwise the stream URL -- with userinfo embedded when the
    same-host gate yields credentials (mpv and the ffmpeg relay accept
    userinfo URLs; QUILL's own log lines are scrubbed by
    ``quill.stability.redaction.redact_url_userinfo``)."""
    if episode.downloaded_path:
        return episode.downloaded_path
    return url_with_auth(show, episode.audio_url)
```

(Import `PodcastEpisode` at the top alongside `PodcastShow`.)

At each of the seven call sites, replace the `source = episode.downloaded_path or episode.audio_url` expression (or its inline equivalent inside the `play_episode(source=...)` argument) with `source = feed_auth.playback_source(show, episode)`, adding `from quill.core.podcasts import feed_auth` per file. Every site already has `show` and `episode` in scope (verified); if any resolves `show` only by id, use the existing `find_show` result already present in that function.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/core/test_podcast_feed_auth.py tests/unit/ui/test_podcast_feed_auth_wiring.py tests/unit/ui -k player -v`
Expected: ALL PASS (player controller tests unaffected -- the controller still receives a plain string).

- [ ] **Step 5: Commit**

```bash
git add quill/core/podcasts/feed_auth.py quill/ui/podcasts/manager_dialog.py quill/ui/podcasts/manager_phase4.py quill/ui/main_frame_podcasts.py quill/apps/podcasts.py tests/unit/core/test_podcast_feed_auth.py tests/unit/ui/test_podcast_feed_auth_wiring.py
git commit -m "feat(podcasts): authenticated streaming via playback_source"
```

---

### Task 10: Feed Credentials... menu item + credential cleanup on unsubscribe

**Files:**
- Modify: `quill/ui/podcasts/show_actions.py` (new `feed_credentials_prompt`; `unsubscribe_show_prompt` line 188-230)
- Modify: `quill/ui/podcasts/manager_dialog.py` (`_show_tree_context_menu` ~line 670-710; its own unsubscribe handler ~line 1160-1195)
- Modify: `quill/apps/podcasts.py` (`_on_library_context_menu` ~line 230-271 and its handler wiring)
- Test: `tests/unit/ui/test_podcast_show_actions_credentials.py` (new)

**Interfaces:**
- Consumes: `FeedCredentialsDialog` (Task 6), `feed_auth.save_feed_password/delete_feed_password` (Task 1), `PodcastShow.feed_username` (Task 2).
- Produces:

```python
def feed_credentials_prompt(parent, library: PodcastLibrary, show: PodcastShow,
                            *, announce: Callable[[str], None]) -> bool
```

Returns True when anything changed (caller saves the library).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/ui/test_podcast_show_actions_credentials.py`:

```python
"""Feed Credentials prompt + credential cleanup on unsubscribe."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "quill"


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_show_actions_exposes_feed_credentials_prompt() -> None:
    src = _read("ui/podcasts/show_actions.py")
    assert "def feed_credentials_prompt(" in src
    assert "FeedCredentialsDialog" in src
    assert "save_feed_password" in src
    assert "delete_feed_password" in src


def test_unsubscribe_deletes_stored_credentials_everywhere() -> None:
    assert "delete_feed_password(show.id)" in _read("ui/podcasts/show_actions.py")
    assert "delete_feed_password(show.id)" in _read("ui/podcasts/manager_dialog.py")


def test_context_menus_offer_feed_credentials() -> None:
    assert "Feed Credentials..." in _read("ui/podcasts/manager_dialog.py")
    assert "Feed Credentials..." in _read("apps/podcasts.py")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/unit/ui/test_podcast_show_actions_credentials.py -v`
Expected: FAIL on all three.

- [ ] **Step 3: Implement `feed_credentials_prompt` in `show_actions.py`**

```python
def feed_credentials_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Set, change, or clear the show's private-feed credentials.

    Saves the username on the show record and the password in the platform
    secret store; returns True when anything changed so the caller persists
    the library."""
    from quill.core.podcasts import feed_auth
    from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsDialog

    result = FeedCredentialsDialog(
        parent,
        username=show.feed_username,
        allow_clear=bool(show.feed_username),
        announce_cb=announce,
    ).show()
    if result is None:
        return False
    if result.action == "clear":
        show.feed_username = ""
        feed_auth.delete_feed_password(show.id)
        announce(f"Cleared feed credentials for {show.title}")
        return True
    show.feed_username = result.username
    if result.password:
        feed_auth.save_feed_password(show.id, result.password)
    announce(f"Saved feed credentials for {show.title}")
    return True
```

- [ ] **Step 4: Hook credential deletion into every unsubscribe path**

1. `show_actions.unsubscribe_show_prompt`: immediately before `library.remove_show(show.id)` (line 225) add:

```python
    from quill.core.podcasts import feed_auth

    feed_auth.delete_feed_password(show.id)
```

2. `manager_dialog`'s own unsubscribe handler (~line 1160-1195): find its `remove_show(show.id)` (or equivalent) call and add the same two lines before it.
3. Search the repo for `delete_folder(` calls with `contents="remove"` (`Grep: contents="remove"`). For each site that unsubscribes shows in bulk, loop the returned shows: `for removed in removed_shows: feed_auth.delete_feed_password(removed.id)`. If no caller uses `contents="remove"`, note that in the commit message and skip.

- [ ] **Step 5: Add the menu items**

1. `manager_dialog._show_tree_context_menu` (after the `pause_item` block, ~line 690):

```python
            if show.feed_url:
                creds_item = menu.Append(wx.ID_ANY, "Feed Cre&dentials...")
                creds_item.SetHelp(
                    "Username and password for a private feed (Patreon-style "
                    "supporter feeds). Only ever sent to this feed's own host."
                )
                menu.Bind(
                    wx.EVT_MENU,
                    lambda _e, s=show: self._on_feed_credentials(s),
                    creds_item,
                )
```

With the handler on the dialog class:

```python
    def _on_feed_credentials(self, show: object) -> None:
        from quill.ui.podcasts.show_actions import feed_credentials_prompt

        if feed_credentials_prompt(
            self.dialog, self._library, show, announce=self._announce
        ):
            self._on_library_changed()
```

(Match the class's actual attribute names -- `self._library` / `self._announce` / `self._on_library_changed` are the names used elsewhere in the file; verify at the existing `_on_refresh_feed` handler and mirror it, including how it persists the library.)

2. `apps/podcasts.py` `_on_library_context_menu`: add a `("Feed Cre&dentials...", self._on_feed_credentials_selected)` entry to the show-kind `entries` list (after "Remove All Episodes...", before "Unsubscribe"), skipped when the show has no `feed_url` (local shows). Handler, mirroring the neighboring `show_actions`-backed handlers (e.g. the `move_show_to_folder` one at ~line 319):

```python
    def _on_feed_credentials_selected(self) -> None:
        from quill.ui.podcasts.show_actions import feed_credentials_prompt

        show = self._selected_show()
        if show is None or not show.feed_url:
            return
        if feed_credentials_prompt(self, self._podcast_library, show, announce=self._announce):
            self._save_podcast_library()
```

(Verify the file's actual helper names for selected-show, library, save, and announce by reading the neighboring handlers first; mirror them exactly.)

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/unit/ui/test_podcast_show_actions_credentials.py tests/unit/ui -k "show_actions or podcast" -v`
Expected: new tests PASS; `test_podcast_show_actions_bulk.py` still green.

- [ ] **Step 7: Commit**

```bash
git add quill/ui/podcasts/show_actions.py quill/ui/podcasts/manager_dialog.py quill/apps/podcasts.py tests/unit/ui/test_podcast_show_actions_credentials.py
git commit -m "feat(podcasts): Feed Credentials menu item; delete stored secret on unsubscribe"
```

---

### Task 11: Full-suite verification and audit gates

**Files:**
- Possibly modify: `quill/tools/network_egress_audit.py`, `quill/tools/persistence_audit.py` expectations, `quill/tools/module_size_budgets.json`
- No new tests.

- [ ] **Step 1: Run the complete podcast test set**

Run: `python -m pytest tests/unit/core -k podcast -v; python -m pytest tests/unit/ui -k podcast -v`
Expected: ALL PASS.

- [ ] **Step 2: Run the audit gates**

Run: `python -m pytest tests -k "egress or persistence or inventory or budget" -v`
Expected: PASS. If the egress audit flags changed signatures, update only the prose justification strings for the podcast entries (no new sites were added). If the module size budget flags a grown file, raise its budget entry by the actual delta in `quill/tools/module_size_budgets.json` (note: this file currently has an unrelated merge conflict on `main` from another workstream -- in the worktree it will be clean; do not copy the conflicted version).

- [ ] **Step 3: Run the full unit suite once**

Run: `python -m pytest tests/unit -x -q`
Expected: PASS (matches pre-change baseline; if unrelated failures exist, verify they also fail on the branch point commit before ignoring: `git stash && python -m pytest <failing test> && git stash pop` equivalent via `git worktree` baseline).

- [ ] **Step 4: Manual smoke script (documented, run by the user or via /run)**

1. Launch Cast from source against the branch: `S:\quill-cast\run-quill-cast.bat` pointed at the worktree (or `python -m quill.apps.podcasts` from the worktree root).
2. Subscriptions > Add Podcast... > Add by Feed URL with a known-protected test feed (any URL returning 401) -- confirm the Feed Credentials dialog opens, Cancel leaves a clear status, wrong credentials re-prompt with username kept.
3. On a subscribed show: context menu > Feed Credentials... -- set, re-open (username prefilled), Clear Credentials.
4. Unsubscribe the show -- confirm no orphaned `quill-podcast-feed:*` entry remains (Windows Credential Manager > Generic Credentials).

- [ ] **Step 5: Commit any audit-expectation updates**

```bash
git add -A
git commit -m "chore(podcasts): audit-gate expectations for feed auth"
```

(Skip the commit if nothing changed.)
