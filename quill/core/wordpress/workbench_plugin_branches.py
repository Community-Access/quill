"""Which site branches belong to a plugin, so a site without it does not show them.

Review item 30: every site had every plugin's branch whether the plugin was
there or not (over a hundred nodes a site), and each one read the network to
say it was empty. A branch here is left out of a site whose REST index, read
once when the Workbench discovers the site, lists none of its namespaces. Until
that index is read, every branch shows, so nothing is hidden on a guess.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from quill.core.forms.qaf_site import NAMESPACES as QAF_NAMESPACES
from quill.core.wordpress.plugin_events import NAMESPACE as EVENTS_NAMESPACE
from quill.core.wordpress.plugin_shop_seo import SEO_NAMESPACES
from quill.core.wordpress.workbench_forms import GRAVITY_NAMESPACE
from quill.core.wordpress.workbench_sweep import REDIRECTION_NAMESPACE

__all__ = ["PLUGIN_BRANCHES", "shows"]

#: Site node key -> the namespaces, any one of which means its plugin is there.
PLUGIN_BRANCHES: Mapping[str, tuple[str, ...]] = {
    "shop": ("wc/v3",),
    "shop_analytics": ("wc-analytics",),
    "memberships": ("pmpro/v1",),
    "events": (EVENTS_NAMESPACE,),
    "seo": tuple(SEO_NAMESPACES),
    "redirects": (REDIRECTION_NAMESPACE,),
    "forms": (GRAVITY_NAMESPACE, *QAF_NAMESPACES),
}


def shows(node_key: str, namespaces: Iterable[str] | None) -> bool:
    """Whether a site whose REST index lists *namespaces* shows *node_key*.

    *namespaces* None means the index has not been read yet: show it.
    """
    wanted = PLUGIN_BRANCHES.get(node_key)
    if wanted is None or namespaces is None:
        return True
    have = {str(n).strip("/") for n in namespaces}
    return any(n.strip("/") in have for n in wanted)
