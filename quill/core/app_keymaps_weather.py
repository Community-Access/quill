"""Quill Weather's menu accelerators (``APP_KEYMAPS["weather"]``).

Extracted from ``quill/core/app_keymaps.py`` under GATE-11 when Weather on a
Past Date and Weather History arrived: extract, never rebaseline.
``app_keymaps`` still owns the table; this module only holds Weather's rows and
the reasons for them.

Quill Radio carries this same Weather menu in its own window, so every key here
must be free in Radio too (``tests/unit/ui/test_menu_accelerators.py``).
"""

from __future__ import annotations

from quill.core.app_keymaps_ai import SMALL_APP_AI_KEYMAPS

WEATHER_KEYMAPS: dict[str, str] = {
    # Quill Weather drove its whole Weather menu from bound menu items and
    # had no command ids at all, so the Command Palette could not reach a
    # single weather verb and a tutorial step could not name one. These are
    # the ids, and their bindings are the keys those menu labels already
    # advertise -- the menu is unchanged; it simply has names now.
    "weather.now": "Ctrl+Shift+W",
    "weather.quick": "Ctrl+Shift+Q",
    "weather.alerts": "Ctrl+Shift+Alt+A",
    "weather.add_location": "Ctrl+Alt+Shift+L",
    "weather.settings": "Ctrl+Alt+Shift+F",
    "weather.test_alert": "Ctrl+Alt+Shift+T",
    # Alert Feed Status (H for health); Studio's H is another app's window.
    "weather.feed_status": "Ctrl+Alt+Shift+H",
    "weather.alert_choices": "Ctrl+Alt+Shift+C",
    "weather.watch_place": "Ctrl+Alt+Shift+U",
    "weather.monitor_toggle": "Ctrl+Alt+Shift+M",
    "weather.monitor_pause": "Ctrl+Alt+Shift+P",
    "weather.noaa_listen": "Ctrl+Alt+N",
    "weather.noaa_update": "Ctrl+Alt+Shift+N",
    # The guided lessons. Ctrl+Alt+F1 is the family key for them -- the same
    # chord opens the lessons in Quill Radio, QUILL Cast and QUILL -- and it
    # sits in the F1 family, which is where help lives everywhere.
    "weather.tutorials": "Ctrl+Alt+F1",
    # Weather on a Past Date: D for date. Ctrl+Shift+D is Radio's Output Device,
    # and Ctrl+Shift+P is the family's Command Palette, so it is Ctrl+Alt.
    "weather.past_date": "Ctrl+Alt+D",
    # Weather History: Ctrl+Shift, like Weather Now and Quick Weather, T for
    # past times. Radio's Ctrl+Shift+D and H are taken (Output Device, Song
    # History), and T is free in both.
    "weather.history": "Ctrl+Shift+T",
    # Next Few Hours: U for upcoming.
    "weather.next_hours": "Ctrl+Shift+U",
    # Report Fields: E for extra fields; once-a-year, so any free key (rule 9).
    "weather.report_fields": "Ctrl+Shift+E",
    # Weather Around Me, the spoken stand-in for radar: R for radar.
    "weather.around": "Ctrl+Shift+R",
    **SMALL_APP_AI_KEYMAPS["weather"],  # AI rows, rule-11 comments: app_keymaps_ai.py
}
