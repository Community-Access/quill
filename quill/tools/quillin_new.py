"""quillin_new — scaffold a new QUILL extension directory.

Usage:
    python -m quill.tools.quillin_new com.example.myquillin "My Quillin" --out <dir>

Generates a ready-to-edit directory with manifest.json, extension.py, README.md,
and LICENSE.  Pass --layer1 to generate a snippet-only (no Python entry module)
extension; the default is a Python handler (Layer 2) extension.

Additional flags:
  --categories    Comma-separated QUILLIN_CATEGORIES labels (e.g. writing,productivity)
  --status-bar    Include a sample status bar cell contribution
  --doc-events    Include a sample document event subscription
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from quill.core.quillins.model import QUILLIN_CATEGORIES

_TEMPLATE_MANIFEST_L2 = """\
{{
  "schema": "quill.extension/1",
  "id": "{id}",
  "name": "{name}",
  "version": "1.0.0",
  "author": "",
  "description": "A brief one-line description of what this Quillin does.",
  "license": "MIT",
  "min_quill_version": "0.6.0",
  "categories": {categories},
  "capabilities": ["editor.read", "editor.write", "ui.announce", "ui.command"{extra_caps}],
  "main": "extension.py"{doc_events_block}{status_bar_block},
  "contributes": {{
    "commands": [
      {{
        "id": "ext.{short_id}.run",
        "title": "Run {name}",
        "description": "Runs the main action of {name}.",
        "run": {{"handler": "run"}}
      }}
    ],
    "menus": [
      {{"parent": "Tools", "command": "ext.{short_id}.run"}}
    ]{doc_events_contributes}{status_bar_contributes}
  }}
}}
"""

_TEMPLATE_MANIFEST_L1 = """\
{{
  "schema": "quill.extension/1",
  "id": "{id}",
  "name": "{name}",
  "version": "1.0.0",
  "author": "",
  "description": "A brief one-line description of what this Quillin does.",
  "license": "MIT",
  "min_quill_version": "0.6.0",
  "categories": {categories},
  "contributes": {{
    "commands": [
      {{
        "id": "ext.{short_id}.insert",
        "title": "Insert {name} snippet",
        "description": "Inserts a sample snippet.",
        "run": {{"snippet": "Hello from {name}!"}}
      }}
    ],
    "menus": [
      {{"parent": "Insert", "command": "ext.{short_id}.insert"}}
    ]
  }}
}}
"""

_TEMPLATE_EXTENSION_PY = '''\
"""Extension entry module for {name}.

Registered via ``api.register_command`` during ``setup(api)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.plugins.quillin_api import QuillExtensionApi


_api: "QuillExtensionApi | None" = None


def setup(api: "QuillExtensionApi") -> None:
    """Called once by QUILL when this Quillin is loaded."""
    global _api
    _api = api
    api.register_command("ext.{short_id}.run", run)
{extra_setup}

def run() -> None:
    """Main action. Replace with your implementation."""
    assert _api is not None
    _api.announce("Hello from {name}!")
{extra_handlers}
'''

_TEMPLATE_README = """\
# {name}

**Bundled QUILL Quillin** — `{id}`

TODO: describe what this Quillin does.

## What it does

TODO: describe the main features.

## Capabilities

TODO: list the capabilities declared in manifest.json and why each is needed.

## License

MIT.
"""

_TEMPLATE_LICENSE = """\
MIT License

Copyright (c) {year} <author>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _short_id(quillin_id: str) -> str:
    """Return the last dotted segment of the quillin id for use as a command prefix."""
    return quillin_id.rsplit(".", 1)[-1].replace("-", "_")


def _build_manifest(
    quillin_id: str,
    name: str,
    categories: list[str],
    layer1: bool,
    doc_events: bool,
    status_bar: bool,
) -> str:
    sid = _short_id(quillin_id)
    cats_json = json.dumps(categories)

    if layer1:
        return _TEMPLATE_MANIFEST_L1.format(
            id=quillin_id,
            name=name,
            short_id=sid,
            categories=cats_json,
        )

    extra_caps = ""
    if doc_events:
        extra_caps += ', "document.events"'
    if status_bar:
        extra_caps += ', "ui.status"'

    doc_events_block = ',\n  "contributes": {}\n  "contributes"' if False else ""
    doc_events_contributes = ""
    if doc_events:
        doc_events_contributes = """,
    "document_events": [
      {
        "event": "document.opened",
        "handler": "on_document_opened",
        "title": "React to document open",
        "description": "Called whenever a document is opened in the editor.",
        "enabled_by_default": true
      },
      {
        "event": "quillin.enabled",
        "handler": "on_enabled",
        "title": "Quillin enabled",
        "description": "Called when this Quillin is enabled or QUILL starts with it active.",
        "enabled_by_default": true
      },
      {
        "event": "settings.changed",
        "handler": "on_settings_changed",
        "title": "Settings changed",
        "description": "Called when any setting belonging to this Quillin is changed by the user.",
        "enabled_by_default": true
      }
    ]"""

    status_bar_contributes = ""
    if status_bar:
        status_bar_contributes = (
            """,
    "status_bar": [
      {
        "id": "status",
        "label": "Ready",
        "handler": "get_status",
        "tooltip": "Current status from """
            + name
            + """",
        "width": 12
      }
    ]"""
        )

    doc_events_block = ""
    status_bar_block = ""

    return _TEMPLATE_MANIFEST_L2.format(
        id=quillin_id,
        name=name,
        short_id=sid,
        categories=cats_json,
        extra_caps=extra_caps,
        doc_events_block=doc_events_block,
        status_bar_block=status_bar_block,
        doc_events_contributes=doc_events_contributes,
        status_bar_contributes=status_bar_contributes,
    )


def _build_extension_py(quillin_id: str, name: str, doc_events: bool, status_bar: bool) -> str:
    sid = _short_id(quillin_id)
    extra_setup = ""
    extra_handlers = ""

    if doc_events:
        extra_setup = "    api.register_command('ext." + sid + ".run', run)\n"
        extra_handlers += '''

