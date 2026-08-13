"""One tested rule for "show this file in the file manager" (x.md item 9).

The regression worth locking down is the Windows quoting one: ``/select,``
and the path must be a single argument. Split in two, Explorer silently opens
Documents instead of selecting the file -- and a screen-reader user gets no
visual cue that the wrong folder just opened.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.file_manager import reveal_command


def test_windows_binds_the_switch_and_the_path_into_one_argument() -> None:
    command = reveal_command(Path(r"C:\Users\someone\Podcasts\ep1.mp3"), platform="win32")

    assert command[0] == "explorer"
    assert len(command) == 2, "/select, and the path are ONE argument, not two"
    assert command[1].startswith("/select,")
    assert command[1] == r"/select,C:\Users\someone\Podcasts\ep1.mp3"


def test_the_switch_is_never_its_own_argument() -> None:
    """The exact bug this module exists to stop coming back."""
    command = reveal_command(Path(r"C:\audio\show.mp3"), platform="win32")
    assert "/select," not in command, "a bare /select, argument is the broken form"


def test_a_path_with_spaces_stays_one_argument() -> None:
    """Popen with an argv list quotes each element itself, so the space needs
    no escaping here -- but it must not split the element in two."""
    command = reveal_command(Path(r"C:\My Podcasts\The Daily\ep 1.mp3"), platform="win32")
    assert len(command) == 2
    assert command[1] == r"/select,C:\My Podcasts\The Daily\ep 1.mp3"


def test_macos_reveals_with_open_dash_r() -> None:
    """A POSIX path stated as text, so this branch reads the same whichever
    machine runs the suite (Path would apply the running flavour)."""
    command = reveal_command("/Users/someone/Podcasts/ep1.mp3", platform="darwin")
    assert command == ["open", "-R", "/Users/someone/Podcasts/ep1.mp3"]


def test_linux_opens_the_containing_folder() -> None:
    """No portable "select this file" verb exists, so the honest fallback is
    the folder -- not a switch that quietly does nothing."""
    command = reveal_command("/home/someone/Podcasts/ep1.mp3", platform="linux")
    assert command == ["xdg-open", "/home/someone/Podcasts"]


def test_a_string_path_is_accepted_too() -> None:
    assert reveal_command(r"C:\audio\show.mp3", platform="win32") == [
        "explorer",
        r"/select,C:\audio\show.mp3",
    ]


def test_the_platform_defaults_to_this_machine() -> None:
    command = reveal_command(Path("anything.mp3"))
    assert command[0] in {"explorer", "open", "xdg-open"}
