"""GATE-DATAFMT: a saved shape cannot change without somebody deciding what it means.

"Back to Stable only if safe" (release-channels plan 5) trusts the version
numbers in :mod:`quill.core.data_formats`: a build says which version of each
on-disk shape it writes, and an older build is refused when it cannot read
it. That is only as true as the numbers, and nothing used to stop somebody
changing a serializer without touching them.

This gate fingerprints what each registered format is written *from*:

* ``dataclass`` -- the fields and their declared types, following any other
  dataclass a field names (``PodcastLibrary`` -> ``PodcastShow`` -> ...). For
  QUILL Lite's settings that is also exactly the set of keys ``_deltas`` can
  write;
* ``groups`` -- the ``to_versioned`` group layout of QUILL's settings: which
  group each field is written under;
* ``constant`` -- a schema stamp written into the file;
* ``function`` -- for stores with no dataclass (keymaps, Radio's listening
  hand-off), the serializer's code, as a hash of its syntax tree (comments,
  docstrings and formatting do not count).

and compares them with ``tests/unit/core/fixtures/data_format_fingerprints.json``.
A difference fails until somebody either **bumps** ``current`` in
``data_formats.py`` (an older build would misread or lose data) or records it
as **additive, compatible** (older builds read it safely). The classification
is the review, as in ``persistence_audit``::

    python -m quill.tools.data_format_audit                  # check
    python -m quill.tools.data_format_audit --write          # record bumps and new formats
    python -m quill.tools.data_format_audit --write --accept radio.favorites \\
        --note "adds an optional station note; older builds ignore it"

``--write`` records a changed format only when its ``current`` went up, or it
is named in ``--accept``. A type that changed under an existing field cannot
be accepted as additive: that is a bump.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import re
import sys
import textwrap
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = _REPO_ROOT / "tests" / "unit" / "core" / "fixtures" / "data_format_fingerprints.json"

ADDITIVE = "additive, compatible"
BUMPED = "version bumped"
BASELINE = "baseline"

#: What each registered format is written from. Every id in
#: ``data_formats.FORMATS`` must be here (the test asserts it).
PROBES: dict[str, tuple[str, ...]] = {
    "quill.settings": (
        "dataclass:quill.core.settings:Settings",
        "groups:quill.core.settings_migration:to_versioned",
        "constant:quill.core.settings_migration:SETTINGS_SCHEMA_VERSION",
    ),
    "quill.keymap": (
        "function:quill.core.keymap:_persisted_keymap_document",
        "constant:quill.core.keymap:KEYMAP_DEFAULTS_EPOCH",
    ),
    "lite.settings": (
        "dataclass:quill.core.lite.settings:Settings",
        "constant:quill.core.lite.settings:SCHEMA",
    ),
    "lite.keymap": ("function:quill.core.lite.keymap:save_keymap",),
    "radio.favorites": (
        "dataclass:quill.core.radio.favorites:RadioFavoritesStore",
        "function:quill.core.radio.favorites:save_favorites",
    ),
    "radio.history": (
        "dataclass:quill.core.radio.history:RadioHistory",
        "function:quill.core.radio.history_store:save_history",
    ),
    "cast.library": (
        "dataclass:quill.core.podcasts.subscriptions:PodcastLibrary",
        "function:quill.core.podcasts.subscriptions:save_library",
    ),
    "cast.history": (
        "dataclass:quill.core.podcasts.history:PodcastHistory",
        "function:quill.core.podcasts.history:save_history",
    ),
    "shared.media_bookmarks": (
        "dataclass:quill.core.media.bookmarks:MediaBookmark",
        "function:quill.core.media.bookmarks:MediaBookmark.to_dict",
    ),
    "shared.listens": ("function:quill.core.podcasts.radio_listens:record_listen",),
}

Shape = dict[str, Any]


def _resolve(dotted: str) -> Any:
    module_name, _, attr = dotted.partition(":")
    target: Any = importlib.import_module(module_name)
    for part in attr.split("."):
        target = getattr(target, part)
    return target


def _type_text(annotation: object) -> str:
    return (
        annotation
        if isinstance(annotation, str)
        else getattr(annotation, "__name__", repr(annotation))
    )


def _dataclass_shape(cls: type) -> dict[str, dict[str, str]]:
    """``{"module:Class": {field: type}}`` for *cls* and every dataclass it names."""
    shapes: dict[str, dict[str, str]] = {}
    pending = [cls]
    while pending:
        current = pending.pop()
        key = f"{current.__module__}:{current.__qualname__}"
        if key in shapes:
            continue
        fields = {f.name: _type_text(f.type) for f in dataclasses.fields(current)}
        shapes[key] = fields
        namespace = vars(sys.modules[current.__module__])
        for text in fields.values():
            for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
                found = namespace.get(name)
                if isinstance(found, type) and dataclasses.is_dataclass(found):
                    pending.append(found)
    return dict(sorted(shapes.items()))


def _groups_shape() -> dict[str, str]:
    from quill.core.settings import Settings
    from quill.core.settings_migration import _group_for_key

    return {f.name: _group_for_key(f.name) for f in dataclasses.fields(Settings)}


def _function_hash(func: Callable[..., object]) -> str:
    return source_hash(inspect.getsource(func))


def source_hash(source: str) -> str:
    """The syntax tree's hash: comments, docstrings and layout do not count."""
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    dump = ast.dump(tree, annotate_fields=False, include_attributes=False)
    return "sha256:" + hashlib.sha256(dump.encode("utf-8")).hexdigest()[:16]


def probe(spec: str) -> Any:
    kind, _, dotted = spec.partition(":")
    if kind == "dataclass":
        return _dataclass_shape(_resolve(dotted))
    if kind == "groups":
        return _groups_shape()
    if kind == "constant":
        return repr(_resolve(dotted))
    if kind == "function":
        return _function_hash(_resolve(dotted))
    raise ValueError(f"unknown probe kind in {spec!r}")


