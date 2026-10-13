"""QUILL Lineups: rule-built, hand-ordered lists of anything Radio and Cast can play.

A Lineup is a named list of references (:class:`~quill.core.lineups.refs.ItemRef`)
to things that already exist in Radio or Cast -- stations, browse places,
podcast shows and episodes, YouTube videos, playlists and channels, local media
and recordings. Rules bring items in and each rule's Keep choice says when they
go; the listener's own moves, keeps and removals always outrank the rules.

Everything in this package is wx-free and strictly typed. The design, with the
reasons behind every rule below, is ``docs/design/2026-10-13-lineups.md``.

Modules, in dependency order:

* :mod:`refs` -- what an item *is*: a kind plus the key its owner already uses.
* :mod:`fields` -- what a rule can ask about each kind.
* :mod:`conditions` -- one test (field, test, value), never raising.
* :mod:`rules` -- a rule: kind, scope, tests, order, limits, Keep.
* :mod:`keep` -- when an item goes, and which claim wins.
* :mod:`model` -- a Lineup, its rows, Removed Items and Recently Left.
* :mod:`merge` -- one refresh: rule results plus hand edits gives the list.
* :mod:`ops` -- every change as an operation named by keys.
* :mod:`store` -- the shared ``lineups.json``, safe for two apps at once.
* :mod:`sources` -- read-only adapters over Radio's stores and Cast's library.
* :mod:`describe` -- the sentences: rules, rows, moves, reasons, refreshes.
"""
