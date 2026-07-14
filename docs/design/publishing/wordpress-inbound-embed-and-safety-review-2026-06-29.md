# WordPress Inbound Embed Map and Safety Review

Date: 2026-06-29
Scope: Audit the WordPress publishing code already shipped in `main`, document
exactly where the inbound (read-only) touchpoints embed, confirm the safety
posture, and confirm that no content-send path is lit up in a public build.

This review intentionally changes no behavior. It is a checkpoint over the
existing implementation plus recommendations for a future, separately approved
inbound-only release.

## 1. Summary of findings

- The WordPress provider is fully implemented in `main` for both directions:
  inbound (verify, browse, load) and outbound (create, update, publish,
  schedule, compare).
- The entire surface is gated behind the `future.publishing` feature, which is
  `locked_off=True` in `quill/core/feature_catalog.py`. In a public build the
  Publish submenu is omitted and every `publishing.*` command is filtered out of
  the command palette, so nothing - inbound or outbound - is reachable.
- The network layer is already hardened: an HTTPS-only endpoint policy, verified
  TLS contexts, egress-audit registration, and OS-backed secret storage.
- Conclusion: "do not light up the code to send content to WordPress" is already
  satisfied by the locked feature flag. No change was required to keep send dark.

## 2. Where the inbound touchpoints embed

### 2.1 Add an account (connection)

- Command: `publishing.connections` ("Publishing Connections...").
- Registered: `quill/ui/main_frame.py` (command registry) -> handler
  `MainFrame._open_publishing_connections` (`main_frame.py:12470`).
- Dialog: `PublishingConnectionsDialog` in `quill/ui/publishing_tools.py`.
- Menu: File > Publish submenu, built in `quill/ui/main_frame_menu.py` only when
  `self._feature_enabled("future.publishing")` is true (currently false).
- Core: `quill/core/publishing.py` connection store
  (`load/save/upsert/remove/set_current/current_publishing_connection`) writes
  `publishing-connections.json` atomically. Application passwords are stored via
  Windows Credential Manager, falling back to DPAPI-protected JSON
  (`save_publishing_secret` / `load_publishing_secret`).

### 2.2 Show pages and posts

- Command: `publishing.browse_content` ("Browse Publishing Content...").
- Handler: `MainFrame._browse_publishing_content` (`main_frame.py:12499`).
- Dialog: `BrowsePublishingContentDialog` (`quill/ui/publishing_tools.py`), which
  runs the network load on `QuillTaskManager` with a real Cancel button.
- Core: `browse_publishing_content` (`publishing.py:295`) ->
  `WordPressPublishingClient.browse_content` (`publishing_clients.py:177`), which
  reads `wp-json/wp/v2/posts` and `.../pages` with `context=edit`,
  `status=publish,draft`, and a trimmed `_fields` projection.

### 2.3 Load one into the editor

- Inside the browse dialog, selecting an item loads it via
  `load_publishing_remote_item` (`publishing.py:349`) ->
  `WordPressPublishingClient.load_remote_item` (`publishing_clients.py:243`).
- Back in `_browse_publishing_content`, the returned `PublishingRemoteDocument`
  is passed through `prepare_publishing_remote_content` (readable Markdown when
  safe, raw HTML when the body contains tables/forms/embeds), wrapped in a
  `Document` with `source_metadata["source_kind"] = "publishing_remote"`, and
  opened as a new tab via `_create_document_tab`.
- The `source_metadata` keys (provider id, site URL, remote id, content kind,
  status, updated-at) are what later enable compare/update - they are the
  linkage that an outbound flow would consume, and they are harmless to populate
  on the inbound path.

## 3. Safety posture (verified)

- Endpoint policy: `_validate_endpoint_security` (`publishing.py:715`) is called
  at the top of verify, browse, load, update, and create. It allows `https` to
  any host, allows `http` only to loopback/private hosts (`_is_local_host`), and
  rejects every other scheme (including `file:`, `ftp:`, `gopher:`). This blocks
  cleartext credential leakage to remote hosts and blocks local-file/SSRF-style
  schemes. Covered by tests (`tests/unit/core/test_publishing.py:167`).
- TLS: every HTTPS request uses `verified_ssl_context()` (`quill/core/net.py`),
  which keeps `check_hostname=True` and `verify_mode=CERT_REQUIRED`.
- Egress audit: both call sites are registered in
  `quill/tools/network_egress_audit.py`
  (`core/publishing_clients.py::verify_connection` and `::_request_json`), so
  GATE-9 accounts for them.
- Secrets: never written to plaintext. Windows Credential Manager first, then
  DPAPI-protected JSON; `clear_publishing_secret` removes both. Application
  passwords are sent only as a per-request Basic header, never persisted in the
  connection profile.
- Feature gating: `future.publishing` is `locked_off=True`; the menu is omitted
  (`main_frame_menu.py:207`) and the palette filters by
  `feature_for_command` -> `future.publishing`
  (`quill/core/feature_command_map.py:317-328`).

## 4. Confirmation: send is not lit

Outbound commands exist and are registered for keymap/palette stability
(`publishing.create_draft`, `publish_current`, `create_page_draft`,
`publish_current_page`, `update_remote_item`, `publish_remote_item`,
`schedule_publish`), but all map to `future.publishing` and are therefore
unreachable while it is locked off. No outbound path is exposed in a public
build, and this review adds none.

## 5. Recommendations

1. (Implemented 2026-06-30, on branch `feature/publishing-google-wp-polish`.)
   Split the feature so inbound can ship without outbound. A new
   `future.publishing_read` feature (not locked) now gates the read-only inbound
   commands (`publishing.connections`, `publishing.verify_connection`,
   `publishing.browse_content`, `publishing.open_remote_item`); the send commands
   stay under the locked-off `future.publishing`. The Publish submenu is built in
   two independently gated halves (`main_frame_menu.py`). `future.publishing_read`
   is on by default only in the Full Quill profile; off elsewhere, individually
   enableable via Manage Individual Features. This lets a release expose "open my
   WordPress posts/pages in QUILL" while keeping create/update/publish/schedule
   locked.
2. Consider tightening HTTP allowance. `_is_local_host` currently permits `http`
   to private LAN ranges (10/8, 172.16/12, 192.168/16), which would send the
   Basic application-password header in cleartext across a LAN. Narrowing the
   HTTP exception to loopback only (localhost, 127.0.0.0/8, ::1) is a defensible
   hardening, weighed against self-hosted WordPress on a LAN over plain HTTP.
3. Defense in depth (optional). The endpoint policy is enforced only in
   `publishing.py`. A future non-WordPress client could call the network helper
   directly. Moving the policy into `quill/core/net.py` and enforcing it inside
   `publishing_clients._request_json` / `verify_connection` would make the guard
   intrinsic to the client. Low marginal value today (nothing bypasses
   `publishing.py`), but cheap and worth doing if a second provider lands.
