"""Every route, and the value still to add: the 9.16 commands in one mixin (wordpress.md 9.16).

:class:`WordPressRouteCommands` gathers the 9.16 mixins, so
:class:`~quill.ui.wordpress_commands.WordPressCommands` takes them as one
base. Each command asks the site's REST index first
(:class:`~quill.ui.wordpress_route_base.WordPressRouteBase`): a site without
the route never gets the request, and the person hears why.
"""

from __future__ import annotations

from quill.ui.wordpress_route_archive import WordPressRouteArchive
from quill.ui.wordpress_route_base import WordPressRouteBase
from quill.ui.wordpress_route_copies import WordPressRouteCopies
from quill.ui.wordpress_route_history import WordPressRouteHistory
from quill.ui.wordpress_route_links import WordPressRouteLinks
from quill.ui.wordpress_route_media import WordPressRouteMedia


class WordPressRouteCommands(
    WordPressRouteLinks,
    WordPressRouteMedia,
    WordPressRouteHistory,
    WordPressRouteCopies,
    WordPressRouteArchive,
    WordPressRouteBase,
):
    """The 9.16 commands; see each mixin for what it does."""
