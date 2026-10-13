"""The QUILL Lineups window, shared by Quill Radio and Quill Cast.

One window module serves both apps: the same lists, keys, menus, sentences and
rule editor, because the command both products have keeps the chord (family
rule 2) and a listener who learns Lineups in one app has learned it in both.
What differs -- how a row plays, which app menu sits beside the window's own,
where the start Lineup is remembered -- is behind :class:`LineupsHost`, which
each app implements in a few lines (``quill/ui/radio/lineups_host.py`` and
``quill/ui/podcasts/lineups_host.py``).

The engine is wx-free in ``quill/core/lineups``; nothing here decides what a
rule finds or when an item leaves, it only shows and edits.
"""
