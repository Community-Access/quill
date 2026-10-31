"""Camera framing advice for a presenter who cannot see the preview."""

from __future__ import annotations

from quill.core.demo_camera import Framing, FramingAnnouncer, framing

W, H = 320, 240


def test_no_face_and_several_faces():
    assert framing([], W, H).sentence == "No face in view."
    assert framing([(10, 10, 50, 50), (200, 10, 50, 50)], W, H).sentence == "2 faces in view."
    assert framing([], 0, 0).sentence.startswith("The camera delivered no picture")


def test_centred_face():
    result = framing([(130, 70, 60, 60)], W, H)
    assert result.sentence == "Face in view, centred."
    assert result.good and result.in_view


def test_face_on_image_left_means_move_to_your_left():
    result = framing([(20, 70, 60, 60)], W, H)
    assert "move to your left" in result.sentence.lower()
    flipped = framing([(20, 70, 60, 60)], W, H, mirrored=True)
    assert "to your right" in flipped.sentence


def test_small_offset_says_a_little():
    assert "a little to your right" in framing([(200, 70, 60, 60)], W, H).sentence


def test_distance_and_height_advice():
    assert "move back" in framing([(60, 30, 200, 180)], W, H).sentence.lower()
    assert "move closer" in framing([(150, 90, 20, 20)], W, H).sentence.lower()
    # Low in the picture: the camera points above the face.
    assert "tilt the camera down" in framing([(130, 160, 60, 60)], W, H).sentence.lower()
    assert "tilt the camera up" in framing([(130, 6, 60, 30)], W, H).sentence.lower()


def test_cut_off_face_is_named_first():
    result = framing([(130, 0, 60, 60)], W, H)
    assert result.sentence.startswith("Face in view: Your face is cut off at the top")


def test_announcer_waits_for_stable_change_and_never_repeats():
    announcer = FramingAnnouncer()
    none = Framing(0, "No face in view.")
    good = Framing(1, "Face in view, centred.")
    assert announcer.feed(none) is None
    assert announcer.feed(none) == "No face in view."
    assert announcer.feed(none) is None
    assert announcer.feed(good) is None
    assert announcer.feed(none) is None  # a blink does not speak
    assert announcer.feed(good) is None
    assert announcer.feed(good) == "Face in view, centred."


def test_coarse_announcer_only_speaks_leaving_and_returning():
    announcer = FramingAnnouncer(coarse=True)
    good = Framing(1, "Face in view, centred.")
    left = Framing(1, "Face in view: Move to your left.")
    gone = Framing(0, "No face in view.")
    assert [announcer.feed(x) for x in (good, good, left, left)] == [None, None, None, None]
    assert [announcer.feed(gone), announcer.feed(gone)] == [None, "Your face left the camera view."]
    assert [announcer.feed(good), announcer.feed(good)] == [None, "Face back in camera view."]
