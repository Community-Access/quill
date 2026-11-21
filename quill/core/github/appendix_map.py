"""The GitHub PRD's Appendix A, B and C as data, so the tables cannot drift from the code.

Appendix A and B say where every retired window's view, button and command
went ("nothing dropped"); Appendix C says, for every object, its Properties
sheet and what its list filters on. The rows are in
:mod:`quill.core.github.appendix_ab_rows` and
:mod:`quill.core.github.appendix_c_rows`; the Explore and GitHub Items views
are not written out at all but read from their own registries, each with the
node that is its home.

Every home is a *ref* the gate resolves against a real registry:

- ``node:<key>`` a fixed tree node, ``node:<template>.<key>`` a templated one;
- ``menu:<verb>`` a row of the Workbench's menu bar;
- ``row:<row type>.<verb>`` a command on a row's context menu (and Item menu);
- ``new:<node key>`` what New Here (Ctrl+N) makes in that node;
- ``sheet:<kind>.<page>[.<field>]`` a Properties sheet page or field;
- ``pref:<name>`` a Workbench Options choice, ``prefpage:<title>`` a page;
- ``editor:<command id>`` a row of the editor's GitHub menu;
- ``door:<command id>`` an editor command that opens the Workbench at a node;
- ``repoaction:<command>`` a row of Repository > Repository Actions...;
- ``code:<path>#<text>`` a control inside a window a ref above opens.

A row whose old thing is gone, or not reachable yet, says why in *reason*.
``python -m quill.tools.github_appendix_reference`` resolves every ref and
writes the generated tables into the PRD. wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Filter", "Home", "ObjectEntry"]


@dataclass(frozen=True)
class Home:
    """One Appendix A or B row: what it was, where it is now, and the refs that prove it.

    *labels* are the retired window's own control labels this row accounts
    for (the gate scans those windows for any it does not). *sheet* and
    *sheet_refs* are Appendix B's "On the Properties sheet" column.
    """

    section: str
    today: str
    home: str
    refs: tuple[str, ...] = ()
    reason: str = ""
    labels: tuple[str, ...] = ()
    sheet: str = ""
    sheet_refs: tuple[str, ...] = ()


#: How a filter is answered.
HERE, SEARCH, NOT_YET = "here", "search", "not yet"


@dataclass(frozen=True)
class Filter:
    """One of Appendix C's filters: the qualifier typed, and how it is answered.

    ``here`` is checked over the loaded rows (:data:`quill.core.github.object_filters.LOCAL`
    must answer *key* for the object's row types); ``search`` is GitHub's own
    search syntax, sent whole; ``not yet`` names why, in *why*.
    """

    words: str
    key: str = ""
    how: str = HERE
    why: str = ""


@dataclass(frozen=True)
class ObjectEntry:
    """One Appendix C object: its sheet, the rows that stand for it, and its filters.

    *sheets* are kinds of :data:`quill.core.github.sheet_catalog.SHEETS`; an
    object with none names its other home in *home* and why in *reason*.
    """

    name: str
    sheets: tuple[str, ...]
    row_types: tuple[str, ...]
    filters: tuple[Filter, ...] = ()
    home: str = ""
    reason: str = ""
