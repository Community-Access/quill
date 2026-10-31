"""The face watcher replaces a detector that stops answering, then gives up out loud.

The lesson is from Kelly Ford's Quick Describe: an engine can keep reporting
itself ready while it has stopped answering, so a failed request starts a
fresh one, and repeated failures end with a sentence rather than silence.
"""

from __future__ import annotations

import threading

import pytest

from quill.core.demo_recording_ffmpeg import FACE_FRAME_SIZE
from quill.platform.windows import demo_media, face_detect


class _Detector:
    created = 0
    failing = True

    def __init__(self) -> None:
        type(self).created += 1

    def detect(self, _pixels, _width, _height):
        if type(self).failing:
            raise face_detect.FaceDetectionError("The face detector did not answer in time.")
        return [(40, 30, 50, 50)]

    def close(self) -> None:
        pass


@pytest.fixture
def detector(monkeypatch):
    class Fresh(_Detector):
        created = 0
        failing = True

    monkeypatch.setattr(face_detect, "FaceDetector", Fresh)
    return Fresh


def _run_until(watcher, done: threading.Event, frames: int) -> None:
    width, height = FACE_FRAME_SIZE
    watcher.start()
    for _ in range(frames):
        if done.is_set():
            break
        watcher.feed(bytes(width * height))
        done.wait(0.2)
    watcher.stop()


def test_a_stalled_detector_is_replaced_and_then_given_up_on_with_a_sentence(detector):
    said = []
    done = threading.Event()

    def on_framing(result):
        said.append(result.sentence)
        done.set()

    watcher = demo_media.FaceWatcher(on_framing)
    _run_until(watcher, done, frames=20)

    assert said == [demo_media.FACE_DETECTION_STOPPED]
    # The first detector, then a fresh one after each of the first two failures.
    assert detector.created == demo_media.FACE_FAILURES_BEFORE_GIVING_UP


def test_one_failure_then_success_keeps_the_advice_going(detector):
    said = []
    done = threading.Event()

    class Recovering(detector):
        def detect(self, pixels, width, height):
            if type(self).created == 1:
                raise face_detect.FaceDetectionError("stalled")
            return [(40, 30, 50, 50)]

    face_detect.FaceDetector = Recovering

    def on_framing(result):
        said.append(result)
        done.set()

    watcher = demo_media.FaceWatcher(on_framing)
    _run_until(watcher, done, frames=20)

    assert said and said[0].in_view
    assert Recovering.created == 2
