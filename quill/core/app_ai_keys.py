"""Where a QuillVille app's AI keys differ from the editors' (rule 11).

Choose Your AI, Which AI Am I Using and Ask are Ctrl+4, Ctrl+8 and Ctrl+6 in
QUILL and QUILL Lite (codex.md 10A.9). Quill Radio and QUILL Cast cannot use
them: Ctrl+1 to Ctrl+9 are their Window menu keys on every window. Each such
divergence is a comment where the key is set (``app_keymaps.APP_KEYMAPS``) and
a row here, and ``tests/unit/core/test_app_ai_keys.py`` holds both halves: every
row still diverges, and no AI command an app binds differs without a row.
wx-free.
"""

from __future__ import annotations

__all__ = ["APP_AI_DIVERGENCES"]

#: Where an app's AI key differs from the editors' (rule 11: every divergence is
#: a comment and a row). ``(app, command id) -> reason``;
#: ``tests/unit/core/test_app_ai_keys.py`` checks each row still diverges and
#: that no AI command an app binds differs without one.
APP_AI_DIVERGENCES: dict[tuple[str, str], str] = {
    **{
        (app, command): (
            "Ctrl+1 to Ctrl+9 are this app's Window menu keys on every window "
            "(quill/ui/window_menu.py), so the editors' plain-digit AI keys would "
            "each be claimed twice. Which AI is Ctrl+F8, Choose Your AI "
            "Ctrl+Shift+F8 and Ask Ctrl+Shift+8, the same in Quill Radio and "
            "QUILL Cast (rule 2)."
        )
        for app in ("radio", "cast")
        for command in ("tools.hosted_ai_which", "tools.hosted_ai_choose")
    },
    ("cast", "tools.hosted_ai_chat_key"): (
        "Ctrl+6 is window 6 on Cast's Window menu and Quick Action 6 in an episode "
        "list; Ask takes Quill Radio's Ask key, Ctrl+Shift+8 (rule 2)."
    ),
    ("cast", "tools.hosted_ai_image"): (
        "Ctrl+F5 is Refresh All in QUILL Cast, so its Describe key is Ctrl+Alt+F5."
    ),
    ("cast", "tools.hosted_ai_privacy"): (
        "Ctrl+Alt+Shift+K is Cast's Keyboard Shortcuts Sheet; Privacy Agreement "
        "sits on Alt+Shift+F2, beside the own key's Alt+F2."
    ),
    ("radio", "tools.hosted_ai_privacy"): (
        "Ctrl+Alt+Shift+K is Radio's Keyboard Shortcuts Sheet; Privacy Agreement "
        "takes Cast's Alt+Shift+F2."
    ),
}
