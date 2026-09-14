"""A settings backup that lands on a different machine (#1501).

Asked for by a user who wanted to configure QUILL once and carry it between
computers, and who worried about two things leaking into the file: his API keys
and his file paths.

**The keys were never in it.** They live in the OS credential store, not in
``Settings``, so a ``.qsf`` has never been able to carry one. That is asserted
here so it stays true.

**The paths were.** Every field went into the export, including
``watch_folder_path``, ``startup_folder``, ``tesseract_path`` and half a dozen
"last folder used" memories -- so importing a backup on a new laptop pointed the
app at folders that did not exist. Those are left out now, and *named* on the way
out, because a backup that quietly differs from the machine it came from is the
exact thing he was trying to avoid.

The other half of his request was a wizard that noticed settings added since the
file was written. What is actually needed is an answer rather than an
interrogation: how many are new, which ones, and how many locations were left
alone. :class:`PortabilityReport` is that answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields

import pytest

from quill.core.settings_portable import (
    PortabilityReport,
    portable_export,
    portable_import,
    settings_field_names,
)


@dataclass
class _Fake:
    theme: str = "dark"
    size: int = 12
    watch_folder: str = ""
    greeting: str = "hello"


LOCAL = frozenset({"watch_folder"})


# --------------------------------------------------------------------- #
# What travels, and what does not


def test_a_machine_local_setting_is_not_written_to_the_file() -> None:
    """The reporter's words: "Everything except file paths"."""
    payload, report = portable_export(
        _Fake(watch_folder="C:/Users/someone/Watched"), app="fake", local_fields=LOCAL
    )
    assert "watch_folder" not in payload["settings"]
    assert report.local == ("watch_folder",)


def test_everything_else_is_written() -> None:
    payload, report = portable_export(_Fake(), app="fake", local_fields=LOCAL)
    assert set(payload["settings"]) == {"theme", "size", "greeting"}
    assert report.carried == 3


def test_the_file_says_which_app_wrote_it() -> None:
    """Nine apps share this format; a file that does not say is a file you can
    import into the wrong one."""
    payload, _ = portable_export(_Fake(), app="weather", local_fields=LOCAL)
    assert payload["app"] == "weather"
    assert payload["schema_version"] >= 1


def test_a_local_value_in_an_old_file_is_ignored_rather_than_applied() -> None:
    """Left out rather than blanked on export, and skipped rather than applied on
    import -- so a backup from another computer cannot overwrite a good local
    value with a path that does not exist here."""
    values, report = portable_import(
        {"settings": {"theme": "light", "watch_folder": "X:/gone"}},
        known=settings_field_names(_Fake),
        local_fields=LOCAL,
    )
    assert values == {"theme": "light"}
    assert report.local == ("watch_folder",)


# --------------------------------------------------------------------- #
# What the report has to say


def test_settings_added_since_the_file_was_written_are_named() -> None:
    """His "intelligent wizard", in the form that does the work: a count and a
    list, rather than a question per setting."""
    _values, report = portable_import(
        {"settings": {"theme": "light"}},
        known=settings_field_names(_Fake),
        local_fields=LOCAL,
    )
    assert set(report.added_since) == {"size", "greeting"}
    assert "watch_folder" not in report.added_since  # local, not missing


def test_a_setting_this_build_does_not_have_is_reported_not_dropped_silently() -> None:
    """Usually a newer file being opened by an older build, which is a thing
    worth being told about before you wonder why something is not set."""
    _values, report = portable_import(
        {"settings": {"theme": "light", "a_future_setting": 1}},
        known=settings_field_names(_Fake),
        local_fields=LOCAL,
    )
    assert report.unknown == ("a_future_setting",)


def test_the_summary_names_every_number_that_is_not_zero() -> None:
    report = PortabilityReport(local=("a", "b"), added_since=("c",), unknown=("d",), carried=7)
    text = report.summary()
    assert "7 settings imported" in text
    assert "1 added since this file was written" in text
    assert "2 folder and file locations" in text
    assert "1 not recognised" in text


def test_a_clean_import_says_only_what_happened() -> None:
    """Nothing to report is not an occasion for reporting nothing four times."""
    assert PortabilityReport(carried=40).summary() == "40 settings imported."


def test_the_summary_is_app_neutral() -> None:
    """The module is shared; a Weather backup must not claim to be QUILL's."""
    assert "QUILL" not in PortabilityReport(added_since=("x",), carried=1).summary()


# --------------------------------------------------------------------- #
# It must never be the reason an import fails


