from pathlib import Path

from quill.io.illumination import (
    ILLUMINATION_SUFFIX,
    ILLUMINATION_VERSION,
    build_illumination,
    illumination_path_for,
    markup_has_formatting,
    read_illumination,
    restore_markup,
    write_illumination,
)
from quill.io.rtf_model import markdown_to_rich

_FORMATTED = (
    "# Heading\n"
    'A [bold word]{font-family="Arial" font-size="14"} and a **plain bold** run.\n'
    "- a bullet"
)


def test_markup_has_formatting_detects_formatting() -> None:
    assert markup_has_formatting(_FORMATTED) is True
    assert markup_has_formatting("just two\nplain lines") is False


def test_build_records_clean_text_and_version() -> None:
    illumination = build_illumination(_FORMATTED)
    assert illumination["version"] == ILLUMINATION_VERSION
    # The hash is over the clean (formatting-stripped) text the .txt will hold.
    clean = markdown_to_rich(_FORMATTED).plain_text()
    assert "{font-family" not in clean and "**" not in clean and "#" not in clean
    assert "document" in illumination


def test_round_trips_formatted_markup() -> None:
    illumination = build_illumination(_FORMATTED)
    clean = markdown_to_rich(_FORMATTED).plain_text()
    restored = restore_markup(illumination, clean)
    assert restored == _FORMATTED


def test_restore_returns_none_when_text_drifted() -> None:
    # The user edited the .txt outside QUILL: the overlay must not be applied.
    illumination = build_illumination(_FORMATTED)
    assert restore_markup(illumination, "totally different text") is None


def test_restore_returns_none_on_unknown_version() -> None:
    illumination = build_illumination(_FORMATTED)
    clean = markdown_to_rich(_FORMATTED).plain_text()
    illumination["version"] = 999
    assert restore_markup(illumination, clean) is None


def test_restore_returns_none_on_garbage() -> None:
    assert restore_markup(None, "x") is None
    assert restore_markup({"version": ILLUMINATION_VERSION}, "x") is None


def test_sidecar_path_appends_suffix_to_full_name() -> None:
    assert illumination_path_for(Path("/docs/report.txt")) == Path(
        "/docs/report.txt" + ILLUMINATION_SUFFIX
    )


def test_write_then_read_round_trips_via_disk(tmp_path: Path) -> None:
    doc = tmp_path / "report.txt"
    doc.write_text(markdown_to_rich(_FORMATTED).plain_text(), encoding="utf-8")
    illumination = build_illumination(_FORMATTED)
    written = write_illumination(doc, illumination)
    assert written == tmp_path / ("report.txt" + ILLUMINATION_SUFFIX)
    assert written.is_file()

    loaded = read_illumination(doc)
    assert loaded is not None
    restored = restore_markup(loaded, doc.read_text(encoding="utf-8"))
    assert restored == _FORMATTED


def test_read_illumination_absent_is_none(tmp_path: Path) -> None:
    assert read_illumination(tmp_path / "no-sidecar.txt") is None