def on_document_opened(event: dict) -> None:
    """Called when a document is opened."""
    assert _api is not None
    filename = event.get("filename", "unknown")
    _api.log(f"Document opened: {filename}")


def on_enabled(event: dict) -> None:
    """Called when this Quillin is enabled."""
    assert _api is not None
    _api.log(f"{name!r} Quillin enabled")


def on_settings_changed(event: dict) -> None:
    """Called when a setting owned by this Quillin changes."""
    assert _api is not None
    key = event.get("key", "?")
    value = event.get("value")
    _api.log(f"Setting changed: {key} = {value!r}")
'''.replace("{name!r}", repr(name))

    if status_bar:
        extra_handlers += '''

def get_status() -> str:
    """Return the current status bar cell text."""
    return "Ready"
'''

    return _TEMPLATE_EXTENSION_PY.format(
        name=name,
        short_id=sid,
        extra_setup=extra_setup,
        extra_handlers=extra_handlers,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new QUILL Quillin extension directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              quillin_new com.example.wraptools "Wrap Tools" --out src/quillins/wraptools
              quillin_new com.example.demobar "Demo Bar" --status-bar --doc-events
        """),
    )
    parser.add_argument(
        "id", metavar="QUILLIN_ID", help="Reverse-DNS Quillin ID (e.g. com.example.foo)"
    )
    parser.add_argument("name", metavar="NAME", help="Human-readable Quillin name")
    parser.add_argument(
        "--out", metavar="DIR", help="Output directory (default: last segment of ID)"
    )
    parser.add_argument(
        "--layer1", action="store_true", help="Generate a snippet-only (no Python) extension"
    )
    parser.add_argument(
        "--categories",
        metavar="CAT,...",
        help=f"Comma-separated categories from: {', '.join(sorted(QUILLIN_CATEGORIES))}",
    )
    parser.add_argument(
        "--status-bar", action="store_true", dest="status_bar", help="Add a sample status bar cell"
    )
    parser.add_argument(
        "--doc-events",
        action="store_true",
        dest="doc_events",
        help="Add sample document event subscriptions",
    )

    args = parser.parse_args(argv)
    quillin_id: str = args.id
    name: str = args.name

    categories: list[str] = []
    if args.categories:
        for cat in args.categories.split(","):
            cat = cat.strip()
            if cat not in QUILLIN_CATEGORIES:
                valid = ", ".join(sorted(QUILLIN_CATEGORIES))
                print(
                    f"Error: unknown category '{cat}'. Valid: {valid}",
                    file=sys.stderr,
                )
                return 1
            categories.append(cat)

    out_dir = Path(args.out) if args.out else Path(quillin_id.rsplit(".", 1)[-1])
    if out_dir.exists() and any(out_dir.iterdir()):
        print(
            f"Error: output directory {out_dir} already exists and is not empty.", file=sys.stderr
        )
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    import datetime

    year = datetime.date.today().year

    # manifest.json
    manifest_text = _build_manifest(
        quillin_id,
        name,
        categories,
        layer1=args.layer1,
        doc_events=args.doc_events,
        status_bar=args.status_bar,
    )
    (out_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")

    if not args.layer1:
        ext_text = _build_extension_py(quillin_id, name, args.doc_events, args.status_bar)
        (out_dir / "extension.py").write_text(ext_text, encoding="utf-8")

    (out_dir / "README.md").write_text(
        _TEMPLATE_README.format(id=quillin_id, name=name), encoding="utf-8"
    )
    (out_dir / "LICENSE").write_text(_TEMPLATE_LICENSE.format(year=year), encoding="utf-8")

    print(f"Created {out_dir}/")
    print("  manifest.json")
    if not args.layer1:
        print("  extension.py")
    print("  README.md")
    print("  LICENSE")
    print()
    print("Next steps:")
    print("  1. Edit manifest.json — fill in author, description, and capabilities.")
    print("  2. Edit extension.py — implement your handler logic.")
    print(f"  3. Run: python -m quill.tools.quillin_lint {out_dir} --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
