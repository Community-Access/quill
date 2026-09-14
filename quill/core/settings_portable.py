"""Settings you can carry to another machine, and be told what did not fit (#1501).

Asked for by a user who wanted to configure QUILL once and move that
configuration between machines: *"the user often makes several changes to a
complex app like this over a long period of time, and they often don't remember
exactly how they got something to work as they did."*

Most of what he asked for already existed -- QUILL exports settings to a `.qsf`
file, the exact extension he proposed -- but two things in his description were
right and missing.

**The export carried machine-local paths.** Every field of the settings object
went into the file, including `watch_folder_path`, `startup_folder`,
`tesseract_path`, the sound pack, the model directories and half a dozen
"last folder used" memories. Import that on a different machine, or a different
account on the same machine, and you get a configuration pointing at folders
that are not there. His phrasing was exact: *"Everything except file paths and
the api keys for the ai hub."* The keys were never a problem -- they live in the
credential store, not here -- but the paths were.

**Nothing told you what had changed.** A file written against an older build
knows nothing about settings added since, and an import that silently applied
defaults for them left the user to discover the gap on their own. He asked for a
wizard; what is actually needed is an *answer*: how many settings are new, which
ones, and how many machine-local values were deliberately left behind. A count
and a list, said out loud, does the work the wizard was standing in for.

Generic over any settings dataclass, because nine apps have one and the argument
above is the same in all nine.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

__all__ = [
    "SCHEMA_VERSION",
    "PortabilityReport",
    "portable_export",
    "portable_import",
    "settings_field_names",
]

#: Bumped only when the envelope changes, never when a setting is added or
#: removed -- the whole design here is that those are survivable.
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PortabilityReport:
    """What an export left out, or what an import found different.

    Every field here exists to be *said*. A backup that quietly differs from the
    machine it came from is the thing the reporter was trying to avoid.
    """

    #: Machine-local settings deliberately not written (export) or not read
    #: back (import).
    local: tuple[str, ...] = ()
    #: Settings this build has that the file did not -- added since it was
    #: written. They keep their defaults.
    added_since: tuple[str, ...] = ()
    #: Settings the file has that this build does not. Usually a newer file
    #: being read by an older build.
    unknown: tuple[str, ...] = ()
    #: How many settings actually crossed over.
    carried: int = 0

    def summary(self) -> str:
        """One sentence naming every number that is not zero.

        Deliberately not a table and not a dialog: this is read out after an
        import, and a listener wants the shape of what happened before they want
        the detail. The detail is in the lists.
        """
        parts = [f"{self.carried} setting{'' if self.carried == 1 else 's'} imported"]
        if self.added_since:
            count = len(self.added_since)
            # App-neutral: this module is shared, and a Weather backup saying
            # "added to QUILL" would be describing the wrong app.
            parts.append(
                f"{count} added since this file was written "
                f"({'it' if count == 1 else 'they'} kept "
                f"{'its' if count == 1 else 'their'} default)"
            )
        if self.local:
            count = len(self.local)
            parts.append(
                f"{count} folder or file location left alone, because those belong to this machine"
                if count == 1
                else f"{count} folder and file locations left alone, because "
                "those belong to this machine"
            )
        if self.unknown:
            parts.append(f"{len(self.unknown)} not recognised by this version")
        return ". ".join(parts) + "."


def settings_field_names(settings: Any) -> frozenset[str]:
    """Every field name on *settings*, which may be a class or an instance."""
    return frozenset(spec.name for spec in fields(settings))


def portable_export(
    settings: Any,
    *,
    app: str,
    local_fields: frozenset[str] | set[str] = frozenset(),
) -> tuple[dict[str, Any], PortabilityReport]:
    """``(payload, report)`` -- *settings* as a file, minus what cannot travel.

    ``local_fields`` names the settings whose value is a path, a folder or
    anything else that describes *this* machine. They are left out rather than
    blanked, so importing an old file cannot wipe a good local value either.
    """
    from dataclasses import asdict

    data = asdict(settings)
    kept = {name: value for name, value in data.items() if name not in local_fields}
    left_out = tuple(sorted(name for name in data if name in local_fields))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "app": app,
        "settings": kept,
    }
    return payload, PortabilityReport(local=left_out, carried=len(kept))


def portable_import(
    raw: object,
    *,
    known: frozenset[str] | set[str],
    local_fields: frozenset[str] | set[str] = frozenset(),
) -> tuple[dict[str, Any], PortabilityReport]:
    """``(values, report)`` -- the settings in *raw* this build can use.

    Accepts the wrapped envelope or a bare mapping, so a file written before
    there was an envelope still imports. Never raises: a file that is not a
    settings file yields nothing to apply and a report that says so, because the
    alternative -- an exception on the way back from a holiday with a new
    laptop -- helps nobody.
    """
    payload: Any = raw
    if isinstance(payload, dict) and isinstance(payload.get("settings"), dict):
        payload = payload["settings"]
    if not isinstance(payload, dict):
        return {}, PortabilityReport(added_since=tuple(sorted(known)))
    values = {
        str(name): value
        for name, value in payload.items()
        if str(name) in known and str(name) not in local_fields
    }
    in_file = {str(name) for name in payload}
    return values, PortabilityReport(
        local=tuple(sorted(name for name in in_file if name in local_fields)),
        added_since=tuple(sorted(known - in_file - frozenset(local_fields))),
        unknown=tuple(sorted(in_file - frozenset(known))),
        carried=len(values),
    )
