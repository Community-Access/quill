"""Camera framing advice for a presenter who cannot see the preview."""

from __future__ import annotations

from quill.core.demo_camera import (
    FIRST_FRAME_GRACE_S,
    FirstFrameGrace,
    Framing,
    FramingAnnouncer,
    framing,
)

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


# -- VIDEO-003: a camera that is starting is "not yet", not "broken" ---------------------


class _Clock:
    def __init__(self):
        self.now = 50.0

    def __call__(self):
        return self.now


def test_grace_starts_at_the_first_frame_read_not_at_launch():
    clock = _Clock()
    grace = FirstFrameGrace(clock=clock)
    clock.now += 10  # however long the camera takes to open, that is not a fault
    assert not grace.settled
    grace.frame_read()  # the first frame, 0.58 s or 10 s after asking
    clock.now += FIRST_FRAME_GRACE_S - 0.1
    grace.frame_read()
    assert not grace.settled and grace.frames == 2
    clock.now += 0.1
    assert grace.settled


def test_dark_start_up_frames_never_say_your_face_left():
    clock = _Clock()
    grace = FirstFrameGrace(clock=clock)
    announcer = FramingAnnouncer(coarse=True, grace=grace)
    gone = Framing(0, "No face in view.")
    good = Framing(1, "Face in view, centred.")
    said = []
    for _ in range(4):  # exposure still settling: every frame finds no face
        grace.frame_read()
        clock.now += 0.2
        said.append(announcer.feed(gone))
    assert said == [None] * 4
    grace.frame_read()
    said = [announcer.feed(good), announcer.feed(good)]
    assert said == [None, None]  # starting in view stays silent
    clock.now += FIRST_FRAME_GRACE_S
    # After the grace a real loss is still reported, once.
    assert [announcer.feed(gone), announcer.feed(gone)] == [None, "Your face left the camera view."]


def test_the_camera_check_speaks_no_face_only_after_the_grace():
    clock = _Clock()
    grace = FirstFrameGrace(clock=clock)
    announcer = FramingAnnouncer(grace=grace)
    none = Framing(0, "No face in view.")
    grace.frame_read()
    assert [announcer.feed(none), announcer.feed(none)] == [None, None]
    clock.now += FIRST_FRAME_GRACE_S
    assert [announcer.feed(none), announcer.feed(none)] == [None, "No face in view."]


def test_a_detector_failure_is_never_held_by_the_grace():
    grace = FirstFrameGrace(clock=_Clock())  # no frame read at all
    announcer = FramingAnnouncer(grace=grace)
    broken = Framing(0, "Face detection is unavailable: no detector.")
    assert [announcer.feed(broken), announcer.feed(broken)] == [None, broken.sentence]


def test_the_face_watcher_counts_frames_actually_read():
    from quill.platform.windows.demo_media import FaceWatcher

    grace = FirstFrameGrace(clock=_Clock())
    watcher = FaceWatcher(lambda _result: None, grace=grace)
    assert grace.frames == 0
    watcher.feed(b"\0" * 4)
    watcher.feed(b"\0" * 4)
    assert grace.frames == 2
