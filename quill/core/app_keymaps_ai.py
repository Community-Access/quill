"""The AI keys of the small QuillVille apps (codex.md Phase 3), merged into APP_KEYMAPS.

Split out of :mod:`quill.core.app_keymaps` under GATE-11 when Quill Weather,
Quill Converter, Quill Media Player, Quill Inkwell and QuillBeacon joined Choose
Your AI. :data:`quill.core.app_keymaps.APP_KEYMAPS` merges these rows in at
import, so everything that reads that table sees them. Every key that differs
from the editors' has its comment here and a row in
:data:`quill.core.app_ai_keys.APP_AI_DIVERGENCES` (rule 11). wx-free.
"""

from __future__ import annotations

__all__ = ["SMALL_APP_AI_KEYMAPS"]

SMALL_APP_AI_KEYMAPS: dict[str, dict[str, str]] = {
    "weather": {
        # The family's AI (codex.md Phase 3). Ctrl+1 to Ctrl+9 are this app's
        # Window menu keys (quill/ui/window_menu.py), so the editors' Ctrl+4,
        # Ctrl+6 and Ctrl+8 would each be claimed twice: it takes Quill Radio's,
        # QUILL Cast's and QUILL Transcribe's set -- Ask Ctrl+Shift+8, Which AI
        # Ctrl+F8, Choose Your AI Ctrl+Shift+F8 (rule 2). Each divergence is
        # this comment and an app_ai_keys row (rule 11); the rest are the
        # editors' keys, written out so the AI menu shows them.
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Ctrl+Alt+Shift+K",
        # Should I Go Out? (codex.md 6.9): G for go, free in this bar.
        "weather.ai_go_out": "Ctrl+Shift+G",
    },
    # Quill Converter's AI rows (codex.md Phase 3); its other keys are literal
    # labels in converter_menu.py.
    "converter": {
        # The family's AI (codex.md Phase 3). Ctrl+1 to Ctrl+9 are this app's
        # Window menu keys (quill/ui/window_menu.py), so the editors' Ctrl+4,
        # Ctrl+6 and Ctrl+8 would each be claimed twice: it takes Quill Radio's,
        # QUILL Cast's and QUILL Transcribe's set -- Ask Ctrl+Shift+8, Which AI
        # Ctrl+F8, Choose Your AI Ctrl+Shift+F8 (rule 2). Each divergence is
        # this comment and an app_ai_keys row (rule 11); the rest are the
        # editors' keys, written out so the AI menu shows them.
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Ctrl+Alt+Shift+K",
        # Will This Play on My Device? (codex.md 10E.7): D for device, free here.
        "converter.ai_will_play": "Ctrl+Shift+D",
    },
    # Quill Media Player's AI rows (codex.md Phase 3); its other keys are
    # literal labels in player_menus.py.
    "player": {
        # The family's AI (codex.md Phase 3). Ctrl+1 to Ctrl+9 are this app's
        # Window menu keys (quill/ui/window_menu.py), so the editors' Ctrl+4,
        # Ctrl+6 and Ctrl+8 would each be claimed twice: it takes Quill Radio's,
        # QUILL Cast's and QUILL Transcribe's set -- Ask Ctrl+Shift+8, Which AI
        # Ctrl+F8, Choose Your AI Ctrl+Shift+F8 (rule 2). Each divergence is
        # this comment and an app_ai_keys row (rule 11); the rest are the
        # editors' keys, written out so the AI menu shows them.
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Ctrl+Alt+Shift+K",
        # The two recaps keep the keys their menu rows always showed (rule 5);
        # they have command ids now and use the AI in use (codex.md 10E.8).
        "player.ai_chapter_summary": "Ctrl+Alt+C",
        "player.ai_recap": "Ctrl+Alt+R",
    },
    # Quill Inkwell's AI rows (codex.md Phase 3); its other keys are literal
    # labels in inkwell.py. Privacy Agreement takes Radio's and Cast's
    # Alt+Shift+F2: Ctrl+Alt+Shift+K is Inkwell's Quick Insert Key (rule 11).
    "inkwell": {
        # The family's AI (codex.md Phase 3). Ctrl+1 to Ctrl+9 are this app's
        # Window menu keys (quill/ui/window_menu.py), so the editors' Ctrl+4,
        # Ctrl+6 and Ctrl+8 would each be claimed twice: it takes Quill Radio's,
        # QUILL Cast's and QUILL Transcribe's set -- Ask Ctrl+Shift+8, Which AI
        # Ctrl+F8, Choose Your AI Ctrl+Shift+F8 (rule 2). Each divergence is
        # this comment and an app_ai_keys row (rule 11); the rest are the
        # editors' keys, written out so the AI menu shows them.
        "tools.hosted_ai_chat_key": "Ctrl+Shift+8",
        "tools.hosted_ai_which": "Ctrl+F8",
        "tools.hosted_ai_choose": "Ctrl+Shift+F8",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Alt+Shift+F2",
        # Suggest Abbreviations from a Document (codex.md 6.12): free here.
        "inkwell.ai_suggest": "Ctrl+Shift+A",
    },
    # QuillBeacon's AI rows (codex.md Phase 3), in its Assist menu after the
    # three local helpers. Beacon has no Window menu and no Ctrl+digit key, so
    # decision 14's Ctrl+6, Ctrl+8 and Ctrl+4 hold, as in DEFAULT_KEYMAP; the
    # rows are written out because Beacon's menu reads its keys from here.
    "beacon": {
        "tools.hosted_ai_chat_key": "Ctrl+6",
        "tools.hosted_ai_which": "Ctrl+8",
        "tools.hosted_ai_choose": "Ctrl+4",
        "tools.hosted_ai_chatgpt": "Alt+F5",
        "tools.hosted_ai_own_key": "Alt+F2",
        "tools.hosted_ai_usage": "Ctrl+Alt+Shift+F2",
        "tools.hosted_ai_privacy": "Ctrl+Alt+Shift+K",
        # Describe a Saved Picture: the family's Describe key (codex.md 10B.6).
        "beacon.describe_picture": "Ctrl+F5",
    },
}
