"""User customization of the menu bar and editor context menu.

This is the model layer behind the Menu Editor. It lets a person reorder the
top-level menus, reorder the items inside each menu, rename either, and hide
items they never use, with a single Reset to Factory Defaults. It is deliberately
``wx``-free: the UI discovers the *default* menu structure from the live menu
bar at build time and asks this model how to transform it, then the same model
is edited by the Menu Editor dialog and persisted.

Design notes
------------
* The model stores only *deltas* from the default. An empty customization means
  "exactly the factory menus", so Reset to Factory Defaults is simply an empty
  customization. This keeps stored files small and forward-compatible: items
  added in a future build appear automatically in their default position.
* Every menu and item is addressed by a stable string *key*. Top-level menus use
  a short menu key (``"file"``, ``"edit"`` ...). Items use their command id where
  one exists (``"edit.copy_with_source"``) or a synthesized stable key otherwise.
  The UI owns key assignment; this model only orders, renames, and hides by key.
* The model is *self-healing*: ordering and override maps are reconciled against
  the set of keys that actually exist, so customization referencing a removed
  command is silently dropped and never resurrects a stale entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

#: Bump when the persisted shape changes incompatibly.
SCHEMA_VERSION = 1

#: Identifies the editor context menu in the per-menu item-order/override maps.
CONTEXT_MENU_KEY = "__context__"


def menu_customization_path() -> Path:
    """Return the on-disk location of the menu customization file."""
    return app_data_dir() / "menu_customization.json"


#: Stable key and factory label for each top-level menu, in default order.
#: The Menu Editor and the menu-build transform pass share this list so a person
#: can reorder, hide, and rename top-level menus without touching item code.
TOP_MENU_DEFS: tuple[tuple[str, str], ...] = (
    ("file", "&File"),
    ("edit", "&Edit"),
    ("view", "&View"),
    ("insert", "&Insert"),
    ("format", "F&ormat"),
    ("navigate", "&Navigate"),
    # Search left the bar on 2026-09-17 and is Edit > Search Tools (bad.md M1).
    ("tools", "&Tools"),
    # Only while GitHub Workbench Mode is on (quill/ui/main_frame_github_menu.py).
    # A stable key, so a person's arrangement survives the menu coming and going.
    ("github", "&GitHub"),
    # AI and QuillVille were missing until 2026-11-08, and a bar holding a menu
    # this table could not name made the customization pass bail out: top-level
    # reordering had silently stopped applying.
    ("ai", "&AI"),
    ("window", "&Window"),
    ("quillville", "&QuillVille"),
    ("help", "&Help"),
)


@dataclass(slots=True)
class MenuCustomization:
    """Deltas applied to the factory menu bar and editor context menu.

    Attributes:
        top_order: Top-level menu keys in the user's preferred order. Keys not
            present here keep their default relative position, appended after the
            ordered ones.
        hidden_top: Top-level menu keys the user has hidden.
        top_labels: Top-level menu key -> custom label (rename).
        item_order: Menu key (or :data:`CONTEXT_MENU_KEY`) -> ordered item keys.
        hidden_items: Item keys the user has hidden, across every menu.
        item_labels: Item key -> custom label (rename).
    """

    top_order: list[str] = field(default_factory=list)
    hidden_top: list[str] = field(default_factory=list)
    top_labels: dict[str, str] = field(default_factory=dict)
    item_order: dict[str, list[str]] = field(default_factory=dict)
    hidden_items: list[str] = field(default_factory=list)
    item_labels: dict[str, str] = field(default_factory=dict)

    # -- queries used by the menu build / transform pass -------------------

    def ordered_top_keys(self, default_keys: list[str]) -> list[str]:
        """Return ``default_keys`` reordered by the user's preference.

        Keys in :attr:`top_order` that still exist come first, in their saved
        order; any remaining default keys follow in their original order. Saved
        keys that no longer exist are ignored. Hidden menus are *not* removed
        here so the editor can still show and toggle them; use
        :meth:`visible_top_keys` for the realized menu bar.
        """
        existing = set(default_keys)
        ordered = [key for key in self.top_order if key in existing]
        seen = set(ordered)
        ordered.extend(key for key in default_keys if key not in seen)
        return ordered

    def visible_top_keys(self, default_keys: list[str]) -> list[str]:
        """Like :meth:`ordered_top_keys` but with hidden menus removed."""
        hidden = set(self.hidden_top)
        return [key for key in self.ordered_top_keys(default_keys) if key not in hidden]

    def ordered_item_keys(self, menu_key: str, default_item_keys: list[str]) -> list[str]:
        """Return a menu's item keys reordered by the user's preference."""
        saved = self.item_order.get(menu_key, [])
        existing = set(default_item_keys)
        ordered = [key for key in saved if key in existing]
        seen = set(ordered)
        ordered.extend(key for key in default_item_keys if key not in seen)
        return ordered

    def visible_item_keys(self, menu_key: str, default_item_keys: list[str]) -> list[str]:
        """Like :meth:`ordered_item_keys` but with hidden items removed."""
        hidden = set(self.hidden_items)
        return [
            key for key in self.ordered_item_keys(menu_key, default_item_keys) if key not in hidden
        ]

    def is_top_hidden(self, menu_key: str) -> bool:
        """Return whether the top-level menu ``menu_key`` is hidden."""
        return menu_key in set(self.hidden_top)

    def is_item_hidden(self, item_key: str) -> bool:
        """Return whether the item ``item_key`` is hidden."""
        return item_key in set(self.hidden_items)

    def top_label(self, menu_key: str, default_label: str) -> str:
        """Return the effective top-level menu label (custom or default)."""
        custom = self.top_labels.get(menu_key, "").strip()
        return custom or default_label

    def item_label(self, item_key: str, default_label: str) -> str:
        """Return the effective item label (custom or default)."""
        custom = self.item_labels.get(item_key, "").strip()
        return custom or default_label

    # -- mutations used by the Menu Editor dialog -------------------------

    def set_top_order(self, ordered_keys: list[str]) -> None:
        """Replace the top-level menu order."""
        self.top_order = list(dict.fromkeys(ordered_keys))

    def set_item_order(self, menu_key: str, ordered_keys: list[str]) -> None:
        """Replace the item order for ``menu_key``."""
        self.item_order[menu_key] = list(dict.fromkeys(ordered_keys))

    def set_top_hidden(self, menu_key: str, hidden: bool) -> None:
        """Show or hide a top-level menu."""
        self._set_membership(self.hidden_top, menu_key, hidden)

    def set_item_hidden(self, item_key: str, hidden: bool) -> None:
        """Show or hide a single item."""
        self._set_membership(self.hidden_items, item_key, hidden)

    def rename_top(self, menu_key: str, label: str) -> None:
        """Rename a top-level menu; an empty label clears the override."""
        self._set_label(self.top_labels, menu_key, label)

    def rename_item(self, item_key: str, label: str) -> None:
        """Rename an item; an empty label clears the override."""
        self._set_label(self.item_labels, item_key, label)

    def is_customized(self) -> bool:
        """Return whether any delta from the factory defaults is present."""
        return bool(
            self.top_order
            or self.hidden_top
            or self.top_labels
            or any(self.item_order.values())
            or self.hidden_items
            or self.item_labels
        )

    def reset(self) -> None:
        """Reset every menu and item to its factory default (in place)."""
        self.top_order = []
        self.hidden_top = []
        self.top_labels = {}
        self.item_order = {}
        self.hidden_items = []
        self.item_labels = {}

    @staticmethod
    def _set_membership(collection: list[str], key: str, present: bool) -> None:
        if present:
            if key not in collection:
                collection.append(key)
        elif key in collection:
            collection.remove(key)

    @staticmethod
    def _set_label(labels: dict[str, str], key: str, label: str) -> None:
        cleaned = label.strip()
        if cleaned:
            labels[key] = cleaned
        else:
            labels.pop(key, None)

    # -- reconciliation against the live menu structure -------------------

    def reconcile(self, known_top_keys: set[str], known_item_keys: set[str]) -> None:
        """Drop deltas that reference menus or items that no longer exist.

        Called after the default menu structure is discovered so stale entries
        from an older build self-heal instead of lingering.
        """
        self.top_order = [key for key in self.top_order if key in known_top_keys]
        self.hidden_top = [key for key in self.hidden_top if key in known_top_keys]
        self.top_labels = {
            key: value for key, value in self.top_labels.items() if key in known_top_keys
        }
        self.item_order = {
            menu_key: [item for item in items if item in known_item_keys]
            for menu_key, items in self.item_order.items()
            if menu_key in known_top_keys or menu_key == CONTEXT_MENU_KEY
        }
        self.item_order = {key: value for key, value in self.item_order.items() if value}
        self.hidden_items = [key for key in self.hidden_items if key in known_item_keys]
        self.item_labels = {
            key: value for key, value in self.item_labels.items() if key in known_item_keys
        }

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Return a versioned, JSON-serializable snapshot."""
        return {
            "schema_version": SCHEMA_VERSION,
            "top_order": list(self.top_order),
            "hidden_top": list(self.hidden_top),
            "top_labels": dict(self.top_labels),
            "item_order": {key: list(value) for key, value in self.item_order.items()},
            "hidden_items": list(self.hidden_items),
            "item_labels": dict(self.item_labels),
        }

    @classmethod
    def from_dict(cls, raw: object) -> MenuCustomization:
        """Build a customization from stored data, tolerating any malformed shape.

        Unknown or wrongly typed fields fall back to empty, so a corrupt or
        partial file degrades to factory defaults rather than raising.
        """
        if not isinstance(raw, dict):
            return cls()
        return cls(
            top_order=_str_list(raw.get("top_order")),
            hidden_top=_str_list(raw.get("hidden_top")),
            top_labels=_str_map(raw.get("top_labels")),
            item_order=_str_list_map(raw.get("item_order")),
            hidden_items=_str_list(raw.get("hidden_items")),
            item_labels=_str_map(raw.get("item_labels")),
        )


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item not in out:
            out.append(item)
    return out


def _str_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, str) and item.strip():
            out[key] = item
    return out


def _str_list_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, item in value.items():
        if isinstance(key, str):
            cleaned = _str_list(item)
            if cleaned:
                out[key] = cleaned
    return out


def load_menu_customization() -> MenuCustomization:
    """Load the persisted menu customization, or factory defaults when absent."""
    raw = read_json(menu_customization_path(), default={})
    return MenuCustomization.from_dict(raw)


def save_menu_customization(customization: MenuCustomization) -> None:
    """Persist the menu customization atomically."""
    write_json_atomic(menu_customization_path(), customization.to_dict(), base=app_data_dir())