def live_shapes() -> dict[str, Shape]:
    """Every registered format's ``current`` and fingerprint, from this tree."""
    from quill.core.data_formats import FORMATS

    result: dict[str, Shape] = {}
    for fmt in FORMATS:
        probes = PROBES.get(fmt.id, ())
        result[fmt.id] = {"current": fmt.current, "shape": {p: probe(p) for p in probes}}
    return result


def load_fixture(path: Path = FIXTURE) -> dict[str, Shape]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    formats = raw.get("formats") if isinstance(raw, dict) else None
    return formats if isinstance(formats, dict) else {}


def _flatten(shape: Shape) -> dict[str, str]:
    """``probe | path -> value`` leaves, for saying what changed."""
    flat: dict[str, str] = {}
    for spec, value in shape.items():
        if isinstance(value, dict):
            for key, inner in value.items():
                if isinstance(inner, dict):
                    for name, kind in inner.items():
                        flat[f"{key}.{name}"] = str(kind)
                else:
                    flat[f"{spec.split(':')[0]} {key}"] = str(inner)
        else:
            flat[spec] = str(value)
    return flat


def differences(old: Shape, new: Shape) -> tuple[list[str], list[str], list[str]]:
    """``(added, removed, changed)`` between two fingerprints."""
    before, after = _flatten(old), _flatten(new)
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    return added, removed, changed


def _type_changes(changed: Iterable[str]) -> list[str]:
    """Changes that are a field's *type*, which no reader can be assumed to absorb."""
    return [c for c in changed if not c.startswith(("groups ", "function:", "constant:"))]


def audit(
    live: dict[str, Shape] | None = None, recorded: dict[str, Shape] | None = None
) -> list[str]:
    """One sentence per format whose fingerprint disagrees with the fixture."""
    from quill.core.data_formats import FORMATS

    current = live if live is not None else live_shapes()
    fixture = recorded if recorded is not None else load_fixture()
    problems: list[str] = []
    for fmt in FORMATS:
        if fmt.id not in PROBES:
            problems.append(f"{fmt.id}: no serializer is registered in data_format_audit.PROBES")
    for format_id, now in sorted(current.items()):
        then = fixture.get(format_id)
        if then is None:
            problems.append(f"{format_id}: not in the fixture yet (run --write)")
            continue
        if then.get("shape") == now["shape"] and then.get("current") == now["current"]:
            continue
        added, removed, changed = differences(then.get("shape", {}), now["shape"])
        what = "; ".join(
            part
            for part in (
                f"added {', '.join(added)}" if added else "",
                f"removed {', '.join(removed)}" if removed else "",
                f"changed {', '.join(changed)}" if changed else "",
            )
            if part
        )
        if now["current"] != then.get("current"):
            what = f"current {then.get('current')} -> {now['current']}" + (
                f"; {what}" if what else ""
            )
        problems.append(
            f"{format_id}: the saved shape changed ({what or 'no detail'}). Bump `current` in "
            f"quill/core/data_formats.py, or record it with --write --accept {format_id} "
            "if older builds read it safely."
        )
    for format_id in sorted(set(fixture) - set(current)):
        problems.append(f"{format_id}: in the fixture but no longer registered (run --write)")
    return problems


def write(
    accept: Sequence[str] = (), note: str = "", path: Path = FIXTURE
) -> tuple[list[str], list[str]]:
    """Record what may be recorded; ``(recorded, refused)`` sentences."""
    live = live_shapes()
    fixture = load_fixture(path)
    recorded: list[str] = []
    refused: list[str] = []
    result: dict[str, Shape] = {}
    for format_id, now in sorted(live.items()):
        then = fixture.get(format_id)
        if then is None:
            result[format_id] = {**now, "classification": BASELINE, "note": ""}
            recorded.append(f"{format_id}: recorded as the baseline")
            continue
        if then.get("shape") == now["shape"] and then.get("current") == now["current"]:
            result[format_id] = then
            continue
        if int(now["current"]) > int(then.get("current", 0)):
            result[format_id] = {**now, "classification": BUMPED, "note": note}
            recorded.append(f"{format_id}: version bumped to {now['current']}")
            continue
        _added, _removed, changed = differences(then.get("shape", {}), now["shape"])
        if format_id in accept and not _type_changes(changed):
            result[format_id] = {**now, "classification": ADDITIVE, "note": note}
            recorded.append(f"{format_id}: recorded as {ADDITIVE}")
            continue
        result[format_id] = then
        reason = (
            f"a field's type changed ({', '.join(_type_changes(changed))}), which is a bump"
            if format_id in accept
            else "changed: bump `current`, or name it in --accept"
        )
        refused.append(f"{format_id}: {reason}")
    document = {
        "_doc": (
            "GATE-DATAFMT fingerprints (quill/tools/data_format_audit.py). Regenerate with "
            "python -m quill.tools.data_format_audit --write [--accept <id> --note ...]. "
            "A changed shape needs a bumped `current` or the classification "
            f"'{ADDITIVE}'; the classification is the review."
        ),
        "formats": result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(document, indent=2, sort_keys=False) + "\n").encode("utf-8"))
    return recorded, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--accept", action="append", default=[], metavar="FORMAT_ID")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    if args.write:
        recorded, refused = write(args.accept, args.note)
        for line in recorded:
            print(line)
        for line in refused:
            print(f"Not recorded: {line}")
        return 1 if refused else 0
    problems = audit()
    for line in problems:
        print(line)
    if not problems:
        print("Data formats: every saved shape matches its recorded fingerprint.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
