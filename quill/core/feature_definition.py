"""Feature metadata, kept separate from the catalogue's size budget."""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.app_launcher import is_dev_build


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    id: str
    name: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    maturity: str = "stable"
    privacy: str = "local only"
    locked_on: bool = False
    locked_off: bool = False
    category: str = ""
    #: False for a feature that is built but held back from the public
    #: release: locked off in a public build, normal in a developer build
    #: (``QUILL_DEV_BUILD=1``) -- the same one switch that reveals the gated
    #: companion apps (``app_launcher.RELEASED_APPS``). Use ``locked_off``
    #: instead for a feature that is off in *every* build.
    released: bool = True
    #: Off in every profile that does not name it, where an unlisted feature
    #: is otherwise on. Only ``core.developer`` uses it: coding features are
    #: the Developer profile's to turn on (code.md 6.4), and a new profile
    #: must not switch them on by forgetting to mention them.
    default_off: bool = False

    @property
    def is_locked_off(self) -> bool:
        """Locked off in this build: permanently, or merely unreleased."""
        return self.locked_off or not (self.released or is_dev_build())
