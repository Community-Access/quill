"""The stores and registries the app owns, and the areas that decide which exist.

Split from :mod:`quill.apps.lite` because it answers a different question. That
module is the *application*: windows, numbering, the inbox, the main loop. This
is what the application keeps -- the switchable feature areas, the copy tray, the
clip library, the abbreviation library, and the command registry the palette
reads.

One rule runs through all of it: **a switched-off feature owns nothing.** The
stores are built by area rather than always, so a listener who has turned the
clipboard off does not find a ``copy_tray.json`` appearing in their data folder,
and an "off" feature that still writes to disk is an off feature nobody believes.

The document memory is here for a second reason as well: it must be **one
object, not one per window.** Every open window writes its own document's row
into the same file, and two stores loaded from the same path would each hold a
snapshot from the moment it loaded -- so whichever window closed last would
write its snapshot back over the other's bookmarks. A store keyed by path has
to be shared by everything that keys into it.

The command registry is built per call rather than kept, for the opposite
reason: the commands never change, but which of them are *available* depends on
the document in front of you, and a palette offering the Format menu for a plain
text document is a palette offering something it knows will refuse.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from quill.core.lite import features as features_mod
from quill.core.lite import keymap as keymap_mod
from quill.core.lite.commands import plain_label
from quill.core.lite.keymap import binding_for, resolved_commands

logger = logging.getLogger(__name__)

__all__ = ["LiteServicesMixin"]


class LiteServicesMixin:
    """Feature areas, optional stores, and the palette's registry.

    Mixed into :class:`~quill.apps.lite.QuillLiteApp`, which supplies
    ``data_dir``, ``settings`` and ``frames``.
    """

    # -- switchable areas, and the stores they need ---------------------- #

    def feature_enabled(self, area_id: str) -> bool:
        """Is this area switched on? Unknown areas are on, by design."""
        return self.features is None or bool(self.features.is_enabled(area_id))

    def save_features(self) -> None:
        features_mod.save_features(self.data_dir, self.features)
        self._load_optional_stores()

    def _load_optional_stores(self) -> None:
        """Build (or drop) the stores whose areas are switched on.

        Loaded lazily by area rather than always: a user who has turned the
        clipboard off should not have a copy-tray file appear in their data
        folder, and an off feature that still writes to disk is an off feature
        nobody believes is off.
        """
        from quill.core.clip_library import ClipLibrary
        from quill.core.copy_tray import CopyTray

        self._load_document_memory()
        if self.feature_enabled("clipboard"):
            self.copy_tray = self.copy_tray or CopyTray(self.data_dir)
            self.clip_library = self.clip_library or ClipLibrary(self.data_dir)
        else:
            self.copy_tray = self.clip_library = None
        self.reload_abbreviations()

    # -- what each document remembers about itself ------------------------ #

    def _load_document_memory(self) -> None:
        """Load the per-document bookmark and cursor store, once for the app.

        QUILL's :class:`~quill.core.bookmarks.DocumentMemory`, pointed at
        QUILL Lite's own folder. The *code* is shared; the *file* is not, because
        QUILL Lite shares no data with QUILL (its PRD 5.3, "not a thin client")
        and a machine that has never had QUILL installed must not grow a Quill
        data folder because somebody opened a text file.

        Tied to the ``bookmarks`` area, so switching bookmarks off stops the
        file being written at all rather than merely hiding the menu -- the same
        rule the copy tray follows above. Where the cursor was is part of the
        same promise and rides along with it.
        """
        if not self.feature_enabled("bookmarks"):
            self.document_memory = None
            return
        from quill.core.bookmarks import DOCUMENT_MEMORY_FILENAME, DocumentMemory

        try:
            self.document_memory = DocumentMemory.load(self.data_dir / DOCUMENT_MEMORY_FILENAME)
        except Exception:  # noqa: BLE001 - a bad store must not stop the editor
            self.document_memory = None

    # -- abbreviations ---------------------------------------------------- #

    def abbreviation_dir(self) -> Path:
        """Where the abbreviation library is read from and written to.

        QUILL Lite's own folder unless the listener has asked, in Preferences, to
        share QUILL's -- in which case this is QUILL's data directory, the same
        one Inkwell and QUILL both use, and a change here is a change there.
        """
        if getattr(self.settings, "share_quill_abbreviations", False):
            from quill.core.paths import app_data_dir

            return app_data_dir()
        return self.data_dir

    def reload_abbreviations(self) -> None:
        """Re-read the library, or drop it when the area is switched off."""
        if not self.feature_enabled("abbreviations"):
            self.abbreviations = None
            return
        from quill.core.abbreviations_store import load_abbreviation_library

        try:
            self.abbreviations = load_abbreviation_library(self.abbreviation_dir())
        except Exception:  # noqa: BLE001 - a bad library must not stop the editor
            self.abbreviations = None

    def save_abbreviations(self) -> None:
        if self.abbreviations is None:
            return
        from quill.core.abbreviations_store import save_abbreviation_library

        try:
            save_abbreviation_library(self.abbreviations, self.abbreviation_dir())
        except Exception:  # noqa: BLE001 - a read-only profile must not lose the editor
            pass

    # -- the command palette's view of the app ---------------------------- #

    def command_registry(self, frame: Any) -> Any:
        """A registry of every command *frame* can run, for the palette.

        Built per call rather than kept: the commands are the same, but which of
        them are *available* depends on the document in front of you, and a
        palette listing the Format menu for a plain text document would be
        offering something it knows will refuse.
        """
        from quill.core.commands import CommandRegistry

        registry = CommandRegistry()
        for menu, label, key, handler, kind in resolved_commands(self.feature_enabled, self.keymap):
            # A submenu's title row names a menu, not a command: it has no
            # handler to run and no key to show.
            if kind in {"sep", "sub"}:
                continue
            registry.try_register(
                f"lite.{handler}",
                f"{plain_label(menu)}: {plain_label(label)}",
                (lambda h=handler: getattr(frame, h)()),
                keybinding=key,
            )
        return registry

    def binding_for(self, command_id: str) -> str | None:
        """The key a palette row should show, looked up by command id.

        The resolved key, not the shipped one: a palette that shows the key a
        command *used* to have is worse than one that shows none, because it is
        how a wrong key gets learned.
        """
        return binding_for(self.keymap, command_id.removeprefix("lite.")) or None

    # -- keys -------------------------------------------------------------- #

    def save_keymap(self) -> None:
        """Persist the user's rebindings and put them on every window at once.

        Every window, not the one the editor was opened from: a menu bar showing
        one key while its neighbour shows another is the same class of bug as a
        stale key, and it would be the more confusing of the two.

        A failed write is swallowed and reported, not raised. The bindings are
        already live in memory; a read-only profile costs the user the *next*
        session's keys, which is a smaller loss than an editor that cannot close.
        """
        # The menus first, and unconditionally: the bindings are already live
        # in memory, so the windows must show them whether or not the disk
        # co-operates.
        self.rebuild_all_menus()
        try:
            keymap_mod.save_keymap(self.data_dir, self.keymap)
        except OSError:
            logger.warning("Could not write the keymap file", exc_info=True)

    def reset_keymap(self) -> None:
        """Put every key back to the one QUILL Lite ships with."""
        self.keymap = keymap_mod.default_keymap()
        self.save_keymap()

    # -- menus ------------------------------------------------------------ #

    def rebuild_all_menus(self) -> None:
        """Rebuild every window's menu bar, after the feature set or the keys changed."""
        for frame in self.frames:
            try:
                frame.rebuild_menus()
            except RuntimeError:
                pass
