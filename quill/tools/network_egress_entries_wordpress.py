"""Reviewed egress for File > WordPress, in QUILL and QUILL Lite (wordpress.md 14).

Split out of ``network_egress_entries`` under GATE-11, like Radio's and Cast's.
Every WordPress request goes through two doors, so two entries cover the REST
routes, sign-in and media; the routes each door carries are listed in the
rationale, because that list is the review.
"""

from __future__ import annotations

WORDPRESS_EGRESS: dict[str, str] = {
    "core/wordpress/api.py::send_to_site": (
        "Every request to a WordPress site the person connected (File > WordPress, "
        "both editors). Self-hosted sites at <site>/wp-json/, WordPress.com sites at "
        "public-api.wordpress.com/wp/v2/sites/<site>/. Routes: the REST index; "
        "users/me (roles and capabilities); pages, posts and custom types (list, "
        "load, create, update, trash, restore, autosaves, revisions); categories, "
        "tags and taxonomies; media (list, upload, update, delete, and downloading a "
        "file for the local backup made before removing it); comments; search; "
        "batch/v1; settings, menus, menu items, menu locations, navigation, "
        "sidebars, widgets, templates, template parts, block patterns, block "
        "renderer, users, application passwords, plugins, themes, fonts, synced "
        "patterns, and oembed/1.0/proxy. Each is an explicit command or the "
        "two-minute autosave of a document the person opened from the site. Sends "
        "the account's application password (Basic) or WordPress.com token "
        "(Bearer) over HTTPS only; plain HTTP only to loopback or .test hosts. The "
        "secret lives in Credential Manager and never in a repr or a log. Off in "
        "Safe Mode and when the WordPress feature is off. The same door also "
        "carries Media and Files > Upload from Web Address: one GET to the HTTPS "
        "address the person typed (any host, by design), capped at 64 MB, content "
        "type checked, no redirect to plain HTTP, and no WordPress credential sent "
        "to that host. Caption tracks for the Media Library player (WebVTT, "
        "only from the connected site's own host) also come through here. The "
        "player itself streams an audio or video file's HTTPS address through the "
        "shared playback engine, with no credential, only when the person "
        "chooses Play or Play Media Here; nothing is saved. Forms (wordpress.md "
        "17a.7, 17a.8, 17a.17), only on a site whose REST index lists qaf/v1 "
        "(QUILL Accessible Forms), or baf/v1, its older name, kept as an alias "
        "for one release; whichever it lists is used for every call: "
        "qaf/v1/forms (list, read, create and update -- "
        "Publish Form, after a confirmation naming the site, and the per-form "
        "response count spoken once a session, which can be turned off per site), "
        "qaf/v1/entries (the responses, read only while Responses is open; "
        "deleting one moves it to QAF's Trash, after a confirmation with the "
        "count), and a search of wp/v2/pages and wp/v2/posts for the page that "
        "shows a form (Test on Site). Responses are never logged and leave only to "
        "a file the person chooses. Off in Safe Mode."
    ),
    "core/wordpress/cdp.py::__init__": (
        "Check This Page and Visual Review: QUILL starts Edge or Chrome hidden, from "
        "their standard install folders only, with remote debugging on 127.0.0.1, "
        "and drives it over this loopback socket. Nothing here leaves the machine; "
        "the browser itself then loads the site's public page, exactly as a visitor "
        "would, and axe-core runs inside it on this computer. Only on the person's "
        "command; off in Safe Mode."
    ),
    "core/wordpress/signin.py::_token_urlopen": (
        "WordPress.com sign-in (Connect a Site, WordPress.com): exchanges the "
        "authorization code (OAuth 2.1 with PKCE, as a public client, so no secret "
        "ships) or a refresh token for an access token at "
        "public-api.wordpress.com/oauth2/token. Only after the person approved "
        "QUILL in their own browser; the reply returns to a one-shot listener on "
        "127.0.0.1. Tokens go to Credential Manager. Off in Safe Mode."
    ),
    # The older publishing core, which File > WordPress replaced; its client still
    # backs the one-time import of saved connections (quill/core/publishing.py).
    "core/publishing_clients.py::verify_connection": (
        "User-initiated publishing connection verification from the Publishing "
        "Connections dialog. Runs only when the user explicitly verifies a saved "
        "connection; remote endpoints are HTTPS-enforced and HTTPS uses a verified "
        "TLS context."
    ),
    "core/publishing_clients.py::_request_json": (
        "User-initiated publishing browse, open, create, update, and schedule "
        "requests from the Publish menu and publishing dialogs. Runs only when "
        "the user explicitly loads, sends, or schedules content through a saved "
        "connection; remote endpoints are HTTPS-enforced and HTTPS uses a "
        "verified TLS context."
    ),
}
