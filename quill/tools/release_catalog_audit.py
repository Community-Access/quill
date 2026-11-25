"""Gate the monorepo's one release catalogue against every release consumer."""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.release_catalog import PLATFORM_VARIANTS, PRODUCTS

REPO_ROOT = Path(__file__).resolve().parents[2]


def _source_constants(path: Path, constant: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return bool(re.search(rf"^{re.escape(constant)}\s*[:=]", text, re.M))


def problems(root: Path = REPO_ROOT) -> list[str]:
    found: list[str] = []
    keys = [product.key for product in PRODUCTS]
    if len(keys) != len(set(keys)):
        found.append("release catalog keys are not unique")
    if len({product.tag_prefix for product in PRODUCTS}) != len(PRODUCTS):
        found.append("release catalog tag prefixes are not unique")
    if len({product.asset_prefix.casefold() for product in PRODUCTS}) != len(PRODUCTS):
        found.append("release catalogue asset prefixes are not unique")

    for product in PRODUCTS:
        version = root / product.version_file
        build = root / product.build_file
        if not version.is_file():
            found.append(f"{product.key}: missing version source {product.version_file}")
        elif not _source_constants(version, product.version_constant):
            found.append(
                f"{product.key}: {product.version_file} has no {product.version_constant} constant"
            )
        if not build.is_file():
            found.append(f"{product.key}: missing build source {product.build_file}")
        elif not re.search(
            rf"^{re.escape(product.build_constant)}\s*=\s*\d+",
            build.read_text(encoding="utf-8"),
            re.M,
        ):
            found.append(
                f"{product.key}: {product.build_file} has no numeric "
                f"{product.build_constant} constant"
            )
        if not (root / product.changelog).is_file():
            found.append(f"{product.key}: missing changelog {product.changelog}")
        if product.build_entry and not (root / product.build_entry).is_file():
            found.append(f"{product.key}: missing build entry {product.build_entry}")
        if product.wave != "held" and not product.build_entry:
            found.append(f"{product.key}: wave {product.wave} requires a build entry")
        if product.shared_runtime and product.key == "quill":
            found.append("quill cannot be marked as a shared-runtime app")
        if not product.shared_runtime and product.key != "quill":
            found.append(f"{product.key}: companion apps use the shared runtime")
        if product.wrapper and not (root / product.wrapper / "pyproject.toml").is_file():
            found.append(f"{product.key}: missing wrapper {product.wrapper}/pyproject.toml")

    wrappers = {
        path.name
        for path in (root / "standalone").iterdir()
        if path.is_dir() and (path / "pyproject.toml").is_file()
    } - {"runtime", *PLATFORM_VARIANTS}
    catalogued = {Path(product.wrapper).name for product in PRODUCTS if product.wrapper}
    if wrappers != catalogued:
        missing = sorted(wrappers - catalogued)
        stale = sorted(catalogued - wrappers)
        if missing:
            found.append(
                "standalone products missing from release catalogue: " + ", ".join(missing)
            )
        if stale:
            found.append("release catalogue wrappers no longer exist: " + ", ".join(stale))

    from scripts import check_sibling_versions, release_build_number  # type: ignore[import-not-found]

    expected = {product.key for product in PRODUCTS}
    if set(release_build_number.BUILD_CONSTANTS) != expected:
        found.append("release build constants disagree with the release catalogue")
    sibling_sites = {site.app for site in check_sibling_versions.SITES}
    if sibling_sites != expected - {"quill"}:
        found.append("sibling-version registry disagrees with the release catalogue")

    from quill.tools import release_feed

    released_or_candidate = {product.key for product in PRODUCTS if product.wave != "held"}
    if set(release_feed.APPS) != released_or_candidate:
        found.append("signed-feed registry disagrees with the release catalogue")
    for product in PRODUCTS:
        spec = release_feed.APPS.get(product.key)
        if spec is None:
            continue
        expected_values = (
            product.name,
            product.tag_prefix,
            product.asset_prefix,
            product.changelog,
            product.version_file,
            product.version_constant,
        )
        actual_values = (
            spec.name,
            spec.tag_prefix,
            spec.asset_prefix,
            spec.changelog,
            spec.version_file,
            spec.version_constant,
        )
        if actual_values != expected_values:
            found.append(f"{product.key}: release-feed identity differs from the catalogue")

    active = {product.key for product in PRODUCTS if product.channels_enabled}
    from quill.core.companion_install import ASSET_PREFIX
    from quill.core.data_formats import formats_for
    from quill.core.runtime_apps import RUNTIME_APPS
    from quill.core.updater import snapshots
    from quill.core.updater.profiles import PROFILES

    if set(PROFILES) != active:
        found.append("updater profiles disagree with channel-enabled catalogue products")
    if set(ASSET_PREFIX) != active:
        found.append("release-asset lookup table disagrees with channel-enabled products")
    if set(snapshots._ADAPTERS) != active:
        found.append("channel snapshots disagree with channel-enabled products")
    runtime_keys = {app.ref_id for app in RUNTIME_APPS}
    expected_runtime_keys = {
        product.key for product in PRODUCTS if product.channels_enabled and product.shared_runtime
    }
    if runtime_keys != expected_runtime_keys:
        found.append("shared-runtime app registry disagrees with channel-enabled products")
    for product in PRODUCTS:
        if not product.channels_enabled:
            continue
        owned = {name for fmt in formats_for(product.key) for name in fmt.files}
        missing = set(product.snapshot_files) - owned
        if missing:
            found.append(
                f"{product.key}: snapshot files missing data-format declarations: "
                + ", ".join(sorted(missing))
            )

    dev_workflow = (root / ".github/workflows/dev-builds.yml").read_text(encoding="utf-8")
    if "fromJSON(needs.decide.outputs.apps)" not in dev_workflow:
        found.append("Dev workflow matrix is not generated from the release catalogue")
    promotion = (root / ".github/workflows/promote-release.yml").read_text(encoding="utf-8")
    if 'description: "Catalogue app key' not in promotion:
        found.append("promotion workflow does not accept a catalogue app key")
    if "BY_KEY[app].channels_enabled" not in promotion:
        found.append("promotion workflow does not validate the catalogue app key")
    feed_workflow = (root / ".github/workflows/release-feeds.yml").read_text(encoding="utf-8")
    for required in (
        "bootstrap_release_feeds.py",
        "QUILL_FEED_SIGNING_KEY",
        "environment: release-feed-signing",
        "python scripts/feed_tool.py verify",
    ):
        if required not in feed_workflow:
            found.append(f"release-feed signing workflow is missing {required}")
    if not active.issubset(released_or_candidate):
        found.append("a channel-enabled product is absent from the signed-feed registry")

    for item in PRODUCTS:
        if not item.channels_enabled:
            continue
        if not item.release_menu_file:
            found.append(f"{item.key}: no Release Channel menu owner is catalogued")
            continue
        menu_file = root / item.release_menu_file
        if not menu_file.is_file():
            found.append(f"{item.key}: missing menu source {item.release_menu_file}")
            continue
        menu_source = menu_file.read_text(encoding="utf-8")
        if item.key == "quill":
            wired = "_install_release_channel_item" in menu_source
        elif item.key == "quilllite":
            wired = "cmd_release_channel" in menu_source
        else:
            patterns = (
                re.search(
                    rf"append_release_channel_item\([^)]*['\"]{re.escape(item.key)}['\"]",
                    menu_source,
                    re.S,
                ),
                re.search(
                    rf"release_channel_menu\.append\([^)]*['\"]{re.escape(item.key)}['\"]",
                    menu_source,
                    re.S,
                ),
            )
            wired = any(patterns)
        if not wired:
            found.append(f"{item.key}: no Release Channel menu wiring in {item.release_menu_file}")

    for product in PRODUCTS:
        if not product.build_entry.endswith(".ps1") or not product.channels_enabled:
            continue
        build_source = (root / product.build_entry).read_text(encoding="utf-8")
        if "[string]$DevVersion" not in build_source:
            found.append(f"{product.key}: Dev build script has no DevVersion input")

    build_script = (root / "build-quill-apps.ps1").read_text(encoding="utf-8")
    app_block = build_script.split("$apps = @{", 1)[-1].split("$aliases = @{", 1)[0]
    build_keys = set(re.findall(r"^\s*([a-z][a-z0-9]*)\s*=", app_block, re.M))
    expected_build_keys = {product.key for product in PRODUCTS if product.build_entry}
    expected_build_keys.add("quilllite")
    if build_keys != expected_build_keys:
        found.append(
            "build-quill-apps.ps1 app table differs from catalogue: "
            f"expected {sorted(expected_build_keys)}, found {sorted(build_keys)}"
        )
    return found


def main() -> int:
    found = problems()
    if found:
        for problem in found:
            print(f"Release catalog: {problem}")
        return 1
    print(f"Release catalog: {len(PRODUCTS)} products agree across source, feeds and build gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
