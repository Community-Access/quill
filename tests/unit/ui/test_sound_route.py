"""The family's words for where sound goes (FUX-03, ui/audio/sound_route)."""

from __future__ import annotations

from quill.ui.audio import sound_route

GUID = "0f3c7a1e-1111-4222-8333-944455556666"
DEVICES = [
    ("{0.0.0.00000000}.{1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d}", "Speakers (Realtek)", True),
    ("{0.0.0.00000000}.{" + GUID + "}", "Headphones (USB)", False),
]


def test_the_system_default_is_followed_by_the_device_it_is_today() -> None:
    device = sound_route.output_device("", lister=lambda: DEVICES)
    assert device.default and device.connected
    assert sound_route.on_device(device) == "on Speakers (Realtek), the system default"


def test_a_chosen_device_is_found_by_its_identity() -> None:
    device = sound_route.output_device("wasapi/{" + GUID + "}", lister=lambda: DEVICES)
    assert sound_route.on_device(device) == "on Headphones (USB)"


def test_a_chosen_device_windows_does_not_list_is_not_reported_as_working() -> None:
    gone = sound_route.output_device(
        "wasapi/{" + GUID + "}", lister=lambda: DEVICES[:1], fallback="Headphones (USB)"
    )
    assert not gone.connected
    assert sound_route.on_device(gone) == "on Headphones (USB), not connected"


def test_when_windows_cannot_be_asked_nothing_is_claimed_about_the_connection() -> None:
    unknown = sound_route.output_device("wasapi/{" + GUID + "}", lister=lambda: None)
    assert unknown.connected and not unknown.known and unknown.label == "the chosen device"
    assert sound_route.output_device("", lister=lambda: None).label == ("the system default device")


def test_microphones_are_found_by_name() -> None:
    mics = [("{x}", "Microphone (USB Audio)", True)]
    assert sound_route.input_device("microphone (usb audio)", lister=lambda: mics).connected
    assert not sound_route.input_device("Podcast Mic", lister=lambda: mics).connected
    two = [("{a}", "Microphone (USB)", False), ("{b}", "Microphone Array", True)]
    assert not sound_route.input_device("Microphone", lister=lambda: two).known  # not a guess
    assert sound_route.input_device("Microphone Arr", lister=lambda: two).label == (
        "Microphone Array"
    )


def test_another_app_on_the_microphone_is_named_and_the_asker_is_not() -> None:
    assert sound_route.microphone_note("radio", holder=lambda: "transcribe") == (
        "QUILL Transcribe is listening on the microphone."
    )
    assert sound_route.microphone_note("studio", holder=lambda: "studio") == ""
    assert sound_route.microphone_note("radio", holder=lambda: None) == ""
    assert sound_route.microphone_note("radio", holder=lambda: "") == (
        "Another QUILL program is listening on the microphone."
    )


def test_join_drops_empty_parts() -> None:
    assert sound_route.join(["One.", "", " Two. "]) == "One. Two."