@pytest.mark.parametrize("junk", [None, 7, "a string", [], {"settings": "not a mapping"}])
def test_a_file_that_is_not_a_settings_file_yields_nothing_rather_than_raising(
    junk: object,
) -> None:
    """This runs when somebody restores a backup on a new machine. An exception
    there helps nobody."""
    values, report = portable_import(junk, known=settings_field_names(_Fake))
    assert values == {}
    assert report.carried == 0


def test_a_bare_mapping_without_the_envelope_still_imports() -> None:
    """Files written before there was an envelope have to keep working."""
    values, _ = portable_import({"theme": "light"}, known=settings_field_names(_Fake))
    assert values == {"theme": "light"}


# --------------------------------------------------------------------- #
# The real apps


def test_quill_exports_no_api_key_because_it_has_none_to_export() -> None:
    """The reporter asked for keys to be excluded. They are not in Settings at
    all -- they live in the OS credential store -- so the honest answer is that
    the file was already safe. Asserted so it stays that way."""
    from quill.core.settings import Settings
    from quill.core.settings_registry import export_portable_settings, export_settings

    # Both kinds of file, because the promise is about Settings having no key
    # to leak rather than about one exporter being careful.
    for payload in (
        export_portable_settings(Settings())["settings"],
        export_settings(Settings())["settings"],
    ):
        assert isinstance(payload, dict)
        secretish = re.compile(r"api_key|apikey|secret|password|token|credential", re.I)
        assert [name for name in payload if secretish.search(name)] == []


def test_the_portable_export_leaves_quills_folders_behind() -> None:
    from quill.core.settings import Settings
    from quill.core.settings_registry import LOCAL_SETTINGS, export_portable_settings

    payload = export_portable_settings(Settings())["settings"]
    assert isinstance(payload, dict)
    assert not (set(payload) & LOCAL_SETTINGS)
    assert "watch_folder_path" in LOCAL_SETTINGS


def test_a_backup_still_keeps_them() -> None:
    """The two are different products and this is the line between them.

    A *backup* restores the computer it came from, so its watch folder and its
    Tesseract path are part of what is being restored -- ``share_package``'s
    backup contract says so outright. A *portable* export is for a different
    machine, where those same values are the bug. Excluding them from both was
    the mistake CI caught; this test is the record of the distinction.
    """
    from quill.core.settings import Settings
    from quill.core.settings_registry import export_settings

    payload = export_settings(Settings())["settings"]
    assert isinstance(payload, dict)
    assert "watch_folder_path" in payload
    assert "startup_folder" in payload


def test_quill_still_carries_the_settings_that_are_preferences() -> None:
    """The exclusion must not have quietly gutted the export."""
    from quill.core.settings import Settings
    from quill.core.settings_registry import export_portable_settings

    payload = export_portable_settings(Settings())["settings"]
    assert isinstance(payload, dict)
    assert len(payload) > 300


def test_every_local_setting_named_by_an_app_actually_exists() -> None:
    """A typo in one of these lists is a path that keeps being exported, which
    is silent and is the bug this whole change is about."""
    from quill.core.expansion.settings import LOCAL_SETTINGS as INKWELL_LOCAL
    from quill.core.expansion.settings import InkwellSettings
    from quill.core.lite.settings import LOCAL_SETTINGS as LITE_LOCAL
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.podcasts.models_settings import LOCAL_SETTINGS as CAST_LOCAL
    from quill.core.podcasts.models_settings import PodcastSettings
    from quill.core.settings import Settings as QuillSettings
    from quill.core.settings_registry import LOCAL_SETTINGS as QUILL_LOCAL
    from quill.core.weather.settings import LOCAL_SETTINGS as WEATHER_LOCAL
    from quill.core.weather.settings import WeatherSettings

    for names, cls in (
        (QUILL_LOCAL, QuillSettings),
        (LITE_LOCAL, LiteSettings),
        (WEATHER_LOCAL, WeatherSettings),
        (CAST_LOCAL, PodcastSettings),
        (INKWELL_LOCAL, InkwellSettings),
    ):
        real = {spec.name for spec in fields(cls)}
        missing = sorted(names - real)
        assert missing == [], f"{cls.__name__} has no {missing}"


def test_quilllite_round_trips_its_preferences_and_not_its_recent_files() -> None:
    from quill.core.lite.settings import Settings, export_portable, import_portable

    settings = Settings()
    settings.font_size = 18
    settings.word_wrap = False
    settings.recent_files = ["C:/only-on-that-machine.txt"]
    payload, out = export_portable(settings)
    assert "recent_files" not in payload["settings"]
    assert "recent_files" in out.local

    restored, back = import_portable(payload)
    assert restored.font_size == 18
    assert restored.word_wrap is False
    assert restored.recent_files == []
    assert back.carried > 20
