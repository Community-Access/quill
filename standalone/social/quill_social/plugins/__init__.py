"""Bundled and third-party plugin host package (PRD 34).

QUILL Social is extended through plugins: network adapters, importers/exporters,
AI providers, media resolvers, soundpacks, composer tools, folder rules,
automation actions, project connectors, and accessibility enhancements. The
*mechanism* -- manifest validation, declared-permission enforcement, safe mode,
and crash isolation -- lives in ``quill_social.services.plugins``; this package
is the namespace where first-party plugin modules live and where a discovered
third-party plugin's entry point is resolved.

Plugins declare their permissions, cannot access credentials by default, run
under a safe mode that disables all third-party code, and are isolated so a
crashing plugin degrades rather than taking down the app (PRD 34).
"""

from __future__ import annotations
