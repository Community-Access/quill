"""Where a QuillVille app's AI keys differ from the editors' (rule 11).

Choose Your AI, Which AI Am I Using and Ask are Ctrl+4, Ctrl+8 and Ctrl+6 in
QUILL and QUILL Lite (codex.md 10A.9). Quill Radio, QUILL Cast, QUILL
Transcribe, Quill Weather, Quill Converter, Quill Media Player and Quill Inkwell
cannot use them: Ctrl+1 to Ctrl+9 are their Window menu keys on every window.
QUILL Studio and QuillBeacon have no Window menu and keep them. Each such
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
    # QUILL Transcribe (codex.md Phase 3): the same Window menu reason as Radio
    # and Cast, so the same three keys.
    **{
        ("transcribe", command): (
            "Ctrl+1 to Ctrl+9 are QUILL Transcribe's Window menu keys "
            "(quill/ui/window_menu.py), so the editors' plain-digit AI keys would "
            "each be claimed twice. It takes Quill Radio's and QUILL Cast's set: "
            "Ask Ctrl+Shift+8, Which AI Ctrl+F8, Choose Your AI Ctrl+Shift+F8 (rule 2)."
        )
        for command in (
            "tools.hosted_ai_chat_key",
            "tools.hosted_ai_which",
            "tools.hosted_ai_choose",
        )
    },
    ("transcribe", "tools.hosted_ai_privacy"): (
        "Ctrl+Alt+Shift+K is QUILL Transcribe's Command Key; Privacy Agreement takes "
        "Radio's and Cast's Alt+Shift+F2."
    ),
    # Quill Weather, Quill Converter, Quill Media Player and Quill Inkwell
    # (codex.md Phase 3): the same Window menu reason, so the same three keys.
    **{
        (app, command): (
            "Ctrl+1 to Ctrl+9 are this app's Window menu keys "
            "(quill/ui/window_menu.py), so the editors' plain-digit AI keys would "
            "each be claimed twice. It takes Quill Radio's, QUILL Cast's and QUILL "
            "Transcribe's set: Ask Ctrl+Shift+8, Which AI Ctrl+F8, Choose Your AI "
            "Ctrl+Shift+F8 (rule 2)."
        )
        for app in ("weather", "converter", "player", "inkwell")
        for command in (
            "tools.hosted_ai_chat_key",
            "tools.hosted_ai_which",
            "tools.hosted_ai_choose",
        )
    },
    ("inkwell", "tools.hosted_ai_privacy"): (
        "Ctrl+Alt+Shift+K is Quill Inkwell's Quick Insert Key; Privacy Agreement takes "
        "Radio's and Cast's Alt+Shift+F2."
    ),
    # The agent tasks (codex.md Phase 4c): each app's task is the family's Do a
    # Task command, Ctrl+3 in the editors, Studio and Beacon. Where Ctrl+3 is
    # window 3 it takes Ctrl+F3, the way Which AI moved from Ctrl+8 to Ctrl+F8
    # (app_keymaps_ai.AGENT_TASK_KEYMAPS).
    **{
        (app, "tools.hosted_ai_task"): (
            "Ctrl+3 is window 3 on this app's Window menu (quill/ui/window_menu.py), "
            "so the agent task moves to the F-row as Which AI did, Ctrl+8 to Ctrl+F8: "
            "Ctrl+F3, the same in every app with a Window menu (rule 2)."
        )
        for app in ("radio", "cast", "transcribe", "converter", "player", "inkwell")
    },
    # QuillBeacon keeps the editors' Ctrl+4, Ctrl+6 and Ctrl+8 (no Window menu).
    # QUILL Studio keeps the editors' Ctrl+4, Ctrl+6 and Ctrl+8 (no Window menu).
    ("studio", "tools.hosted_ai_privacy"): (
        "Ctrl+Alt+Shift+K is Studio's Ask AI About a Video; Privacy Agreement takes "
        "Radio's and Cast's Alt+Shift+F2."
    ),
}
