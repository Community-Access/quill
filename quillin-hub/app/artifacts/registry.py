"""The Hub's artifact-type registry.

Every shareable QUILL artifact family the Hub accepts for review and
publication. The type ids match ``quill.tools.artifact_validate`` exactly --
that tool is the single validation authority; this registry only carries the
storefront-facing metadata (labels, guidance, upload rules).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HubArtifactType:
    id: str
    label: str
    plural: str
    description: str
    # File suffixes accepted by the Forge upload form for this type.
    upload_suffixes: tuple[str, ...]
    # Where the artifact lands inside QUILL once installed.
    installs_into: str
    # One-line submission tip shown in the Forge.
    forge_tip: str
    # Repo paths (relative to Community-Access/quill) the sync worker scans.
    repo_paths: tuple[str, ...] = field(default_factory=tuple)


ARTIFACT_TYPES: tuple[HubArtifactType, ...] = (
    HubArtifactType(
        id="quillin",
        label="Quillin extension",
        plural="Quillin extensions",
        description=(
            "Sandboxed extensions that add commands, menus, smart triggers, and "
            "automation to the QUILL editor."
        ),
        upload_suffixes=(".zip",),
        installs_into="Tools > Quillins > Manage Quillins",
        forge_tip=(
            "Zip your Quillin folder (manifest.json at the top level). The Forge "
            "runs the same quillin_lint the Quillin Verify workflow uses."
        ),
        repo_paths=("quill/quillins_bundled", "examples/quillins"),
    ),
    HubArtifactType(
        id="agent",
        label="AI agent",
        plural="AI agents",
        description=(
            "Declarative agents the AI Hub lists and any harness can run: a system "
            "prompt, permissions, and tool declarations in one reviewable file."
        ),
        upload_suffixes=(".md", ".json"),
        installs_into="AI > AI Library > Agents",
        forge_tip=(
            "Submit the single .md or .json agent file. The file name must match the agent id."
        ),
        repo_paths=("quill/core/ai/agents",),
    ),
    HubArtifactType(
        id="verbosity-pack",
        label="Verbosity pack",
        plural="Verbosity packs",
        description=(
            "Data-only bundles of verbosity templates that shape how QUILL speaks, "
            "brailles, and displays status information."
        ),
        upload_suffixes=(".qvp.json", ".json"),
        installs_into="the Verbosity Library",
        forge_tip="Submit the .qvp.json pack file. No code ever runs from a verbosity pack.",
    ),
    HubArtifactType(
        id="sound-pack",
        label="Sound pack",
        plural="Sound packs",
        description="QSP earcon packs: the WAV cues QUILL plays for sound events.",
        upload_suffixes=(".qsp",),
        installs_into="Settings > Sounds",
        forge_tip="Submit the .qsp ZIP (manifest.json plus WAV files).",
    ),
    HubArtifactType(
        id="keyboard-pack",
        label="Keyboard pack",
        plural="Keyboard packs",
        description="Keyboard Quill Packs: complete, shareable keymap layouts.",
        upload_suffixes=(".kqp",),
        installs_into="Settings > Keyboard",
        forge_tip="Submit the .kqp file exported from Settings > Keyboard.",
    ),
    HubArtifactType(
        id="skill-pack",
        label="Skill pack",
        plural="Skill packs",
        description=(
            "Skill Quill Packs: multi-step AI workflows written in plain Markdown "
            "with a YAML front matter block."
        ),
        upload_suffixes=(".sqp",),
        installs_into="AI > AI Library > Skills",
        forge_tip="Submit the .sqp file. Steps are level-1 headings; no code executes.",
    ),
    HubArtifactType(
        id="pronunciation-dictionary",
        label="Pronunciation dictionary",
        plural="Pronunciation dictionaries",
        description=(
            "Named collections of pronunciation entries applied to all QUILL speech, "
            "from jargon respellings to full SSML."
        ),
        upload_suffixes=(".json",),
        installs_into="Tools > Speech > Pronunciation Dictionaries",
        forge_tip="Submit the dictionary .json exported from the Pronunciation manager.",
    ),
)

TYPES_BY_ID = {artifact_type.id: artifact_type for artifact_type in ARTIFACT_TYPES}


def get_type(type_id: str) -> HubArtifactType | None:
    return TYPES_BY_ID.get(type_id)


def accepted_suffixes() -> tuple[str, ...]:
    """Every suffix the Forge upload accepts, across all types."""
    seen: list[str] = []
    for artifact_type in ARTIFACT_TYPES:
        for suffix in artifact_type.upload_suffixes:
            if suffix not in seen:
                seen.append(suffix)
    return tuple(seen)
