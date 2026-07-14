"""CI gate: every feature ID in COMMAND_FEATURE_MAP must exist in FEATURE_DEFINITIONS.

Catches typos and stale mappings before they become silent runtime failures — a
command mapped to a non-existent feature would either crash or never be filtered
correctly.

Run::

    python -m quill.tools.check_feature_tags

Exit 0 = all checks pass.  Exit 1 = failures reported to stdout.
"""

from __future__ import annotations

import sys


def run() -> int:
    from quill.core.feature_command_map import COMMAND_FEATURE_MAP
    from quill.core.features import FEATURE_DEFINITIONS

    errors: list[str] = []
    for command_id, feature_id in sorted(COMMAND_FEATURE_MAP.items()):
        if feature_id not in FEATURE_DEFINITIONS:
            errors.append(f"command {command_id!r} references unknown feature {feature_id!r}")

    # The dependency graph must be sound for enable/disable and kill-switch
    # cascades to be correct: every declared dependency must exist, and there
    # must be no cycles (a cycle would make transitive resolution ambiguous and
    # can infinite-loop a naive walk).
    for feature_id, definition in sorted(FEATURE_DEFINITIONS.items()):
        for dependency in definition.dependencies:
            if dependency not in FEATURE_DEFINITIONS:
                errors.append(f"feature {feature_id!r} depends on unknown feature {dependency!r}")
    cycle = _find_dependency_cycle(FEATURE_DEFINITIONS)
    if cycle is not None:
        errors.append("feature dependency cycle: " + " -> ".join(cycle))

    if errors:
        for err in errors:
            print(f"FEATURE_TAGS: {err}")
        return 1

    print(
        f"check_feature_tags: OK "
        f"({len(COMMAND_FEATURE_MAP)} commands, "
        f"{len(FEATURE_DEFINITIONS)} features, dependency graph acyclic)"
    )
    return 0


def _find_dependency_cycle(definitions: dict) -> list[str] | None:
    """Return a dependency cycle as a path if one exists, else None (DFS)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {fid: WHITE for fid in definitions}

    def visit(node: str, path: list[str]) -> list[str] | None:
        color[node] = GRAY
        path.append(node)
        definition = definitions.get(node)
        for dependency in getattr(definition, "dependencies", ()):
            if dependency not in definitions:
                continue
            if color[dependency] == GRAY:
                return path[path.index(dependency) :] + [dependency]
            if color[dependency] == WHITE:
                found = visit(dependency, path)
                if found is not None:
                    return found
        color[node] = BLACK
        path.pop()
        return None

    for feature_id in definitions:
        if color[feature_id] == WHITE:
            found = visit(feature_id, [])
            if found is not None:
                return found
    return None


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
