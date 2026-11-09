"""The Command Key's reviewed outbound call (docs/design/command-key.md 7.6 and 7.9).

Split out of ``network_egress_entries`` under GATE-11, like the Radio, speech and GitHub
tables beside it: the entry text is the review record and is unchanged.
"""

from __future__ import annotations

COMMAND_KEY_EGRESS: dict[str, str] = {
    "core/command_catalogue/jev.py::_post_json": (
        "The Command Key's one outbound call (docs/design/command-key.md 7.6 and 7.9): "
        "Jev, TypeSafe's decision model, asked to pick one of this window's commands "
        "for a sentence the offline matcher could not settle. Two routes share it: "
        "POST https://api.typesafe.ai/v1/systemone with the person's own TypeSafe key "
        "(read from Windows Credential Manager, generic credential 'QUILL TypeSafe "
        "dev key'), and POST <gateway>/v1/decide with the QUILL device token once "
        "the Community Access gateway route is deployed (it is not; the route "
        "answers disabled). Sends only what jev_request.build_request built and "
        "checked: the words typed or heard (at most 300 characters), the app id, "
        "the surface name, recent command ids, whether a number or duration was "
        "found, and the candidate commands' own descriptions. Never document text, "
        "file names, stations, places or accounts (payload_is_private, refused "
        "before sending). User-initiated: only after the person typed into the "
        "Command Key and only when command_understanding is 'jev', which they chose "
        "in the consent question. TLS with a verified context; three-second budget; "
        "one request in flight. TypeSafe keep requests and do not train on them. "
        "Off in Safe Mode (the Command Key builds no assist there)."
    ),
}
